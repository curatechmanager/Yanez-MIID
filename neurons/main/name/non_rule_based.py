"""
Name Variation Optimizer - Aligned with Validator Scoring System

Scoring Weights (from validator):
- similarity_weight: 60% (phonetic + orthographic combined)
- count_weight: 15%
- uniqueness_weight: 10%
- length_weight: 15%

Similarity Boundaries:
- Phonetic: Light (0.80-1.00), Medium (0.60-0.79), Far (0.30-0.59)
- Orthographic: Light (0.70-1.00), Medium (0.50-0.69), Far (0.20-0.49)

IMPORTANT: Non-rule variations that accidentally pass rule checks get moved to
rule_compliant_variations, reducing the non_rule_compliant count and hurting scores.
This optimizer prioritizes variations that DON'T pass rule checks.
"""

import random
import jellyfish
import Levenshtein
import math
import re
from typing import List, Dict, Tuple, Set


class NameVariationOptimizer:
    def __init__(self):
        # Phonetic transforms organized by target similarity level
        self.phonetic_transforms = {
            'light': [
                ('ph', 'f'), ('ck', 'k'), ('qu', 'kw'), ('x', 'ks'),
                ('c', 'k'), ('s', 'z'), ('z', 's'),
                ('i', 'y'), ('y', 'i'),
                ('tion', 'shun'), ('sion', 'zhun'),
                ('dg', 'j'), ('dge', 'j'),
                ('wh', 'w'), ('wr', 'r'),
                ('kn', 'n'), ('gn', 'n'),
                ('ea', 'ee'), ('ie', 'i'), ('ei', 'i'),
                ('ou', 'u'), ('ow', 'ou')
            ],
            'medium': [
                ('b', 'p'), ('p', 'b'),
                ('d', 't'), ('t', 'd'),
                ('g', 'k'), ('k', 'g'),
                ('v', 'f'), ('f', 'v'),
                ('j', 'g'), ('g', 'j'),
                ('th', 'd'), ('th', 't'),
                ('ch', 'sh'), ('sh', 'ch'),
                ('oo', 'u'), ('ee', 'i'),
                ('ou', 'ow'), ('ow', 'o'),
                ('ai', 'ay'), ('ay', 'e'),
                ('au', 'aw'), ('aw', 'au')
            ],
            'far': [
                ('r', 'l'), ('l', 'r'),
                ('n', 'm'), ('m', 'n'),
                ('w', 'v'), ('v', 'w'),
                ('h', ''),
                ('gh', ''),
                ('a', 'e'), ('e', 'i'), ('i', 'o'), ('o', 'u'), ('u', 'a'),
                ('ll', 'l'), ('ss', 's'), ('tt', 't'), ('nn', 'n'),
                ('ph', 'p'), ('c', 's'), ('k', 'q'),
                ('y', 'ie'), ('ie', 'y')
            ]
        }
        
        self.orthographic_transforms = {
            'light': [
                ('ie', 'y'), ('y', 'ie'),
                ('ph', 'f'), ('f', 'ph'),
                ('ck', 'k'), ('k', 'ck'),
                ('c', 'k'), ('k', 'c'),
                ('s', 'z'), ('z', 's'),
                ('ee', 'i'), ('i', 'ee'),
                ('oo', 'u'), ('u', 'oo'),
                ('ai', 'ay'), ('ay', 'ai'),
                ('ou', 'ow'), ('ow', 'ou'),
                ('tion', 'shun'), ('sion', 'zhun'),
                ('ll', 'l'), ('ss', 's'),
                ('dge', 'j'), ('dg', 'j')
            ],
            'medium': [
                ('a', 'e'), ('e', 'a'),
                ('i', 'y'), ('y', 'i'),
                ('o', 'u'), ('u', 'o'),
                ('er', 'or'), ('or', 'er'),
                ('an', 'en'), ('en', 'an'),
                ('ie', 'ei'), ('ei', 'ie'),
                ('au', 'aw'), ('aw', 'au'),
                ('ck', 'q'), ('q', 'ck'),
                ('th', 't'), ('t', 'th')
            ],
            'far': [
                ('a', 'i'), ('i', 'a'),
                ('e', 'o'), ('o', 'e'),
                ('i', 'o'), ('o', 'i'),
                ('m', 'n'), ('n', 'm'),
                ('r', 'l'), ('l', 'r'),
                ('w', 'v'), ('v', 'w'),
                ('h', ''),
                ('gh', ''),
                ('ck', 'k'),
                ('ph', 'p'),
                ('y', 'i'), ('i', 'y')
            ]
        }
        
        # Validator's exact boundaries
        self.phonetic_boundaries = {
            "light": (0.80, 1.00),
            "medium": (0.60, 0.79),
            "far": (0.30, 0.59)
        }
        
        self.orthographic_boundaries = {
            "light": (0.70, 1.00),
            "medium": (0.50, 0.69),
            "far": (0.20, 0.49)
        }
        
        # Validator's exact weights
        self.WEIGHTS = {
            "similarity": 0.60,
            "count": 0.15,
            "uniqueness": 0.10,
            "length": 0.15
        }

    def has_excessive_letter_repetition(self, text: str, max_repetition: int = 2) -> bool:
        """Check if text has excessive letter repetition."""
        if not text:
            return False
        pattern = r'(.)\1{' + str(max_repetition) + r',}'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def passes_rule_check(self, original: str, variation: str) -> bool:
        """
        Check if variation would pass any of the validator's rule checks.
        If True, this variation will be moved to rule_compliant_variations.
        """
        original_lower = original.lower()
        variation_lower = variation.lower()
        
        if original_lower == variation_lower:
            return False
        
        vowels = 'aeiou'
        
        # Check: is_letters_swapped (exactly 2 adjacent positions swapped)
        if len(original) == len(variation):
            diffs = []
            for i in range(len(original)):
                if original[i] != variation[i]:
                    diffs.append(i)
            if len(diffs) == 2 and abs(diffs[0] - diffs[1]) == 1:
                if (original[diffs[0]] == variation[diffs[1]] and
                    original[diffs[1]] == variation[diffs[0]]):
                    return True
        
        # Check: is_letter_removed (length -1, Levenshtein 1)
        if len(variation) == len(original) - 1:
            if Levenshtein.distance(original, variation) == 1:
                return True
        
        # Check: is_vowel_replaced (same length, vowel→vowel, <=1 other change)
        if len(original_lower) == len(variation_lower):
            vowel_changes = 0
            other_changes = 0
            for i in range(len(original_lower)):
                if original_lower[i] != variation_lower[i]:
                    if original_lower[i] in vowels and variation_lower[i] in vowels:
                        vowel_changes += 1
                    else:
                        other_changes += 1
            if vowel_changes >= 1 and other_changes <= 1:
                return True
        
        # Check: is_consonant_replaced (same length, consonant→consonant, <=1 other)
        if len(original_lower) == len(variation_lower):
            consonant_changes = 0
            other_changes = 0
            for i in range(len(original_lower)):
                if original_lower[i] != variation_lower[i]:
                    o_cons = original_lower[i].isalpha() and original_lower[i] not in vowels
                    v_cons = variation_lower[i].isalpha() and variation_lower[i] not in vowels
                    if o_cons and v_cons:
                        consonant_changes += 1
                    else:
                        other_changes += 1
            if consonant_changes >= 1 and other_changes <= 1:
                return True
        
        # Check: is_letter_duplicated (length +1, one letter doubled)
        if len(variation_lower) == len(original_lower) + 1:
            for i, char in enumerate(original_lower):
                test = original_lower[:i] + char + original_lower[i:]
                if test == variation_lower:
                    return True
        
        # Check: is_random_letter_inserted (length +1, Levenshtein 1)
        if len(variation) == len(original) + 1:
            if Levenshtein.distance(original, variation) == 1:
                return True
        
        return False

    def calculate_phonetic_similarity(self, original_name: str, variation: str) -> float:
        """Calculate phonetic similarity using validator's algorithm."""
        algorithms = {
            "soundex": lambda x, y: jellyfish.soundex(x) == jellyfish.soundex(y),
            "metaphone": lambda x, y: jellyfish.metaphone(x) == jellyfish.metaphone(y),
            "nysiis": lambda x, y: jellyfish.nysiis(x) == jellyfish.nysiis(y),
        }

        random.seed(hash(original_name) % 10000)
        selected_algorithms = random.sample(list(algorithms.keys()), k=min(3, len(algorithms)))

        weights = [random.random() for _ in selected_algorithms]
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        phonetic_score = sum(
            algorithms[algo](original_name, variation) * weight
            for algo, weight in zip(selected_algorithms, normalized_weights)
        )

        return float(phonetic_score)

    def calculate_orthographic_similarity(self, original_name: str, variation: str) -> float:
        """Calculate orthographic similarity using Levenshtein distance."""
        try:
            distance = Levenshtein.distance(original_name, variation)
            max_len = max(len(original_name), len(variation))
            return 1.0 - (distance / max_len)
        except Exception:
            return 0.0

    def get_phonetic_grade(self, score: float) -> str:
        for grade, (min_val, max_val) in self.phonetic_boundaries.items():
            if min_val <= score <= max_val:
                return grade
        return None

    def get_orthographic_grade(self, score: float) -> str:
        for grade, (min_val, max_val) in self.orthographic_boundaries.items():
            if min_val <= score <= max_val:
                return grade
        return None

    def calculate_length_score(self, original: str, variation: str) -> float:
        original_len = len(original)
        var_len = len(variation)
        length_ratio = min(var_len / original_len, original_len / var_len)
        absolute_diff = abs(var_len - original_len)
        length_score = length_ratio * (1.0 - min(1.0, absolute_diff / original_len))
        return length_score

    def generate_all_variations(self, name: str) -> Set[str]:
        """
        Generate variations optimized for validator scoring.
        
        Key strategies:
        1. Preserve Soundex codes (vowel changes, same-group consonant swaps)
        2. High orthographic similarity (1-2 char changes max)
        3. Same length (best length score)
        4. Avoid rule-passing patterns (no single deletions, no adjacent swaps)
        """
        name_lower = name.lower()
        original_len = len(name_lower)
        variations = set()
        
        # Soundex groups - consonants in same group produce same code
        # Group 1: b, f, p, v
        # Group 2: c, g, j, k, q, s, x, z
        # Group 3: d, t
        # Group 4: l
        # Group 5: m, n
        # Group 6: r
        # Vowels (a, e, i, o, u) and h, w, y are ignored in Soundex
        
        soundex_groups = {
            'b': ['f', 'p', 'v'], 'f': ['b', 'p', 'v'], 'p': ['b', 'f', 'v'], 'v': ['b', 'f', 'p'],
            'c': ['g', 'j', 'k', 'q', 's', 'x', 'z'], 'g': ['c', 'j', 'k', 'q', 's', 'x', 'z'],
            'j': ['c', 'g', 'k', 'q', 's', 'x', 'z'], 'k': ['c', 'g', 'j', 'q', 's', 'x', 'z'],
            'q': ['c', 'g', 'j', 'k', 's', 'x', 'z'], 's': ['c', 'g', 'j', 'k', 'q', 'x', 'z'],
            'x': ['c', 'g', 'j', 'k', 'q', 's', 'z'], 'z': ['c', 'g', 'j', 'k', 'q', 's', 'x'],
            'd': ['t'], 't': ['d'],
            'l': ['r'], 'r': ['l'],  # Not same Soundex but phonetically similar
            'm': ['n'], 'n': ['m'],
        }
        
        vowels = 'aeiou'
        
        # STRATEGY 1: Vowel substitutions (preserves Soundex, same length)
        # Soundex ignores vowels after first letter, so any vowel change preserves code
        for i in range(len(name_lower)):
            if name_lower[i] in vowels:
                for new_vowel in vowels:
                    if new_vowel != name_lower[i]:
                        var = name_lower[:i] + new_vowel + name_lower[i+1:]
                        if not self.has_excessive_letter_repetition(var):
                            variations.add(var)
        
        # STRATEGY 2: Same Soundex group consonant swaps (preserves Soundex, same length)
        for i in range(1, len(name_lower)):  # Skip first letter (Soundex keeps it)
            char = name_lower[i]
            if char in soundex_groups:
                for new_char in soundex_groups[char][:2]:  # Limit to 2 alternatives
                    var = name_lower[:i] + new_char + name_lower[i+1:]
                    if not self.has_excessive_letter_repetition(var):
                        # Avoid creating double letters
                        if i > 0 and var[i-1] != var[i]:
                            if i < len(var)-1 and var[i] != var[i+1]:
                                variations.add(var)
        
        # STRATEGY 3: Two vowel changes (still preserves Soundex, high orthographic)
        single_vowel_vars = list(variations)[:50]
        for base in single_vowel_vars:
            for i in range(len(base)):
                if base[i] in vowels:
                    for new_vowel in vowels:
                        if new_vowel != base[i]:
                            var = base[:i] + new_vowel + base[i+1:]
                            if var != name_lower and var != base:
                                if not self.has_excessive_letter_repetition(var):
                                    variations.add(var)
                            break  # Only one more change per base
        
        # STRATEGY 4: Vowel + consonant change (2 changes, medium orthographic)
        for base in single_vowel_vars[:30]:
            for i in range(1, len(base)):
                char = base[i]
                if char in soundex_groups:
                    new_char = soundex_groups[char][0]
                    var = base[:i] + new_char + base[i+1:]
                    if var != name_lower and var != base:
                        if not self.has_excessive_letter_repetition(var):
                            if i > 0 and var[i-1] != var[i]:
                                variations.add(var)
                    break
        
        # STRATEGY 5: Three changes for "Far" bucket (lower orthographic)
        for _ in range(30):
            chars = list(name_lower)
            # Change 2-3 vowels
            vowel_positions = [i for i, c in enumerate(chars) if c in vowels]
            if len(vowel_positions) >= 2:
                for pos in random.sample(vowel_positions, min(3, len(vowel_positions))):
                    chars[pos] = random.choice([v for v in vowels if v != chars[pos]])
            var = ''.join(chars)
            if var != name_lower and not self.has_excessive_letter_repetition(var):
                variations.add(var)
        
        # STRATEGY 6: Add 'h' or 'y' (Soundex ignores these, +1 length)
        # Only a few for length distribution
        for i in range(1, min(3, len(name_lower))):
            for insert_char in ['h', 'y']:
                var = name_lower[:i] + insert_char + name_lower[i:]
                if not self.has_excessive_letter_repetition(var):
                    variations.add(var)
        
        variations.discard(name_lower)
        
        # Capitalize
        capitalized = set()
        for var in variations:
            cap_var = ' '.join(word.capitalize() for word in var.split())
            capitalized.add(cap_var)
        
        return capitalized
        return capitalized

    def score_variation(self, original: str, variation: str) -> Dict:
        """Score a single variation."""
        original_lower = original.lower()
        variation_lower = variation.lower()
        
        p_score = self.calculate_phonetic_similarity(original_lower, variation_lower)
        o_score = self.calculate_orthographic_similarity(original_lower, variation_lower)
        l_score = self.calculate_length_score(original_lower, variation_lower)
        
        p_grade = self.get_phonetic_grade(p_score)
        o_grade = self.get_orthographic_grade(o_score)
        
        passes_rule = self.passes_rule_check(original, variation)
        
        return {
            'variation': variation,
            'phonetic_score': p_score,
            'orthographic_score': o_score,
            'length_score': l_score,
            'phonetic_grade': p_grade,
            'orthographic_grade': o_grade,
            'valid': p_grade is not None and o_grade is not None,
            'passes_rule': passes_rule
        }

    def optimize_selection(self, name: str, count: int,
                          phonetic_similarity: Dict[str, float],
                          orthographic_similarity: Dict[str, float]) -> List[Dict]:
        """
        Optimize selection prioritizing:
        1. HIGH ORTHOGRAPHIC SCORE (top miners get 0.77)
        2. HIGH LENGTH SCORE (top miners get 0.95)
        3. Variations that DON'T pass rule checks
        4. Good phonetic similarity
        """
        all_variations = self.generate_all_variations(name)
        all_variations.discard(name)
        all_variations.discard(name.lower())
        all_variations.discard(name.capitalize())
        
        if not all_variations:
            return []
        
        scored_variations = []
        for var in all_variations:
            score_data = self.score_variation(name, var)
            if score_data['valid']:
                scored_variations.append(score_data)
        
        if not scored_variations:
            return []
        
        # Separate by rule-passing status
        non_rule_passing = [v for v in scored_variations if not v['passes_rule']]
        rule_passing = [v for v in scored_variations if v['passes_rule']]
        
        # Sort by ORTHOGRAPHIC first (most important gap: 0.41 → 0.77), then LENGTH, then phonetic
        # Top miners: Orthographic 0.77, Length 0.95, Phonetic 0.48
        def score_key(x):
            return (
                x['orthographic_score'] * 2 +  # Highest priority
                x['length_score'] * 1 +         # Second priority
                x['phonetic_score'] * 2            # Third priority
            )
        
        non_rule_passing.sort(key=score_key, reverse=True)
        rule_passing.sort(key=score_key, reverse=True)
        
        selected = []
        used = set()
        
        # Target distribution based on orthographic similarity request
        # Prioritize Light (0.70-1.00) for high orthographic scores
        o_light_target = int(count * orthographic_similarity.get('light', 0))
        o_medium_target = int(count * orthographic_similarity.get('medium', 0))
        o_far_target = int(count * orthographic_similarity.get('far', 0))
        
        # Ensure at least some from each requested bucket
        if orthographic_similarity.get('light', 0) > 0:
            o_light_target = max(1, o_light_target)
        if orthographic_similarity.get('medium', 0) > 0:
            o_medium_target = max(1, o_medium_target)
        if orthographic_similarity.get('far', 0) > 0:
            o_far_target = max(1, o_far_target)
        
        # Group by orthographic grade
        o_light = [v for v in non_rule_passing if v['orthographic_grade'] == 'light']
        o_medium = [v for v in non_rule_passing if v['orthographic_grade'] == 'medium']
        o_far = [v for v in non_rule_passing if v['orthographic_grade'] == 'far']
        
        # Select from Light orthographic first (highest scores)
        for var in o_light[:o_light_target]:
            if var['variation'] not in used:
                selected.append(var)
                used.add(var['variation'])
        
        # Then Medium
        for var in o_medium[:o_medium_target]:
            if var['variation'] not in used:
                selected.append(var)
                used.add(var['variation'])
        
        # Then Far
        for var in o_far[:o_far_target]:
            if var['variation'] not in used:
                selected.append(var)
                used.add(var['variation'])
        
        # Fill remaining from highest scoring non-rule-passing
        for var in non_rule_passing:
            if len(selected) >= count:
                break
            if var['variation'] not in used:
                selected.append(var)
                used.add(var['variation'])
        
        # Last resort: rule-passing with high orthographic
        if len(selected) < count:
            rule_passing_sorted = sorted(rule_passing, key=score_key, reverse=True)
            for var in rule_passing_sorted:
                if len(selected) >= count:
                    break
                if var['variation'] not in used:
                    selected.append(var)
                    used.add(var['variation'])
        
        return selected[:count]


