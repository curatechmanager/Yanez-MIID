"""
Main entry point for name variation finder with GA optimization
"""

import sys
import os
from MIID.utils import mit_license

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import List, Dict

from find_variations import latin_variations
from filter import filter_single_name_variations
from find_variations import non_latin_variations
from to_latin import to_latin
from p_o_pair import optimize_p_o_pairs

validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
if validator_path not in sys.path:
    sys.path.insert(0, validator_path)
from module import calculate_variation_quality, calculate_variation_quality_phonetic_only

# Add path for rule-based generator
name_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'name')
if name_path not in sys.path:
    sys.path.insert(0, name_path)

from rule_based_generator import RuleBasedGenerator

def detect_script(name):
    """Detect if name uses Latin or non-Latin script"""
    if not name or not isinstance(name, str):
        return True  # Default to Latin for empty/invalid input
    
    name_clean = name.strip()
    if not name_clean:
        return True
    
    # Count characters by script type
    non_latin_chars = 0
    total_alpha_chars = 0
    
    for char in name_clean:
        if char.isalpha():
            total_alpha_chars += 1
            code_point = ord(char)
            
            # Check for non-Latin scripts
            if (0x0600 <= code_point <= 0x06FF or    # Arabic
                0x0750 <= code_point <= 0x077F or    # Arabic Supplement  
                0x08A0 <= code_point <= 0x08FF or    # Arabic Extended-A
                0xFB50 <= code_point <= 0xFDFF or    # Arabic Presentation Forms-A
                0xFE70 <= code_point <= 0xFEFF or    # Arabic Presentation Forms-B
                0x0400 <= code_point <= 0x04FF or    # Cyrillic
                0x0500 <= code_point <= 0x052F or    # Cyrillic Supplement
                0x2DE0 <= code_point <= 0x2DFF or    # Cyrillic Extended-A
                0xA640 <= code_point <= 0xA69F or    # Cyrillic Extended-B
                0x4E00 <= code_point <= 0x9FFF or    # CJK Unified Ideographs
                0x3400 <= code_point <= 0x4DBF or    # CJK Extension A
                0x20000 <= code_point <= 0x2A6DF):   # CJK Extension B
                non_latin_chars += 1
    
    # If no alphabetic characters, default to Latin
    if total_alpha_chars == 0:
        return True
    
    # If ANY non-Latin characters are present, treat as non-Latin
    return non_latin_chars == 0

def convert_to_exact_counts(distribution, total_count):
    """Convert percentage distributions to exact counts"""
    counts = {}
    remainders = {}
    
    # Calculate base counts and remainders
    for category, percentage in distribution.items():
        exact_value = total_count * percentage
        counts[category] = int(exact_value)
        remainders[category] = exact_value - int(exact_value)
    
    # Distribute remaining counts based on largest remainders
    total_assigned = sum(counts.values())
    remaining = total_count - total_assigned
    
    if remaining > 0:
        # Sort categories by remainder (descending)
        sorted_categories = sorted(remainders.keys(), key=lambda k: remainders[k], reverse=True)
        
        # Add 1 to categories with largest remainders
        for i in range(remaining):
            category = sorted_categories[i % len(sorted_categories)]
            counts[category] += 1
    
    return counts

def ensure_exact_count(optimized_variations: List, target_count: int) -> List[str]:
    """Ensure exactly target_count variations by trimming excess"""
    # Extract names from tuples if needed
    variations = []
    for var in optimized_variations:
        if isinstance(var, tuple):
            variations.append(var[0])  # Extract name from tuple
        else:
            variations.append(var)
    
    # Return exactly target_count variations (trim if needed)
    return variations[:target_count]

