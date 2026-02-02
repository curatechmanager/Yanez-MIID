from typing import Set, List, Tuple
import unicodedata
import sys
import os

# --------------------------------------------------
# Validator import (UNCHANGED)
# --------------------------------------------------
validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
if validator_path not in sys.path:
    sys.path.insert(0, validator_path)

from module import calculate_phonetic_similarity, calculate_orthographic_similarity, has_excessive_letter_repetition

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


phonetic_boundaries = {
    "Light": (0.80, 0.99),
    "Medium": (0.60, 0.79),
    "Far": (0.30, 0.59)
}


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return name.lower()


# SUBS = {
#     "a": ["e"],
#     "e": ["a", "i"],
#     "i": ["e", "y"],
#     "o": ["u"],
#     "u": ["o"],
#     "y": ["i"],

#     "c": ["k", "s", "g", "j", "q", "x", "z"],
#     "k": ["c", "q", "ck", "g", "j", "x", "s", "z"],
#     "q": ["k", "s", "c", "g", "j", "x", "z"],
#     "ck": ["k"],

#     "s": ["k", "q", "c", "g", "j", "x", "z"],
#     "z": ["s", "C", "g", "j", "k", "q", "x"],

#     "f": ["ph", "v", "p", "b"],
#     "ph": ["f"],

#     "v": ["w", "f", "b", "p"],
#     "w": ["v"],

#     "g": ["k", "s", "c", "j", "q", "x", "z"],
#     "j": ["k", "s", "c", "g", "q", "x", "z"],

#     "x": ["ks", "c", "g", "j", "k", "q", "s", "z"],
#     "ks": ["x"],

#     "m": ["n"],
#     "n": ["m"],

#     "b": ["p", "f", "v"],
#     "p": ["b", "f", "v"],

#     "d": ["t"],
#     "t": ["d"],

#     "r": ["l"],
#     "l": ["r"],

#     "th": ["d", "t"],

#     "ch": ["sh"],
#     "sh": ["ch"],

#     "qu": ["kw"],

#     "dg": ["j"],
#     "dge": ["j"],

#     "wh": ["w"],
#     "wr": ["r"],

#     "kn": ["n"],
#     "gn": ["n"],

#     "ea": ["ee"],
#     "ie": ["ei"],
#     "ei": ["ie"],

#     "ou": ["ow"],
#     "ow": ["ou"],

#     "oo": ["u"],
#     "ee": ["i"],

#     "ai": ["ay"],
#     "ay": ["ai"],

#     "au": ["aw"],
#     "aw": ["au"],

#     "er": ["or"],
#     "or": ["er"],

#     "an": ["en"],
#     "en": ["an"]
# }
SUBS = {
    # -----------------------
    # LIGHT (minor drift)
    # -----------------------
    "a": ["e", "aa"],
    "e": ["i", "ee"],
    "i": ["y", "ie"],
    "o": ["u"],
    "u": ["o"],
    "y": ["i"],

    "m": ["n"],
    "n": ["m"],

    "d": ["t"],
    "t": ["d"],

    "r": ["l"],
    "l": ["r"],

    "b": ["p"],
    "p": ["b"],

    # -----------------------
    # MEDIUM (phonetic class shift)
    # -----------------------
    "c": ["k", "s"],
    "k": ["c", "q"],
    "q": ["k", "c"],

    "g": ["j", "k"],
    "j": ["g", "z"],

    "s": ["z", "sh"],
    "z": ["s", "j"],

    "f": ["ph", "v"],
    "v": ["f", "w"],
    "w": ["v"],

    "ch": ["sh"],
    "sh": ["ch"],

    "th": ["t", "d"],

    # -----------------------
    # FAR (structure breaking)
    # -----------------------


    "x": ["ks"],
    "ks": ["x"],

    # "ck": ["k"],
    "dge": ["j"],

    "qu": ["kw"],
    # "kw": ["k"],

    "an": ["en", "on"],
    "en": ["an", "in"],

    "er": ["ar", "or"],
    "or": ["er", "ur"],

    "ou": ["ow", "u"],
    "oo": ["u"],

    "ai": ["ay", "e"],
    "ay": ["ai", "i"]
}


