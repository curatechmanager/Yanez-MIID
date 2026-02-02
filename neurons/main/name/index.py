#!/usr/bin/env python3
"""
Main Name Variation Generator

Implements the generate_name_variations function as specified in .md file.
Handles both Latin and non-Latin names with rule-based and non-rule-based generation.
"""

import random
import re
import os
from typing import List, Dict, Set

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rule_based_generator import RuleBasedGenerator
from non_rule_based import NameVariationOptimizer
from non_latin_generator import NonLatinNameOptimizer
from name_variations import generate_name_variations as basic_generate_name_variations


def detect_script(name):

    if not name or not isinstance(name, str):
        return True  # Default to Latin for empty/invalid input
    
    # Remove spaces and convert to lowercase for analysis
    name_clean = name.strip()
    if not name_clean:
        return True
    
    # Count characters by script type
    latin_chars = 0
    non_latin_chars = 0
    total_alpha_chars = 0
    
    for char in name_clean:
        if char.isalpha():
            total_alpha_chars += 1
            code_point = ord(char)
            
            # Check for non-Latin scripts first (based on validator's categorization)
            
            # Arabic script (includes Persian/Farsi, Urdu, Pashto)
            if (0x0600 <= code_point <= 0x06FF or    # Arabic
                0x0750 <= code_point <= 0x077F or    # Arabic Supplement  
                0x08A0 <= code_point <= 0x08FF or    # Arabic Extended-A
                0xFB50 <= code_point <= 0xFDFF or    # Arabic Presentation Forms-A
                0xFE70 <= code_point <= 0xFEFF):     # Arabic Presentation Forms-B
                non_latin_chars += 1
                
            # Cyrillic script (Russian, Ukrainian, Bulgarian, Belarusian, etc.)
            elif (0x0400 <= code_point <= 0x04FF or  # Cyrillic
                  0x0500 <= code_point <= 0x052F or  # Cyrillic Supplement
                  0x2DE0 <= code_point <= 0x2DFF or  # Cyrillic Extended-A
                  0xA640 <= code_point <= 0xA69F):   # Cyrillic Extended-B
                non_latin_chars += 1
                
            # Chinese/Japanese/Korean (CJK)
            elif (0x4E00 <= code_point <= 0x9FFF or  # CJK Unified Ideographs
                  0x3400 <= code_point <= 0x4DBF or  # CJK Extension A
                  0x20000 <= code_point <= 0x2A6DF): # CJK Extension B
                #   0x3040 <= code_point <= 0x309F or  # Hiragana
                #   0x30A0 <= code_point <= 0x30FF or  # Katakana
                #   0x31F0 <= code_point <= 0x31FF or  # Katakana Phonetic Extensions
                #   0xAC00 <= code_point <= 0xD7AF):   # Hangul Syllables
                non_latin_chars += 1
                
            # Latin script (including extended Latin)
            elif (0x0041 <= code_point <= 0x007A or  # Basic Latin (A-Z, a-z)
                  0x00C0 <= code_point <= 0x024F or  # Latin Extended A & B
                  0x1E00 <= code_point <= 0x1EFF or  # Latin Extended Additional
                  0x0100 <= code_point <= 0x017F or  # Latin Extended-A
                  0x0180 <= code_point <= 0x024F):   # Latin Extended-B
                latin_chars += 1
                
            else:
                # For unknown scripts, default to Latin (validator's behavior)
                latin_chars += 1
    
    # If no alphabetic characters, default to Latin
    if total_alpha_chars == 0:
        return True
    
    # Determine script based on validator's logic:
    # If ANY non-Latin characters are present, treat as non-Latin
    # This matches how the validator handles mixed scripts
    return non_latin_chars == 0  # True only if NO non-Latin characters


def split_name(name: str) -> tuple:
    """Split name into first and last name parts"""
    parts = name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])  # Handle multiple last names
        return first_name, last_name
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return "", ""


def combine_name_variations(first_variations: List[str], last_variations: List[str], 
                          original_first: str, original_last: str, target_count: int) -> List[str]:
    """Combine first and last name variations to produce exactly target_count combinations"""
    combinations = []
    used = set()
    
    # Original combination
    if original_last:
        original = f"{original_first} {original_last}"
    else:
        original = original_first
    
    # Combine exactly target_count variations (not max of both lists)
    for i in range(target_count):
        # Get variation at index i, or use original if no more variations
        first = first_variations[i] if i < len(first_variations) else original_first
        last = last_variations[i] if i < len(last_variations) else original_last
        
        # Create combination
        if last:
            combination = f"{first} {last}"
        else:
            combination = first
        
        # Add if unique and not original
        if combination.lower() not in used and combination != original:
            combinations.append(combination)
            used.add(combination.lower())
    
    return combinations