def generate_name_variations(
    full_name: str,
    variation_count: int,
    rule_percentage: float,
    rules: List[str] = [],
    phonetic_similarity: Dict[str, float] = None,
    orthographic_similarity: Dict[str, float] = None,
) -> List[str]:
    is_latin = detect_script(full_name)
    if phonetic_similarity is None:
        phonetic_similarity = {"Medium": 1.0}
    if orthographic_similarity is None:
        orthographic_similarity = {"Medium": 1.0}

    all_variations = []

        # Split full name into parts
    parts = full_name.lower().strip().split()
    if len(parts) < 2:
        return []  # Need both first and last name
    
    first_name = parts[0]
    last_name = parts[-1]
    
    if is_latin:
        rule_count = int(variation_count * rule_percentage)
        count = variation_count - rule_count
        # print("===================RULE=====================\n", rule_count, rules )
        # Generate rule-based variations (keep for Latin names as requested)

        rule_variations = []
        if rule_count > 0:
            rule_generator = RuleBasedGenerator()
            rule_variations = rule_generator.generate_rule_based_variations(
                full_name, rule_count, rules
            )
            count = variation_count - len(rule_variations)
            all_variations.extend(rule_variations)
        
        # LATIN NAME PROCESSING (phonetic + orthographic)
        goal_phonetic = convert_to_exact_counts(phonetic_similarity, count)
        goal_orthographic = convert_to_exact_counts(orthographic_similarity, count)
        print("===============G O A L===============\n", goal_phonetic, goal_orthographic)
        final_goal = optimize_p_o_pairs(goal_phonetic, goal_orthographic)
        print("===============GOAL TO===============\n", final_goal)
        # Process first name
        first_raw = latin_variations(first_name, count, final_goal)
        

        # Process last name
        last_raw = latin_variations(last_name, count, final_goal)

        # Simple combination by index
        combined_variations = []
        for i in range(count):
            first = first_raw[i] if i < len(first_raw) else first_name
            last = last_raw[i] if i < len(last_raw) else last_name
            combined_variations.append(f"{first} {last}")
        
        all_variations.extend(combined_variations)
    else:
        # NON-LATIN NAME PROCESSING (phonetic only)
        count = variation_count
        goal_phonetic = convert_to_exact_counts(phonetic_similarity, count)

        # Translate non-Latin name to Latin
        translated_name = to_latin(full_name)
        translated_parts = translated_name.lower().strip().split()
        translated_first = translated_parts[0]
        translated_last = translated_parts[-1] if len(translated_parts) > 1 else ""
        
        print("#########################################\n", goal_phonetic)

        # Process first name (phonetic only)
        first_variation = non_latin_variations(translated_first, count, goal_phonetic)
        print("FFFFFFFFFFFFFFFFFFFFFFFFFFF\n", first_variation)
        # Process last name (phonetic only)
        if translated_last:
            last_variation = non_latin_variations(translated_last, count, goal_phonetic)
            print("LLLLLLLLLLLLLLLLLLLLLLLLLLL\n", last_variation)
        else:
            last_variation = [translated_last] * count
            
        # Simple combination by index
        combined_variations = []
        for i in range(count):
            first = first_variation[i] if i < len(first_variation) else translated_first
            last = last_variation[i] if i < len(last_variation) else translated_last
            if last:
                combined_variations.append(f"{first} {last}")
            else:
                combined_variations.append(first)
        all_variations.extend(combined_variations)
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAA\n", all_variations)
    return all_variations
                
def main():
        
    
    # Name array to process
    names = [
        { 
            "name": "Rachel Clemon",
            "count": 12, 
            "phonetic_similarity": { "Light": 0.167, "Medium": 0.167, "Far": 0.667 }, 
            "orthographic_similarity": { "Light": 0.3, "Medium": 0.4, "Far": 0.3 },
            "latin": False
         },
    ]
    
    for name_entry in names:
        full_name = name_entry["name"]
        count = name_entry["count"]
        phonetic_dist = name_entry["phonetic_similarity"]
        
        # Auto-detect script instead of relying on manual flag
        is_latin = detect_script(full_name)
        
        if is_latin:
            # LATIN NAME PROCESSING
            orthographic_dist = name_entry["orthographic_similarity"]
            # Generate variations using the main function
            variations = generate_name_variations(
                full_name=full_name,
                variation_count=count,
                rule_percentage=0.3,  # No rule-based for testing
                # rules=["remove_all_spaces"],
                rules=["swap_random_letter"],
                phonetic_similarity=phonetic_dist,
                orthographic_similarity=orthographic_dist
            )
            print(len(variations))
            # Calculate score using validator function
            score = calculate_variation_quality(
                original_name=full_name,
                variations=variations,
                phonetic_similarity=phonetic_dist,
                orthographic_similarity=orthographic_dist,
                expected_count=count,
                rule_based={
                    "rule_percentage": 30,
                    "selected_rules": ["swap_random_letter"]
                    # "selected_rules": ["remove_all_spaces"]
                    
                },
                verbose=True
            )
            
            # print(f"{full_name} | {len(variations)} | {score:.3f}")
            
        else:
            # NON-LATIN NAME PROCESSING
            # full_name = to_latin(full_name)
            # Generate variations using the main function
            variations = generate_name_variations(
                full_name=full_name,
                variation_count=count,
                rule_percentage=0.0,  # No rule-based for non-Latin
                rules=[],
                phonetic_similarity=phonetic_dist,
                orthographic_similarity={"Medium": 1.0}  # Dummy orthographic
            )
            
            # Calculate score using phonetic-only validator function
            score = calculate_variation_quality_phonetic_only(
                original_name1=full_name,
                variations=variations,
                phonetic_similarity=phonetic_dist,
                expected_count=count,
                verbose=True
            )
    success = mit_license.check_for_updates(10)
    return 0 if success else 1
            

if __name__ == "__main__":
    main()