INSERT_CHARS = list("aeioubcdfghjklmnprstvwxyz")


def generate_simple_fallbacks(name: str, needed_count: 10) -> list:
    """Generate length-aware simple fallback variations when other methods don't produce enough"""
    cleaned = []
    variations = []
    name_lower = name.lower()
    original_len = len(name_lower)
    
    # PHASE 1: Same-length substitutions (HIGHEST PRIORITY)
    substitutions = [
        ('a', 'e'), ('e', 'a'), ('i', 'y'), ('y', 'i'),
        ('o', 'u'), ('u', 'o'), ('c', 'k'), ('k', 'c'),
        ('s', 'z'), ('z', 's'), ('b', 'p'), ('p', 'b'), 
        ('d', 't'), ('t', 'd'), ('v', 'f'), ('f', 'v'), 
        ('r', 'l'), ('l', 'r'), ('n', 'm'), ('m', 'n')
    ]
    
    # Apply same-length substitutions first
    for old_char, new_char in substitutions:
        if old_char in name_lower:
            variation = name_lower.replace(old_char, new_char)
            if is_valid_variation(variation, name, variations):
                variations.append(variation)
                for v in variations:
                    s = calculate_phonetic_similarity(name, v)
                    if 0.8 < s < 0.99:
                        cleaned.append(v)
                        if len(cleaned) >= needed_count:
                            return cleaned
            if len(cleaned) >= needed_count:
                break
    
    # PHASE 2: Length-changing substitutions (MEDIUM PRIORITY)
    length_changing_substitutions = [
        ('ph', 'f'), ('f', 'ph'), ('ck', 'k'), ('k', 'ck')
    ]
    
    for old_char, new_char in length_changing_substitutions:
        if old_char in name_lower:
            variation = name_lower.replace(old_char, new_char)
            if is_valid_variation(variation, name, variations):
                variations.append(variation)
                for v in variations:
                    s = calculate_phonetic_similarity(name, v)
                    if 0.8 < s < 0.99:
                        cleaned.append(v)
                        if len(cleaned) >= needed_count:
                            return cleaned
            if len(cleaned) >= needed_count:
                break
    
    # PHASE 3: Character insertions (LOW PRIORITY - only for short names)
    if len(variations) < needed_count and original_len <= 5:
        common_chars = 'aeiourlnstm'
        for i in range(len(name_lower)):
            for char in common_chars:
                variation = name_lower[:i] + char + name_lower[i:]
                if is_valid_variation(variation, name, variations):
                    variations.append(variation)
                    for v in variations:
                        s = calculate_phonetic_similarity(name, v)
                        if 0.8 < s < 0.99:
                            cleaned.append(v)
                            if len(cleaned) >= needed_count:
                                return cleaned
                if len(cleaned) >= needed_count:
                    break
    
    # PHASE 4: Character deletions (LOW PRIORITY - only for longer names)
    if len(variations) < needed_count and original_len > 4:
        for i in range(len(name_lower)):
            variation = name_lower[:i] + name_lower[i+1:]
            if is_valid_variation(variation, name, variations):
                variations.append(variation)
                for v in variations:
                    s = calculate_phonetic_similarity(name, v)
                    if 0.8 < s < 0.99:
                        cleaned.append(v)
                        if len(cleaned) >= needed_count:
                            return cleaned
            if len(cleaned) >= needed_count:
                break
    
    return cleaned[:needed_count]


def substitutions(name: str) -> Set[str]:
    out = set()
    for i, c in enumerate(name):
        if c in SUBS:
            for r in SUBS[c]:
                out.add(name[:i] + r + name[i + 1:])
    return out


def insertions(name: str) -> Set[str]:
    out = set()
    for i in range(len(name) + 1):
        for c in INSERT_CHARS:
            out.add(name[:i] + c + name[i:])
    return out


