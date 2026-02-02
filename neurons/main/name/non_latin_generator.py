"""
Non-Latin Name Variation Optimizer - Aligned with Validator Scoring System

KEY INSIGHT from validator:
1. Validator receives original non-Latin name (e.g., "محمد علي")
2. Validator transliterates it using unidecode -> "mhmd ly"  
3. Validator compares miner's variations against "mhmd ly" using phonetic algorithms

The phonetic algorithms (Soundex, Metaphone, NYSIIS) work by:
- Soundex: Keeps first letter, converts rest to numbers based on consonant groups
- Metaphone: Creates phonetic encoding based on pronunciation rules
- NYSIIS: New York State algorithm for name matching

To score well, variations must produce MATCHING phonetic codes with the transliterated original.

Scoring Weights:
- similarity_weight: 60% (phonetic only)
- count_weight: 15%
- uniqueness_weight: 10%
- length_weight: 15%
"""

import random
import jellyfish
import Levenshtein
import math
import re
import os
import sys
from typing import List, Dict, Set
from unidecode import unidecode


class NonLatinNameOptimizer:
    def __init__(self):
        # Validator's exact phonetic boundaries
        self.phonetic_boundaries = {
            "light": (0.80, 1.00),
            "medium": (0.60, 0.79),
            "far": (0.30, 0.59)
        }
        
        self.WEIGHTS = {
            "similarity": 0.60,
            "count": 0.15,
            "uniqueness": 0.10,
            "length": 0.15
        }

    def transliterate_to_latin(self, name: str) -> str:
        """
        Convert non-Latin script names to Latin characters using unidecode.
        IMPORTANT: Must match validator's translate_unidecode() output exactly.
        Validator uses: unidecode(original_name) without any cleaning.
        """
        try:
            # Match validator's exact behavior - just unidecode, no cleaning
            latin_name = unidecode(name)
            return latin_name
        except Exception:
            return name

    def has_excessive_letter_repetition(self, text: str, max_repetition: int = 2) -> bool:
        """Check if text has excessive letter repetition."""
        if not text:
            return False
        pattern = r'(.)\1{' + str(max_repetition) + r',}'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def calculate_phonetic_similarity(self, original_name: str, variation: str) -> float:
        """Calculate phonetic similarity using validator's exact algorithm."""
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

    def get_phonetic_grade(self, score: float) -> str:
        """Get phonetic grade from score."""
        for grade, (min_val, max_val) in self.phonetic_boundaries.items():
            if min_val <= score <= max_val:
                return grade
        return None

    def calculate_length_score(self, original: str, variation: str) -> float:
        """Calculate length score using validator's exact logic."""
        original_len = len(original)
        var_len = len(variation)
        
        if original_len == 0:
            return 0.0
        
        length_ratio = min(var_len / original_len, original_len / var_len) if var_len > 0 else 0
        absolute_diff = abs(var_len - original_len)
        length_score = length_ratio * (1.0 - min(1.0, absolute_diff / original_len))
        return length_score

    def generate_phonetic_preserving_variations(self, word: str) -> Set[str]:
        """
        Generate variations that preserve phonetic similarity.
        Focus on changes that don't affect Soundex/Metaphone/NYSIIS codes.
        Also maintain similar length to original for better length scores.
        
        Works with raw unidecode output (may contain special chars like backticks).
        """
        variations = set()
        # Clean word for processing but keep original format
        word_clean = ''.join(c.lower() for c in word if c.isalpha())
        
        if len(word_clean) < 2:
            return variations
        
        # 1. Vowel substitutions (preserve phonetic codes, same length)
        vowels = 'aeiou'
        for i in range(len(word_clean)):
            if word_clean[i] in vowels:
                for v in vowels:
                    if v != word_clean[i]:
                        new_var = word_clean[:i] + v + word_clean[i+1:]
                        if not self.has_excessive_letter_repetition(new_var):
                            variations.add(new_var)
        
        # 2. Consonant substitutions that preserve phonetic codes
        equiv_consonants = [
            ('b', 'p'), ('p', 'b'),
            ('d', 't'), ('t', 'd'),
            ('g', 'k'), ('k', 'g'),
            ('c', 'k'), ('k', 'c'),
            ('f', 'v'), ('v', 'f'),
            ('s', 'z'), ('z', 's'),
            ('m', 'n'), ('n', 'm'),
            ('l', 'r'), ('r', 'l'),
            ('h', ''),  # H is often silent
        ]
        for old, new in equiv_consonants:
            if old in word_clean:
                if len(new) == 1:  # Same length substitution
                    new_var = word_clean.replace(old, new, 1)
                    if not self.has_excessive_letter_repetition(new_var):
                        variations.add(new_var)
                elif len(new) == 0:  # Removal (shorter by 1)
                    new_var = word_clean.replace(old, new, 1)
                    if new_var and not self.has_excessive_letter_repetition(new_var):
                        variations.add(new_var)
        
        # 3. Character swapping (same length)
        for i in range(len(word_clean) - 1):
            chars = list(word_clean)
            chars[i], chars[i+1] = chars[i+1], chars[i]
            new_var = ''.join(chars)
            if not self.has_excessive_letter_repetition(new_var):
                variations.add(new_var)
        
        # 4. Single character removal (shorter by 1)
        if len(word_clean) > 2:
            for i in range(len(word_clean)):
                new_var = word_clean[:i] + word_clean[i+1:]
                if new_var and not self.has_excessive_letter_repetition(new_var):
                    variations.add(new_var)
        
        # 5. Single vowel addition (longer by 1) - only add vowels to preserve phonetics
        for i in range(len(word_clean) + 1):
            for v in vowels:
                new_var = word_clean[:i] + v + word_clean[i:]
                if not self.has_excessive_letter_repetition(new_var):
                    variations.add(new_var)
        
        # 6. Double a consonant (longer by 1)
        for i in range(len(word_clean)):
            if word_clean[i] not in vowels and word_clean[i].isalpha():
                new_var = word_clean[:i+1] + word_clean[i] + word_clean[i+1:]
                if not self.has_excessive_letter_repetition(new_var):
                    variations.add(new_var)
        
        return variations

    def generate_all_variations(self, latin_name: str) -> Set[str]:
        """
        Generate variations for a full name (may have multiple parts).
        Works with raw unidecode output which may contain special characters.
        """
        # Clean the name for processing - extract only alphabetic parts
        # Split by spaces and non-alpha characters
        import re
        parts = re.split(r'[^a-zA-Z]+', latin_name)
        parts = [p for p in parts if p]  # Remove empty strings
        
        if len(parts) == 0:
            return set()
        
        # Generate variations for each part
        part_variations = []
        for part in parts:
            pv = self.generate_phonetic_preserving_variations(part)
            pv.add(part.lower())  # Include original (lowercase)
            
            # Apply variations iteratively for more diversity
            for _ in range(2):
                new_vars = set()
                for v in list(pv)[:100]:
                    new_vars.update(self.generate_phonetic_preserving_variations(v))
                pv.update(new_vars)
                if len(pv) > 500:
                    break
            
            part_variations.append(pv)
        
        # Combine parts
        all_variations = set()
        
        if len(part_variations) == 1:
            all_variations = part_variations[0]
        else:
            # Combine first and last name variations
            first_vars = list(part_variations[0])[:100]
            last_vars = list(part_variations[-1])[:100]
            
            for fv in first_vars:
                for lv in last_vars:
                    combined = f"{fv} {lv}"
                    if not self.has_excessive_letter_repetition(combined.replace(' ', '')):
                        all_variations.add(combined)
        
        # Remove original (cleaned version)
        cleaned_original = ' '.join(parts).lower()
        all_variations.discard(cleaned_original)
        
        return all_variations

    def score_variation(self, original: str, variation: str) -> Dict:
        """
        Score a single variation.
        Original should be the raw unidecode output.
        Variation is the cleaned alphabetic version.
        """
        import re
        # Clean original for comparison (extract only alphabetic chars)
        original_clean = ''.join(c.lower() for c in original if c.isalpha() or c == ' ')
        variation_lower = variation.lower()
        
        p_score = self.calculate_phonetic_similarity(original_clean, variation_lower)
        l_score = self.calculate_length_score(original_clean, variation_lower)
        p_grade = self.get_phonetic_grade(p_score)
        
        return {
            'variation': variation,
            'phonetic_score': p_score,
            'length_score': l_score,
            'phonetic_grade': p_grade,
            'valid': p_grade is not None
        }

    def optimize_phonetic_selection(self, name: str, count: int,
                                   phonetic_similarity: Dict[str, float]) -> List[Dict]:
        """Optimize selection of name variations using only phonetic similarity."""
        # Step 1: Transliterate to Latin
        latin_name = self.transliterate_to_latin(name)
        
        # Step 2: Generate all variations
        all_variations = self.generate_all_variations(latin_name)
        
        if not all_variations:
            return []
        
        # Step 3: Score all variations
        scored_variations = []
        for var in all_variations:
            score_data = self.score_variation(latin_name, var)
            scored_variations.append(score_data)
        
        # Sort by phonetic score + length score
        scored_variations.sort(key=lambda x: x['phonetic_score'] + x['length_score'], reverse=True)
        
        # Step 4: Select variations prioritizing those with valid grades
        valid_vars = [v for v in scored_variations if v['valid']]
        invalid_vars = [v for v in scored_variations if not v['valid']]
        
        # Group valid by grade
        grade_groups = {'light': [], 'medium': [], 'far': []}
        for var in valid_vars:
            if var['phonetic_grade']:
                grade_groups[var['phonetic_grade']].append(var)
        
        # Calculate targets
        targets = {
            'light': max(1, int(count * phonetic_similarity.get('light', 0.33))),
            'medium': max(1, int(count * phonetic_similarity.get('medium', 0.34))),
            'far': max(1, int(count * phonetic_similarity.get('far', 0.33)))
        }
        
        # Select to meet targets
        selected = []
        used = set()
        
        for grade in ['light', 'medium', 'far']:
            candidates = [v for v in grade_groups[grade] if v['variation'] not in used]
            take_count = min(len(candidates), targets[grade])
            for var in candidates[:take_count]:
                if len(selected) < count:
                    selected.append(var)
                    used.add(var['variation'])
        
        # Fill remaining with best scoring (valid first, then invalid)
        remaining = [v for v in valid_vars + invalid_vars if v['variation'] not in used]
        for var in remaining:
            if len(selected) >= count:
                break
            selected.append(var)
        
        return selected[:count]


