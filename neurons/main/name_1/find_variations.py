"""
Find raw name variations from OpenAI API seed data and rule-based generation
"""
import sys
import os
from algorithm_fallback import clean_phonetic_variation, clean_phonetic_orthographic_variation

# Add validator path
validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
if validator_path not in sys.path:
    sys.path.insert(0, validator_path)
from module import has_excessive_letter_repetition

phonetic_boundaries = {
    "Light": (0.80, 0.99),
    "Medium": (0.60, 0.79),
    "Far": (0.30, 0.59)
}

orthographic_boundaries = {
    "Light": (0.70, 1.00),
    "Medium": (0.50, 0.69),
    "Far": (0.20, 0.49)
}

def is_length_appropriate(variation: str, original: str) -> bool:
    """Check if variation length is appropriate according to validator scoring criteria"""
    original_len = len(original)
    var_len = len(variation)
    
    # Apply validator's length criteria with slight relaxation for better similarity
    if original_len <= 5:
        min_ratio = 0.55  # Slightly relaxed from 0.6 for better similarity options
        acceptable_range = [max(1, original_len-1), original_len+2]
    else:
        min_ratio = 0.65  # Slightly relaxed from 0.7 for better similarity options
        acceptable_range = [original_len-1, original_len+2]  # Allow +2 for longer names too
    
    # Check if variation length is in acceptable range
    if var_len < acceptable_range[0] or var_len > acceptable_range[1]:
        return False
    
    # Check length ratio
    if original_len > 0:
        length_ratio = min(var_len / original_len, original_len / var_len)
        if length_ratio < min_ratio:
            return False
    
    return True


def is_valid_variation(variation: str, original: str, existing_vars: list) -> bool:
    """Check if variation is valid with exact uniqueness and appropriate length"""
    if not variation or variation.lower() == original.lower():
        return False
    
    if has_excessive_letter_repetition(variation, max_repetition=2):
        return False
    
    # Check length appropriateness according to validator criteria
    if not is_length_appropriate(variation, original):
        return False
    
    # UPDATED: Use exact string matching instead of similarity threshold for guaranteed uniqueness
    if variation.lower() in [v.lower() for v in existing_vars]:
        return False
    
    return True