def generate_fallback_variations(name: str, needed_count: int) -> List[str]:
    """Generate fallback variations using simple methods"""
    variations = set()
    
    # Method 1: Basic phonetic transformations
    try:
        basic_vars = basic_generate_name_variations(name, limit=needed_count * 2)
        if basic_vars:
            variations.update(basic_vars)
    except Exception as e:
        print(f"Error in basic_generate_name_variations: {e}")
    
    # Method 2: Character-level transformations for the whole name
    name_clean = name.replace(' ', '')  # Work with name without spaces first
    
    # Remove characters
    for i in range(len(name_clean)):
        if name_clean[i].isalpha() and len(variations) < needed_count * 3:
            var = name_clean[:i] + name_clean[i+1:]
            if var and var != name_clean and len(var) > 1:
                variations.add(var)
    
    # Duplicate characters
    for i in range(len(name_clean)):
        if name_clean[i].isalpha() and len(variations) < needed_count * 3:
            var = name_clean[:i+1] + name_clean[i] + name_clean[i+1:]
            if var != name_clean:
                variations.add(var)
    
    # Swap adjacent characters
    for i in range(len(name_clean) - 1):
        if name_clean[i].isalpha() and name_clean[i+1].isalpha() and len(variations) < needed_count * 3:
            chars = list(name_clean)
            chars[i], chars[i+1] = chars[i+1], chars[i]
            var = ''.join(chars)
            if var != name_clean:
                variations.add(var)
    
    # Method 3: Simple phonetic substitutions
    simple_substitutions = [
        ('a', 'e'), ('e', 'i'), ('i', 'o'), ('o', 'u'), ('u', 'a'),
        ('b', 'p'), ('p', 'b'), ('d', 't'), ('t', 'd'), ('g', 'k'), ('k', 'g'),
        ('f', 'v'), ('v', 'f'), ('s', 'z'), ('z', 's'), ('c', 'k'), ('k', 'c'),
        ('m', 'n'), ('n', 'm'), ('l', 'r'), ('r', 'l')
    ]
    
    for old_char, new_char in simple_substitutions:
        if len(variations) >= needed_count * 3:
            break
        if old_char in name_clean.lower():
            var = name_clean.lower().replace(old_char, new_char)
            if var != name_clean.lower():
                variations.add(var)
    
    # Method 4: Part manipulations for multi-part names
    parts = name.split()
    if len(parts) >= 2:
        # Reverse parts
        reversed_name = ' '.join(parts[::-1])
        if reversed_name != name:
            variations.add(reversed_name)
        
        # Merge parts
        merged_name = ''.join(parts)
        if merged_name != name:
            variations.add(merged_name)
        
        # Different separators
        for sep in ['-', '_', '.']:
            sep_name = sep.join(parts)
            if sep_name != name:
                variations.add(sep_name)
        
        # Individual part variations
        for i, part in enumerate(parts):
            if len(part) > 2:  # Only modify parts with more than 2 characters
                # Remove first character
                var_part = part[1:]
                new_parts = parts.copy()
                new_parts[i] = var_part
                variations.add(' '.join(new_parts))
                
                # Remove last character
                var_part = part[:-1]
                new_parts = parts.copy()
                new_parts[i] = var_part
                variations.add(' '.join(new_parts))
    
    # Remove original name and empty variations
    variations.discard(name)
    variations.discard('')
    variations = {v for v in variations if v.strip()}
    
    result = list(variations)[:needed_count]
    # print(f"    fallback: {result}")
    return result