def main():
    """Test the non-Latin optimizer."""
    optimizer = NonLatinNameOptimizer()
    
    test_names = [
        "محمد",      # Arabic
        "Владимир",       # Cyrillic
    ]
    
    count = 10
    # Use capitalized keys to match validator's phonetic_boundaries
    phonetic_similarity = {"Light": 0.3, "Medium": 0.4, "Far": 0.3}
    
    validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
    if validator_path not in sys.path:
        sys.path.insert(0, validator_path)
    
    from module import calculate_part_score_phonetic_only
    
    for name in test_names:
        print(f"\nOriginal: {name}")
        latin = optimizer.transliterate_to_latin(name)
        print(f"Transliterated: {latin}")
        
        # Use lowercase keys for optimizer (it expects lowercase)
        phonetic_lower = {k.lower(): v for k, v in phonetic_similarity.items()}
        results = optimizer.optimize_phonetic_selection(name, count, phonetic_lower)
        
        grade_counts = {'light': 0, 'medium': 0, 'far': 0, None: 0}
        for r in results:
            grade = r.get('phonetic_grade')
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        print(f"Grade distribution: {grade_counts}")
        variations = [r['variation'] for r in results]
        
        # Use capitalized keys for validator
        print(calculate_part_score_phonetic_only(
            latin,
            variations,
            phonetic_similarity,  # Capitalized keys
            count
        ))

if __name__ == "__main__":
    main()