def generate_simple_fallbacks(name: str, needed_count: int, final_goal: dict) -> list:
    """
    Generate variations matching final_goal distribution step by step.
    For each case in final_goal, generate variations until that case is satisfied.
    
    Example: {('M','F'):2, ('F','F'):4, ('M','M'):3, ('L','L'):1}
    - First generate 2 variations with ('M','F')
    - Then generate 4 variations with ('F','F')
    - Then generate 3 variations with ('M','M')
    - Finally generate 1 variation with ('L','L')
    """
    from module import calculate_phonetic_similarity, calculate_orthographic_similarity
    import random
    
    name = name.lower()
    generated = []
    
    def create_diverse_candidates(base):
        """Generate MANY diverse candidate variations"""
        cands = set()  # Use set to avoid duplicates
        
        # LIGHT: Single character substitutions
        for i, ch in enumerate(base):
            if ch in 'aeiou':
                for v in 'aeiouy':
                    if v != ch:
                        cands.add(base[:i] + v + base[i+1:])
            # Double letters
            cands.add(base[:i+1] + base[i] + base[i+1:])
        
        # MEDIUM: Phonetic substitutions
        phonetic_pairs = [
            ('c','k'),('k','c'),('ph','f'),('f','ph'),('s','c'),('c','s'),
            ('ck','k'),('z','s'),('s','z'),('x','ks'),('th','t'),('ch','sh')
        ]
        for old, new in phonetic_pairs:
            if old in base:
                cands.add(base.replace(old, new, 1))
                cands.add(base.replace(old, new))
        
        # Letter swapping
        for i in range(len(base) - 1):
            cands.add(base[:i] + base[i+1] + base[i] + base[i+2:])
        
        # Consonant substitutions
        cons_pairs = [
            ('b','p'),('p','b'),('d','t'),('t','d'),('g','k'),('k','g'),
            ('v','f'),('f','v'),('j','g'),('g','j'),('m','n'),('n','m'),
            ('s','z'),('z','s'),('r','l'),('l','r'),('w','v'),('v','w')
        ]
        for i, ch in enumerate(base):
            for old, new in cons_pairs:
                if ch == old:
                    cands.add(base[:i] + new + base[i+1:])
        
        # FAR: Shortened forms and major changes
        if len(base) > 4:
            cands.add(base[:len(base)//2])
            cands.add(base[:3])
            cands.add(base[:4])
            cands.add(base[1:])
            cands.add(base[:-1])
            cands.add(base[:-2])
            if len(base) > 5:
                cands.add(base[2:])
                cands.add(base[:len(base)-2])
        
        # Multiple substitutions for FAR similarity
        if len(base) > 3:
            # Double vowel changes
            for v1, v2 in [('a','o'),('e','i'),('i','a'),('o','u')]:
                temp = base
                if v1 in temp:
                    temp = temp.replace(v1, v2, 1)
                    if v1 in temp:
                        temp = temp.replace(v1, v2, 1)
                    if temp != base:
                        cands.add(temp)
            
            # Vowel + consonant changes
            for v1, v2 in [('a','e'),('i','y')]:
                for c1, c2 in [('d','t'),('v','f'),('s','z')]:
                    if v1 in base and c1 in base:
                        cands.add(base.replace(v1, v2, 1).replace(c1, c2, 1))
        
        # Character deletions
        if len(base) > 4:
            for i in range(len(base)):
                cands.add(base[:i] + base[i+1:])
        
        # Add endings
        if len(base) > 3:
            for end in ['a','o','i','e','y']:
                cands.add(base + end)
        
        # Remove first/last 2 chars
        if len(base) > 5:
            cands.add(base[2:])
            cands.add(base[:-2])
        
        return list(cands)
    
    # Generate ALL candidates once
    all_candidates = create_diverse_candidates(name)
    random.shuffle(all_candidates)
    
    # Score and organize into pools by similarity pair
    pools = {}  # {('L','L'): [vars], ('M','F'): [vars], ...}
    
    for cand in all_candidates:
        if not is_valid_variation(cand, name, []):
            continue
        
        try:
            p_sc = calculate_phonetic_similarity(name, cand)
            o_sc = calculate_orthographic_similarity(name, cand)
            
            # Determine levels
            if 0.80 <= p_sc <= 1.00:
                p_lv = 'L'
            elif 0.60 <= p_sc < 0.80:
                p_lv = 'M'
            elif 0.30 <= p_sc < 0.60:
                p_lv = 'F'
            else:
                continue
            
            if 0.70 <= o_sc <= 1.00:
                o_lv = 'L'
            elif 0.50 <= o_sc < 0.70:
                o_lv = 'M'
            elif 0.20 <= o_sc < 0.50:
                o_lv = 'F'
            else:
                continue
            
            pair = (p_lv, o_lv)
            if pair not in pools:
                pools[pair] = []
            pools[pair].append(cand)
        except:
            continue
    
    # Now select from pools step by step for each goal case
    for target_pair, target_count in final_goal.items():
        if target_pair in pools:
            available = pools[target_pair]
            for cand in available:
                if target_count <= 0:
                    break
                if is_valid_variation(cand, name, generated):
                    generated.append(cand)
                    target_count -= 1
    
    # If still short, fill with any valid variations
    if len(generated) < needed_count:
        for pool_list in pools.values():
            for cand in pool_list:
                if len(generated) >= needed_count:
                    break
                if is_valid_variation(cand, name, generated):
                    generated.append(cand)
    
    return generated[:needed_count]


def latin_variations(single_name: str, target_count: int, final_goal: dict) -> list:
    try:
        from module import calculate_phonetic_similarity, calculate_orthographic_similarity
        
        raw = clean_phonetic_orthographic_variation(single_name)
        
        if not raw:
            return []
        
        # Classify variations by boundary combinations
        boundary_variations = {}
        all_variations = []  # Keep track of all processed variations
        
        for item in raw:
            # Handle different data structures from clean_phonetic_orthographic_variation
            if len(item) == 2:
                # If only 2 values, assume it's (variation, combined_score) or similar
                variation, score = item
                # Calculate both scores manually
                phonetic_score = calculate_phonetic_similarity(single_name, variation)
                orthographic_score = calculate_orthographic_similarity(single_name, variation)
            elif len(item) == 3:
                # If 3 values, assume it's (variation, phonetic_score, orthographic_score)
                variation, phonetic_score, orthographic_score = item
            else:
                continue  # Skip malformed items
            
            # Determine phonetic boundary
            phonetic_boundary = None
            if phonetic_boundaries["Light"][0] <= phonetic_score <= phonetic_boundaries["Light"][1]:
                phonetic_boundary = 'L'
            elif phonetic_boundaries["Medium"][0] <= phonetic_score <= phonetic_boundaries["Medium"][1]:
                phonetic_boundary = 'M'
            elif phonetic_boundaries["Far"][0] <= phonetic_score <= phonetic_boundaries["Far"][1]:
                phonetic_boundary = 'F'
            
            # Determine orthographic boundary
            orthographic_boundary = None
            if orthographic_boundaries["Light"][0] <= orthographic_score <= orthographic_boundaries["Light"][1]:
                orthographic_boundary = 'L'
            elif orthographic_boundaries["Medium"][0] <= orthographic_score <= orthographic_boundaries["Medium"][1]:
                orthographic_boundary = 'M'
            elif orthographic_boundaries["Far"][0] <= orthographic_score <= orthographic_boundaries["Far"][1]:
                orthographic_boundary = 'F'
            
            # Skip if boundaries couldn't be determined
            if phonetic_boundary is None or orthographic_boundary is None:
                continue
            
            variation_data = (variation, phonetic_score, orthographic_score, phonetic_boundary, orthographic_boundary)
            all_variations.append(variation_data)
            
            boundary_pair = (phonetic_boundary, orthographic_boundary)
            if boundary_pair not in boundary_variations:
                boundary_variations[boundary_pair] = []
            
            boundary_variations[boundary_pair].append(variation_data)
        
        # Sort each boundary group by combined score (phonetic + orthographic)
        for boundary_pair in boundary_variations:
            boundary_variations[boundary_pair].sort(
                key=lambda x: (x[1] + x[2]) / 2, reverse=True
            )
        
        extracted_variations = []
        remaining_goals = final_goal.copy()
        
        # First pass: Extract exact matches for each boundary combination
        for boundary_pair, needed_count in final_goal.items():
            if boundary_pair in boundary_variations:
                available = boundary_variations[boundary_pair]
                selected = available[:needed_count]
                for var_data in selected:
                    extracted_variations.append(var_data[0])  # Just the variation name
                remaining_goals[boundary_pair] -= len(selected)
        
        # Enhanced backfill logic
        total_extracted = len(extracted_variations)
        total_needed = sum(final_goal.values())
        
        if total_extracted < total_needed:
            # Get all unused variations
            used_variations = set(extracted_variations)
            unused_variations = [var_data for var_data in all_variations if var_data[0] not in used_variations]
            
            # Sort unused by combined score
            unused_variations.sort(key=lambda x: (x[1] + x[2]) / 2, reverse=True)
            
            # Group unused variations by boundaries
            orthographic_groups = {'L': [], 'M': [], 'F': []}
            phonetic_groups = {'L': [], 'M': [], 'F': []}
            
            for var_data in unused_variations:
                var, p_score, o_score, p_boundary, o_boundary = var_data
                orthographic_groups[o_boundary].append(var_data)
                phonetic_groups[p_boundary].append(var_data)
            
            # Backfill strategy for each remaining goal
            for boundary_pair, original_count in final_goal.items():
                remaining_for_this_goal = remaining_goals[boundary_pair]
                if remaining_for_this_goal <= 0:
                    continue
                
                phonetic_b, orthographic_b = boundary_pair
                still_needed = total_needed - len(extracted_variations)
                if still_needed <= 0:
                    break
                
                # Strategy 1: Try orthographic boundary match first
                available_ortho = [var_data for var_data in orthographic_groups[orthographic_b] 
                                 if var_data[0] not in extracted_variations]
                
                take_count = min(remaining_for_this_goal, len(available_ortho), still_needed)
                for i in range(take_count):
                    var_data = available_ortho[i]
                    extracted_variations.append(var_data[0])
                    remaining_for_this_goal -= 1
                    # Remove from all groups to avoid duplicates
                    for group in orthographic_groups.values():
                        if var_data in group:
                            group.remove(var_data)
                    for group in phonetic_groups.values():
                        if var_data in group:
                            group.remove(var_data)
                
                # Strategy 2: If still need more, try phonetic boundary match
                if remaining_for_this_goal > 0:
                    still_needed = total_needed - len(extracted_variations)
                    if still_needed > 0:
                        available_phonetic = [var_data for var_data in phonetic_groups[phonetic_b] 
                                            if var_data[0] not in extracted_variations]
                        
                        take_count = min(remaining_for_this_goal, len(available_phonetic), still_needed)
                        for i in range(take_count):
                            var_data = available_phonetic[i]
                            extracted_variations.append(var_data[0])
                            remaining_for_this_goal -= 1
                            # Remove from all groups to avoid duplicates
                            for group in orthographic_groups.values():
                                if var_data in group:
                                    group.remove(var_data)
                            for group in phonetic_groups.values():
                                if var_data in group:
                                    group.remove(var_data)
                
                # Update remaining goals
                remaining_goals[boundary_pair] = remaining_for_this_goal
            
            # Strategy 3: If still need more, get any remaining variations
            still_needed = total_needed - len(extracted_variations)
            if still_needed > 0:
                # Get all remaining unused variations
                all_remaining = []
                for group in orthographic_groups.values():
                    all_remaining.extend(group)
                
                # Remove duplicates and sort by score
                seen = set()
                unique_remaining = []
                for var_data in all_remaining:
                    if var_data[0] not in seen and var_data[0] not in extracted_variations:
                        unique_remaining.append(var_data)
                        seen.add(var_data[0])
                
                unique_remaining.sort(key=lambda x: (x[1] + x[2]) / 2, reverse=True)
                
                # Take what we need
                take_count = min(still_needed, len(unique_remaining))
                for i in range(take_count):
                    extracted_variations.append(unique_remaining[i][0])
        print("==================LATIN=====================\n", extracted_variations)
        return extracted_variations[:target_count]
        
    except Exception as e:
        print(f"ERROR in latin_variations: {e}")
        return []


def non_latin_variations(single_name: str, target_count: int, goal_phonetic: dict) -> list:
    try:
        non_latin = []
        raw = clean_phonetic_variation(single_name)
        # Group variations by boundary based on their scores
        boundary_variations = {
            "Light": [],
            "Medium": [],
            "Far": []
        }
        
        # Classify each variation into boundaries based on phonetic_boundaries
        for variation, score in raw:
            if phonetic_boundaries["Light"][0] <= score <= phonetic_boundaries["Light"][1]:
                boundary_variations["Light"].append((variation, score))
            elif phonetic_boundaries["Medium"][0] <= score <= phonetic_boundaries["Medium"][1]:
                boundary_variations["Medium"].append((variation, score))
            elif phonetic_boundaries["Far"][0] <= score <= phonetic_boundaries["Far"][1]:
                boundary_variations["Far"].append((variation, score))
        
        # Sort each boundary by score (highest first)
        for boundary in boundary_variations:
            boundary_variations[boundary].sort(key=lambda x: x[1], reverse=True)
        
        # Extract variations according to goal_phonetic
        extracted_variations = []
        total_needed = sum(goal_phonetic.values())
        
        # First pass: try to get exact count from each boundary
        remaining_needed = {}
        for boundary, needed_count in goal_phonetic.items():
            available = boundary_variations[boundary]
            selected = available[:needed_count]
            extracted_variations.extend([var for var, score in selected])
            remaining_needed[boundary] = needed_count - len(selected)
        
        # Second pass: fill remaining slots from other boundaries if needed
        if len(extracted_variations) < total_needed:
            # Collect unused variations from all boundaries
            unused_variations = []
            for boundary in ["Light", "Medium", "Far"]:
                used_count = goal_phonetic.get(boundary, 0)
                unused = boundary_variations[boundary][used_count:]
                unused_variations.extend(unused)
            
            # Sort unused by score and take what we need
            unused_variations.sort(key=lambda x: x[1], reverse=True)
            needed = total_needed - len(extracted_variations)
            for var, score in unused_variations[:needed]:
                extracted_variations.append(var)
        
        # Ensure we don't exceed total_needed
        non_latin = extracted_variations[:total_needed]
        # print("NNNNNNNNNNNNNNNNNNNNNNNNNNNN", non_latin)
        return non_latin
    except Exception as e:
        print(f"ERROR in non_latin_variations: {e}")
        return []