def generate_name_variations(
    original_name: str,
    variation_count: int,
    rule_percentage: float,
    rules: List[str] = [],
    phonetic_similarity: Dict[str, float] = None,
    orthographic_similarity: Dict[str, float] = None
) -> List[str]:
    """
    Generate name variations according to the specification.
    
    Args:
        original_name: The original name (e.g., "smith")
        variation_count: Number of variations to generate (e.g., 10)
        rule_percentage: Percentage of rule-based variations (e.g., 0.2)
        rules: List of rules to apply (e.g., ["remove_random_letter"])
        phonetic_similarity: Distribution dict (e.g., {"Light": 0.2, "Medium": 0.3, "Far": 0.5})
        orthographic_similarity: Distribution dict (e.g., {"Light": 0.2, "Medium": 0.3, "Far": 0.5})
    
    Returns:
        List of unique name variations
    """
    if phonetic_similarity is None:
        phonetic_similarity = {"Medium": 1.0}
    if orthographic_similarity is None:
        orthographic_similarity = {"Medium": 1.0}
        
    # Normalize similarity dictionaries to include all required keys with default values
    def normalize_similarity_dict(sim_dict: Dict[str, float]) -> Dict[str, float]:
        """Ensure all Light/Medium/Far keys exist with default 0.0 values"""
        normalized = {"Light": 0.0, "Medium": 0.0, "Far": 0.0}
        for key, value in sim_dict.items():
            if key in normalized:
                normalized[key] = value
        return normalized
    
    phonetic_similarity = normalize_similarity_dict(phonetic_similarity)
    orthographic_similarity = normalize_similarity_dict(orthographic_similarity)
    
    
    # Check if Latin or non-Latin
    # script = detect_script(original_name)
    # is_non_latin = (script != 'latin')
    is_non_latin = (detect_script(original_name) != True)
    
    all_variations = []
    used_variations = set([original_name.lower()])
    
    if is_non_latin:
        # NON-LATIN PATH
        print("-Using non-Latin generation path")
        
        # Split name into first/last parts
        first_name, last_name = split_name(original_name)
        
        # Initialize non-Latin optimizer
        non_latin_optimizer = NonLatinNameOptimizer()
        
        # Generate variations for each part
        first_variations = []
        last_variations = []
        
        if first_name:
            # Convert phonetic similarity to lowercase keys for compatibility
            phonetic_sim_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
            
            first_results = non_latin_optimizer.optimize_phonetic_selection(
                first_name, 
                variation_count,
                phonetic_sim_lower
            )
            first_variations = [result['variation'] for result in first_results]
        if last_name:
            # Convert phonetic similarity to lowercase keys for compatibility
            phonetic_sim_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
            
            last_results = non_latin_optimizer.optimize_phonetic_selection(
                last_name,
                variation_count,
                phonetic_sim_lower
            )
            last_variations = [result['variation'] for result in last_results]
        # Combine first/last name variations
        if first_variations or last_variations:
            combined_variations = combine_name_variations(
                first_variations, last_variations, first_name, last_name, variation_count
            )
            all_variations.extend(combined_variations)
        print(f"-Non-latin variations: {len(combined_variations)}")
        # Filter unique variations
        unique_variations = []
        for var in all_variations:
            if var.lower() not in used_variations:
                unique_variations.append(var)
                used_variations.add(var.lower())
        
        all_variations = unique_variations
    else:
        # LATIN PATH
        print("-Using Latin generation path")
        
        # Calculate rule and non-rule counts
        rule_count = int(variation_count * rule_percentage)
        non_rule_count = variation_count - rule_count
        
        # print(f"Rule-based: {rule_count}, Non-rule-based: {non_rule_count}")
        
        # Generate rule-based variations
        rule_variations = []
        if rule_count > 0:
            # print("Generating rule-based variations...")
            rule_generator = RuleBasedGenerator()
            rule_variations = rule_generator.generate_rule_based_variations(
                original_name, rule_count, rules
            )
            print(f"-Rule based {len(rule_variations)}")
        # Generate non-rule variations
        non_rule_variations = []
        if non_rule_count > 0:
            
            # Split name into first/last parts
            first_name, last_name = split_name(original_name)
            
            # Initialize optimizer
            optimizer = NameVariationOptimizer()
            
            # Generate variations for each part
            first_variations = []
            last_variations = []
            
            if first_name:
                # Convert similarity keys to lowercase for compatibility
                phonetic_sim_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
                orthographic_sim_lower = {k.lower(): v for k, v in orthographic_similarity.items()}
                
                first_results = optimizer.optimize_selection(
                    first_name,
                    non_rule_count,
                    phonetic_sim_lower,
                    orthographic_sim_lower
                )
                first_variations = [result['variation'] for result in first_results]
            
            if last_name:
                # Convert similarity keys to lowercase for compatibility
                phonetic_sim_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
                orthographic_sim_lower = {k.lower(): v for k, v in orthographic_similarity.items()}
                
                last_results = optimizer.optimize_selection(
                    last_name,
                    non_rule_count,
                    phonetic_sim_lower,
                    orthographic_sim_lower
                )
                last_variations = [result['variation'] for result in last_results]
            
            # Combine first/last name variations
            if first_variations or last_variations:
                combined_variations = combine_name_variations(
                    first_variations, last_variations, first_name, last_name, non_rule_count
                )
                non_rule_variations.extend(combined_variations)
            
            print(f"-Non-rule-based: {len(non_rule_variations)}")
        
        # Combine rule and non-rule variations
        all_variations = rule_variations + non_rule_variations
        
        # Filter unique variations
        unique_variations = []
        for var in all_variations:
            if var.lower() not in used_variations:
                unique_variations.append(var)
                used_variations.add(var.lower())
        
        all_variations = unique_variations
    # FALLBACK SYSTEM - if we don't have enough variations
    if len(all_variations) < variation_count:
        needed = variation_count - len(all_variations)
        print(f"****Need {needed} more variations, using fallback system...")
        
        fallback_variations = generate_fallback_variations(original_name, needed * 2)
        
        # Add unique fallback variations
        for var in fallback_variations:
            if len(all_variations) >= variation_count:
                break
            if var.lower() not in used_variations:
                all_variations.append(var)
                used_variations.add(var.lower())
        
    
    # Return exactly the requested count
    final_variations = all_variations[:variation_count]
    
    return final_variations