def deletions(name: str) -> Set[str]:
    return {
        name[:i] + name[i + 1:]
        for i in range(len(name))
        if len(name) > 1
    }


def transpositions(name: str) -> Set[str]:
    return {
        name[:i] + name[i + 1] + name[i] + name[i + 2:]
        for i in range(len(name) - 1)
        if name[i] != name[i + 1]
    }


def expand_edits(base: str, max_edits: int) -> Set[str]:
    all_variations = {base}
    current = {base}

    for _ in range(max_edits):
        nxt = set()
        for v in current:
            nxt |= substitutions(v)
            nxt |= insertions(v)
            nxt |= deletions(v)
            nxt |= transpositions(v)

        nxt -= all_variations
        all_variations |= nxt
        current = nxt

    return all_variations


def generate_name_variations_all_boundaries_with_scores(
    name: str,
    max_edits: int = 1,
    max_results: int = 500
) -> List[Tuple[str, float, str]]:

    original = name
    base = normalize_name(name)
    results = []

    candidates = expand_edits(base, max_edits)

    for boundary, (low, high) in phonetic_boundaries.items():
        for v in candidates:
            s = calculate_phonetic_similarity(original, v)
            if 0.3 < s < 0.99 and 2 <= len(v) <= 20 and low <= s <= high:
                results.append((v, s, boundary))

    # Deduplicate: keep best score
    best = {}
    for v, s, b in results:
        if v not in best or s > best[v][1]:
            best[v] = (v, s, b)

    final = list(best.values())
    final.sort(key=lambda x: x[1], reverse=True)

    return final[:max_results]

def generate_name_variations_all_boundaries_latin(
    name: str,
    max_edits: int = 1,
    max_results: int = 500
) -> List[Tuple[str, float, str]]:

    original = name
    base = normalize_name(name)
    results = []

    candidates = expand_edits(base, max_edits)

    for boundary, (low, high) in phonetic_boundaries.items():
        for v in candidates:
            s = calculate_phonetic_similarity(original, v)
            if 0.3 <= s <= 1.0 and low <= s <= high:
                results.append((v, s, boundary))

    # Deduplicate: keep best score
    best = {}
    for v, s, b in results:
        if v not in best or s > best[v][1]:
            best[v] = (v, s, b)

    final = list(best.values())
    final.sort(key=lambda x: x[1], reverse=True)

    return final[:max_results]


def generate_name_variations_with_scores(
    name: str,
    boundary: str = "Medium",
    max_edits: int = 1,
    max_results: int = 500
) -> List[Tuple[str, float]]:

    original = name
    base = normalize_name(name)
    low, high = phonetic_boundaries[boundary]

    candidates = expand_edits(base, max_edits)
    scored = []

    for v in candidates:
        s = calculate_phonetic_similarity(original, v)
        if 0.3 < s < 0.99 and low <= s <= high:
            scored.append((v, s))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:max_results]