def main():
    """Test the Latin name optimizer with validator scoring."""
    import os
    import sys
    
    # Add validator path
    validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
    if validator_path not in sys.path:
        sys.path.insert(0, validator_path)
    
    from module import calculate_part_score
    
    optimizer = NameVariationOptimizer()
    
    test_names = [
        "John",
        "Smith",
        "Michael",
    ]
    
    count = 10
    # Use capitalized keys to match validator's boundaries
    phonetic_similarity = {"Light": 0.3, "Medium": 0.4, "Far": 0.3}
    orthographic_similarity = {"Light": 0.3, "Medium": 0.4, "Far": 0.3}
    
    for name in test_names:
        print(f"\nOriginal: {name}")
        
        # Use lowercase keys for optimizer
        phonetic_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
        orthographic_lower = {k.lower(): v for k, v in orthographic_similarity.items()}
                
        results = optimizer.optimize_selection(name, count, phonetic_lower, orthographic_lower)
        
        grade_counts = {'light': 0, 'medium': 0, 'far': 0, None: 0}
        for r in results:
            grade = r.get('orthographic_grade')
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        print(f"Orthographic grade distribution: {grade_counts}")
        variations = [r['variation'] for r in results]
        print(f"Variations: {variations}")
        
        # Use capitalized keys for validator
        score, metrics = calculate_part_score(
            name,
            variations,
            phonetic_similarity,
            orthographic_similarity,
            count
        )
        print(f"Score: {score:.4f}")
        print(f"Metrics: similarity={metrics.get('similarity_score', 0):.4f}, "
              f"phonetic={metrics.get('phonetic_quality', 0):.4f}, "
              f"orthographic={metrics.get('orthographic_quality', 0):.4f}, "
              f"count={metrics.get('count_score', 0):.4f}, "
              f"uniqueness={metrics.get('uniqueness_score', 0):.4f}, "
              f"length={metrics.get('length_score', 0):.4f}")


if __name__ == "__main__":
    main()