def score_variations(original_name: str, variations: List[str], 
                     phonetic_similarity: Dict[str, float],
                     orthographic_similarity: Dict[str, float],
                     rules: List[str], rule_percentage: float,
                     is_non_latin: bool = False) -> float:
    """
    Score variations using validator's scoring system
    
    Returns final score (prints detailed breakdown)
    """
    # Import validator modules
    validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
    if validator_path not in sys.path:
        sys.path.insert(0, validator_path)
    
    from module import calculate_variation_quality, calculate_variation_quality_phonetic_only
    
    if is_non_latin:
        # Non-Latin: phonetic-only scoring
        final_score = calculate_variation_quality_phonetic_only(
            original_name,
            variations,
            phonetic_similarity,
            expected_count=len(variations),
            verbose=True
        )
        return final_score
    else:
        # Latin: full scoring with rules
        rule_based_config = None
        if rules and rule_percentage > 0:
            rule_based_config = {
                "selected_rules": rules,
                "rule_percentage": int(rule_percentage * 100)
            }
        
        final_score = calculate_variation_quality(
            original_name,
            variations,
            phonetic_similarity,
            orthographic_similarity,
            expected_count=len(variations),
            rule_based=rule_based_config,
            verbose=True
        )
        
        return final_score


def main():
    """Example usage with validator scoring"""
    
    # ============================================================
    # TEST 1: Latin name
    # ============================================================
    print("=" * 60)
    print("Testing with Latin name: John Smith")
    print("=" * 60)
    
    latin_name = "John Smith"
    latin_rules = ["delete_random_letter", "swap_random_letter"]
    latin_phonetic = {"Light": 0.2, "Medium": 0.3, "Far": 0.5}
    latin_orthographic = {"Light": 0.2, "Medium": 0.3, "Far": 0.5}
    latin_rule_pct = 0.2
    
    latin_variations = ['John Smih', 'John Smtih', 'jouanne smithe', 'jouneau smeath', 'johnye schmidt', 'johan smithy', 'jouanny smythe', 'johm smedt', 'joyanne smead', 'johnas smed']
    
    
    # latin_variations = generate_name_variations(
    #     original_name=latin_name,
    #     variation_count=10,
    #     rule_percentage=latin_rule_pct,
    #     rules=latin_rules,
    #     phonetic_similarity=latin_phonetic,
    #     orthographic_similarity=latin_orthographic
    # )
    
    # Score with validator (prints detailed breakdown)
    latin_score = score_variations(
        latin_name, latin_variations,
        latin_phonetic, latin_orthographic,
        latin_rules, latin_rule_pct,
        is_non_latin=False
    )
    
    # ============================================================
    # TEST 2: Non-Latin name
    # ============================================================
    print("\n" + "=" * 60)
    print("Testing with non-Latin name: محمد علي")
    print("=" * 60)
    
    non_latin_name = "محمد علي"
    non_latin_phonetic = {"Light": 0.3, "Medium": 0.4, "Far": 0.3}
    
    non_latin_variations = generate_name_variations(
        original_name=non_latin_name,
        variation_count=8,
        rule_percentage=0.0,
        rules=[],
        phonetic_similarity=non_latin_phonetic
    )
    
    # Score with validator (prints detailed breakdown)
    non_latin_score = score_variations(
        non_latin_name, non_latin_variations,
        non_latin_phonetic, {"Medium": 1.0},
        [], 0.0,
        is_non_latin=True
    )
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Latin name score:     {latin_score:.4f}")
    print(f"Non-Latin name score: {non_latin_score:.4f}")


if __name__ == "__main__":
    main()
    # print(detect_script('alfred dupré'))