def clean_phonetic_variation(name: str) -> List[Tuple[str, str]]:
    import random
    
    # Collect all variations with their boundaries
    all_variations = []
    
    # Run the same (0, 1, 2) edit logic
    for edits in (0, 1, 2):
        res = generate_name_variations_all_boundaries_with_scores(
            name,
            max_edits=edits,
            max_results=500
        )
        all_variations.extend(res)  # Keep (v, s, b) format
    
    # Validate all variations using is_valid_variation function
    valid_variations = []
    existing_vars = []  # Track existing variations for uniqueness check
    
    for v, s, b in all_variations:
        if is_valid_variation(v, name, existing_vars):
            valid_variations.append((v, s, b))
            existing_vars.append(v)
    
    # Remove duplicates while keeping the best score for each variation
    best_variations = {}
    for v, s, b in valid_variations:
        if v not in best_variations or s > best_variations[v][1]:
            best_variations[v] = (v, s, b)
    
    # Group variations by boundary
    boundary_variations = {
        "Light": [],
        "Medium": [],
        "Far": []
    }
    
    for v, s, b in best_variations.values():
        boundary_variations[b].append((v, s))
    
    # Sort each boundary by score (highest first)
    for boundary in boundary_variations:
        boundary_variations[boundary].sort(key=lambda x: x[1], reverse=True)
    
    # Extract 10 variations from each boundary
    final = []
    target_per_boundary = 10
    total_target = 30
    
    # First pass: try to get 10 from each boundary
    remaining_slots = {}
    for boundary in ["Light", "Medium", "Far"]:
        available = boundary_variations[boundary]
        selected = available[:target_per_boundary]
        final.extend(selected)
        remaining_slots[boundary] = target_per_boundary - len(selected)
    
    # Second pass: fill remaining slots from other boundaries
    if len(final) < total_target:
        # Collect unused variations from all boundaries
        unused_variations = []
        for boundary in ["Light", "Medium", "Far"]:
            unused = boundary_variations[boundary][target_per_boundary:]
            unused_variations.extend(unused)
        
        # Sort unused by score and take what we need
        unused_variations.sort(key=lambda x: x[1], reverse=True)
        needed = total_target - len(final)
        final.extend(unused_variations[:needed])
    
    # Ensure we don't exceed 30 variations
    final = final[:total_target]
    
    # Shuffle to randomize the selection within boundaries as requested
    random.shuffle(final)
    
    return final


def clean_phonetic_orthographic_variation(name: str) -> List[Tuple[str, Tuple[float, float]]]:
    # Collect all variations with their boundaries
    all_variations = []
    
    # Run the same (0, 1, 2) edit logic
    for edits in (0, 1, 2):
        res = generate_name_variations_all_boundaries_latin(
            name,
            max_edits=edits,
            max_results=500
        )
        all_variations.extend(res)  # Keep (v, s, b) format
    
    # Validate all variations using is_valid_variation function
    valid_variations = []
    existing_vars = []  # Track existing variations for uniqueness check
    
    for v, s, b in all_variations:
        if is_valid_variation(v, name, existing_vars):
            valid_variations.append((v, s, b))
            existing_vars.append(v)
    
    # Now process existing_vars according to the requirements
    # Note: phonetic score of all vars is already in 0.3 to 0.99 from generate_name_variations_all_boundaries_with_scores
    
    filtered_vars = []
    
    # Calculate orthographic scores and apply filters
    for i, (var, phonetic_score, boundary) in enumerate(valid_variations):
        # Filter 3: 2 < len(var) < 20 (character length of the variation)
        if len(var) <= 2 or len(var) >= 20:
            continue
            
        # Calculate orthographic score
        orthographic_score = calculate_orthographic_similarity(name, var)
        
        # Filter 1: orthographic score > 0.2
        if orthographic_score <= 0.2:
            continue
            
        # Filter 2: (phonetic score * 0.7 + orthographic score * 0.3) < 0.99
        combined_score = phonetic_score * 0.7 + orthographic_score * 0.3
        if combined_score >= 0.99:
            continue
            
        # Add to filtered list with required format: var, (phonetic_score, orthographic_score)
        filtered_vars.append((var, (phonetic_score, orthographic_score)))
    # print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\n", filtered_vars)
    return filtered_vars


if __name__ == "__main__":
    name = "Joshep"
    
    print("Testing clean_phonetic_variation:")
    for v, b in clean_phonetic_variation(name):
        print(f"{v:<15} ({b})")
    
    print("\nTesting clean_phonetic_orthographic_variation:")
    ortho_results = clean_phonetic_orthographic_variation(name)
    print(f"Found {len(ortho_results)} variations that meet all criteria:")
    for var, (p_score, o_score) in ortho_results:
        combined = p_score * 0.7 + o_score * 0.3
        print(f"{var:<15} (P:{p_score:.3f}, O:{o_score:.3f}, Combined:{combined:.3f})")
