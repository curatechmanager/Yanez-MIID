#!/usr/bin/env python3
"""
Rule-Based Variation Generator

This module generates rule-based name variations that EXACTLY match the validator's
rule evaluation functions in rule_evaluator.py.

CRITICAL: Rule names and implementations must match validator's RULE_EVALUATORS exactly.
"""

import random
import re
from typing import List, Dict
import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from db import save_error
except ImportError:
    # Fallback if db module not available
    def save_error(category, data, message):
        print(f"[ERROR] {category}: {message} - {data}")


class RuleBasedGenerator:
    """Generate rule-based name variations that pass validator's rule checks"""
    
    def __init__(self, seed: int = None):
        """Initialize with optional seed for reproducibility"""
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        
        # CRITICAL: Rule names MUST match validator's RULE_EVALUATORS keys exactly
        # ONLY include rules that exist in validator's rule_extractor.py RULE_FUNCTIONS
        self.rule_map = {
            # Character replacement rules - EXACT validator names
            'replace_spaces_with_random_special_characters': self.replace_spaces_with_special_chars,
            'replace_double_letters_with_single_letter': self.replace_double_letter,
            'replace_random_vowel_with_random_vowel': self.replace_vowel,
            'replace_random_consonant_with_random_consonant': self.replace_consonant,
            
            # Swap rules - EXACT validator names
            'swap_random_letter': self.swap_adjacent_letters,
            'swap_adjacent_consonants': self.swap_adjacent_consonants,
            'swap_adjacent_syllables': self.swap_adjacent_letters,  # Simplified
            
            # Removal rules - EXACT validator names (ONLY those in validator)
            'delete_random_letter': self.delete_letter,
            'remove_random_vowel': self.remove_vowel,
            'remove_random_consonant': self.remove_consonant,
            'remove_all_spaces': self.remove_all_spaces,
            
            # Addition rules - EXACT validator names
            'duplicate_random_letter_as_double_letter': self.duplicate_letter,
            'duplicate_random_letter': self.duplicate_letter,
            'insert_random_letter': self.insert_letter,
            'add_random_leading_title': self.add_title_prefix,
            'add_random_trailing_title': self.add_title_suffix,
            
            # Name structure rules - EXACT validator names
            'shorten_name_to_initials': self.shorten_to_initials,
            'name_parts_permutations': self.permute_name_parts,
            'initial_only_first_name': self.initial_first_name,
            'shorten_name_to_abbreviations': self.abbreviate_name
        }
        
        # Rules that require specific name structure - EXACT validator names
        self.multi_part_rules = {
            'name_parts_permutations', 'initial_only_first_name', 
            'shorten_name_to_initials', 'shorten_name_to_abbreviations'
        }
        self.space_rules = {'replace_spaces_with_random_special_characters', 'remove_all_spaces'}
        self.double_letter_rules = {'replace_double_letters_with_single_letter'}
    
    def _has_double_letters(self, name: str) -> bool:
        """Check if name has double letters"""
        name_lower = name.lower()
        for i in range(len(name_lower) - 1):
            if name_lower[i] == name_lower[i+1] and name_lower[i].isalpha():
                return True
        return False
    
    def _has_adjacent_consonants(self, name: str) -> bool:
        """Check if name has different adjacent consonants"""
        vowels = 'aeiou'
        name_lower = name.lower()
        for i in range(len(name_lower) - 1):
            if (name_lower[i].isalpha() and name_lower[i] not in vowels and
                name_lower[i+1].isalpha() and name_lower[i+1] not in vowels and
                name_lower[i] != name_lower[i+1]):
                return True
        return False
    
    def _get_applicable_rules(self, name: str, rules: List[str]) -> List[str]:
        """Filter rules to only those applicable to this name structure"""
        applicable = []
        name_parts = name.split()
        has_space = ' ' in name
        has_double = self._has_double_letters(name)
        has_adj_cons = self._has_adjacent_consonants(name)
        
        for rule in rules:
            # Skip multi-part rules for single-part names
            if rule in self.multi_part_rules and len(name_parts) < 2:
                continue
            # Skip space rules for names without spaces
            if rule in self.space_rules and not has_space:
                continue
            # Skip double letter rules for names without double letters
            if rule in self.double_letter_rules and not has_double:
                continue
            # Skip adjacent consonant swap for names without swappable consonants
            if rule == 'swap_adjacent_consonants' and not has_adj_cons:
                continue
            applicable.append(rule)
        
        return applicable
    
    def generate_rule_based_variations(self, name: str, count: int, rules: List[str]) -> List[str]:
        """Generate rule-based variations using specified rules with smart rule application"""
        variations = []
        
        # Filter to applicable rules
        applicable_rules = self._get_applicable_rules(name, rules)
        
        if not applicable_rules:
            # Fall back to all applicable rules from rule_map
            all_rules = list(self.rule_map.keys())
            applicable_rules = self._get_applicable_rules(name, all_rules)
        
        if not applicable_rules:
            return variations
        
        max_attempts_per_rule = 10  # Max attempts to get unique variation from same rule
        
        if count >= len(applicable_rules):
            # STRATEGY 1: Use all rules at least once, then continue with any rules
            
            # Phase 1: Apply each rule once to ensure all are used
            for rule in applicable_rules:
                if len(variations) >= count:
                    break
                    
                if rule in self.rule_map:
                    attempts = 0
                    while attempts < max_attempts_per_rule:
                        try:
                            variation = self.rule_map[rule](name)
                            if variation and variation != name and variation not in variations:
                                variations.append(variation)
                                break
                        except Exception as e:
                            save_error("name", {rule}, f"rule error:")
                            break
                        attempts += 1
                else:
                    save_error("name", {rule}, f"don't find rule")
            
            # Phase 2: Continue with any rules to reach target count
            rule_index = 0
            while len(variations) < count:
                rule = applicable_rules[rule_index % len(applicable_rules)]
                
                if rule in self.rule_map:
                    attempts = 0
                    while attempts < max_attempts_per_rule:
                        try:
                            variation = self.rule_map[rule](name)
                            if variation and variation != name and variation not in variations:
                                variations.append(variation)
                                break
                        except Exception as e:
                            save_error("name", {rule}, f"rule error: {e}")
                            break
                        attempts += 1
                    
                    # If we couldn't get unique variation after max attempts, try next rule
                    if attempts >= max_attempts_per_rule:
                        rule_index += 1
                        if rule_index >= len(applicable_rules) * 3:  # Prevent infinite loop
                            break
                else:
                    rule_index += 1
                    if rule_index >= len(applicable_rules) * 3:  # Prevent infinite loop
                        break
                
                rule_index += 1
        
        else:
            # STRATEGY 2: Use exactly count rules, ensure unique variations
            
            # Select count rules (can repeat if needed)
            selected_rules = []
            for i in range(count):
                selected_rules.append(applicable_rules[i % len(applicable_rules)])
            
            # Apply each selected rule once, ensuring uniqueness
            for rule in selected_rules:
                if len(variations) >= count:
                    break
                    
                if rule in self.rule_map:
                    attempts = 0
                    while attempts < max_attempts_per_rule:
                        try:
                            variation = self.rule_map[rule](name)
                            if variation and variation != name and variation not in variations:
                                variations.append(variation)
                                break
                        except Exception as e:
                            save_error("name", {rule}, f"rule error: {e}")
                            break
                        attempts += 1
                else:
                    save_error("name", {rule}, f"don't find rule")
        
        return variations[:count]  # Ensure exact count
    
    def _generate_rule_variation_with_randomization(self, name: str, rule: str, existing_variations: List[str]) -> str:
        """Generate a variation with additional randomization to create diversity"""
        
        # For rules that can have multiple outcomes, add randomization
        if rule == 'replace_spaces_with_random_special_characters':
            special_chars = ['-', '_', '.', '~', '+', '=']
            if ' ' in name:
                char = random.choice(special_chars)
                return name.replace(' ', char)
        
        elif rule == 'swap_adjacent_consonants':
            # Find all possible consonant swaps and pick randomly
            vowels = 'aeiou'
            name_lower = name.lower()
            swap_positions = []
            
            for i in range(len(name_lower) - 1):
                if (name_lower[i].isalpha() and name_lower[i] not in vowels and
                    name_lower[i+1].isalpha() and name_lower[i+1] not in vowels and
                    name_lower[i] != name_lower[i+1]):
                    swap_positions.append(i)
            
            if swap_positions:
                pos = random.choice(swap_positions)
                result = list(name)
                result[pos], result[pos+1] = result[pos+1], result[pos]
                return ''.join(result)
        
        elif rule == 'replace_random_vowel_with_random_vowel':
            vowels = 'aeiou'
            result = list(name)
            vowel_positions = [i for i, c in enumerate(result) if c.lower() in vowels]
            
            if vowel_positions:
                pos = random.choice(vowel_positions)
                old_vowel = result[pos].lower()
                new_vowel = random.choice([v for v in vowels if v != old_vowel])
                
                # Preserve case
                if result[pos].isupper():
                    new_vowel = new_vowel.upper()
                result[pos] = new_vowel
                return ''.join(result)
        
        elif rule == 'replace_random_consonant_with_random_consonant':
            vowels = 'aeiou'
            consonants = 'bcdfghjklmnpqrstvwxyz'
            result = list(name)
            consonant_positions = [i for i, c in enumerate(result) 
                                  if c.lower() in consonants]
            
            if consonant_positions:
                pos = random.choice(consonant_positions)
                old_cons = result[pos].lower()
                new_cons = random.choice([c for c in consonants if c != old_cons])
                
                # Preserve case
                if result[pos].isupper():
                    new_cons = new_cons.upper()
                result[pos] = new_cons
                return ''.join(result)
        
        elif rule == 'add_random_leading_title':
            titles = ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sir", "Lady", "Lord"]
            title = random.choice(titles)
            return f"{title} {name}"
        
        elif rule == 'add_random_trailing_title':
            suffixes = ["Jr.", "Sr.", "III", "IV", "PhD", "MD", "Esq.", "II"]
            suffix = random.choice(suffixes)
            return f"{name} {suffix}"
        
        # Fall back to original rule implementation
        return self.rule_map[rule](name)
    
    def _generate_enhanced_variations(self, name: str, rules: List[str], needed_count: int, existing_variations: List[str]) -> List[str]:
        """Generate additional variations using enhanced techniques"""
        enhanced_variations = []
        
        # Try multiple random seeds for more diversity
        original_seed = random.getstate()
        
        # Strategy 1: Multiple rule applications with different parameters
        for i in range(needed_count * 5):  # More attempts
            # Use different random seed for each attempt
            random.seed(hash(name + str(i)) % 1000000)
            
            rule = random.choice(rules)
            if rule in self.rule_map:
                try:
                    variation = self._generate_rule_variation_with_randomization(name, rule, [])
                    if (variation and variation != name and 
                        variation not in existing_variations and 
                        variation not in enhanced_variations):
                        enhanced_variations.append(variation)
                        if len(enhanced_variations) >= needed_count:
                            break
                except Exception:
                    continue
        
        # Strategy 2: If still not enough, create hybrid variations
        if len(enhanced_variations) < needed_count:
            enhanced_variations.extend(self._generate_hybrid_variations(
                name, rules, needed_count - len(enhanced_variations), 
                existing_variations + enhanced_variations
            ))
        
        # Strategy 3: If still not enough, use fallback variations
        if len(enhanced_variations) < needed_count:
            enhanced_variations.extend(self._generate_fallback_variations(
                name, needed_count - len(enhanced_variations),
                existing_variations + enhanced_variations
            ))
        
        # Restore original random state
        random.setstate(original_seed)
        
        return enhanced_variations
    
    def _generate_hybrid_variations(self, name: str, rules: List[str], needed_count: int, existing_variations: List[str]) -> List[str]:
        """Generate variations by combining multiple rule effects"""
        hybrid_variations = []
        
        for i in range(needed_count * 3):
            # Apply multiple rules in sequence
            variation = name
            num_rules = min(random.randint(1, 2), len(rules))
            selected_rules = random.sample(rules, num_rules)
            
            for rule in selected_rules:
                if rule in self.rule_map:
                    try:
                        variation = self.rule_map[rule](variation)
                    except Exception:
                        continue
            
            if (variation and variation != name and 
                variation not in existing_variations and 
                variation not in hybrid_variations):
                hybrid_variations.append(variation)
                if len(hybrid_variations) >= needed_count:
                    break
        
        return hybrid_variations
    
    def _generate_fallback_variations(self, name: str, needed_count: int, existing_variations: List[str]) -> List[str]:
        """Generate fallback variations using simple transformations"""
        fallback_variations = []
        
        # Simple character substitutions
        substitutions = [
            ('a', 'e'), ('e', 'a'), ('i', 'y'), ('y', 'i'),
            ('o', 'u'), ('u', 'o'), ('c', 'k'), ('k', 'c'),
            ('ph', 'f'), ('f', 'ph'), ('s', 'z'), ('z', 's')
        ]
        
        for i in range(needed_count * 2):
            variation = name
            
            # Apply random substitution
            old_char, new_char = random.choice(substitutions)
            if old_char in variation.lower():
                # Find all positions of the character
                positions = [j for j, c in enumerate(variation.lower()) if c == old_char]
                if positions:
                    pos = random.choice(positions)
                    variation_list = list(variation)
                    # Preserve case
                    if variation[pos].isupper():
                        new_char = new_char.upper()
                    variation_list[pos] = new_char
                    variation = ''.join(variation_list)
            
            # Add random character insertion/deletion for more variety
            if random.random() < 0.3 and len(variation) > 3:
                # Random character deletion
                pos = random.randint(1, len(variation) - 2)
                if variation[pos].isalpha():
                    variation = variation[:pos] + variation[pos+1:]
            elif random.random() < 0.3:
                # Random character insertion
                pos = random.randint(0, len(variation))
                char = random.choice('aeiou')
                variation = variation[:pos] + char + variation[pos:]
            
            if (variation and variation != name and 
                variation not in existing_variations and 
                variation not in fallback_variations):
                fallback_variations.append(variation)
                if len(fallback_variations) >= needed_count:
                    break
        
        return fallback_variations
    
    # ============================================================================
    # RULE IMPLEMENTATIONS - Must pass validator's evaluation functions
    # ============================================================================
    
    def replace_spaces_with_special_chars(self, name: str) -> str:
        """
        Validator check: is_space_replaced_with_special_chars
        - Original must have space, variation must not have space
        - Levenshtein distance <= number of spaces + 1
        """
        if ' ' not in name:
            return name
        special_chars = ['-', '_', '.']
        return name.replace(' ', random.choice(special_chars))
    
    def replace_double_letter(self, name: str) -> str:
        """
        Validator check: is_double_letter_replaced
        - Length must be original - 1
        - Removing one of the double letters must produce the variation
        """
        name_lower = name.lower()
        for i in range(len(name_lower) - 1):
            if name_lower[i] == name_lower[i+1] and name_lower[i].isalpha():
                # Remove one of the double letters (keep case of original)
                return name[:i] + name[i+1:]
        return name
    
    def replace_vowel(self, name: str) -> str:
        """
        Validator check: is_vowel_replaced
        - Same length as original
        - At least 1 vowel→vowel change, at most 1 other change
        """
        vowels = 'aeiou'
        result = list(name)
        vowel_positions = [i for i, c in enumerate(result) if c.lower() in vowels]
        
        if not vowel_positions:
            return name
        
        # Replace exactly 1 vowel with a different vowel
        pos = random.choice(vowel_positions)
        old_vowel = result[pos].lower()
        new_vowel = random.choice([v for v in vowels if v != old_vowel])
        
        # Preserve case
        if result[pos].isupper():
            new_vowel = new_vowel.upper()
        result[pos] = new_vowel
        
        return ''.join(result)
    
    def replace_consonant(self, name: str) -> str:
        """
        Validator check: is_consonant_replaced
        - Same length as original
        - At least 1 consonant→consonant change, at most 1 other change
        """
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        result = list(name)
        consonant_positions = [i for i, c in enumerate(result) 
                              if c.lower() in consonants]
        
        if not consonant_positions:
            return name
        
        # Replace exactly 1 consonant with a different consonant
        pos = random.choice(consonant_positions)
        old_cons = result[pos].lower()
        new_cons = random.choice([c for c in consonants if c != old_cons])
        
        # Preserve case
        if result[pos].isupper():
            new_cons = new_cons.upper()
        result[pos] = new_cons
        
        return ''.join(result)
    
    def replace_special_char(self, name: str) -> str:
        """
        Validator check: is_special_character_replaced
        - Same length, special char → different special char
        """
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        result = list(name)
        special_positions = [i for i, c in enumerate(result) if c in special_chars]
        
        if not special_positions:
            return name
        
        pos = random.choice(special_positions)
        old_char = result[pos]
        new_char = random.choice([c for c in special_chars if c != old_char])
        result[pos] = new_char
        
        return ''.join(result)
    
    def swap_adjacent_letters(self, name: str) -> str:
        """
        Validator check: is_letters_swapped
        - Same length as original
        - Exactly 2 positions differ
        - Those 2 positions are adjacent
        - Characters at those positions are swapped
        """
        if len(name) < 2:
            return name
        
        result = list(name)
        # Find valid swap positions (avoid spaces)
        positions = [i for i in range(len(result) - 1) 
                    if result[i] != ' ' and result[i+1] != ' ' and result[i] != result[i+1]]
        
        if not positions:
            return name
        
        pos = random.choice(positions)
        result[pos], result[pos+1] = result[pos+1], result[pos]
        
        return ''.join(result)
    
    def swap_adjacent_consonants(self, name: str) -> str:
        """
        Validator check: is_adjacent_consonants_swapped
        - Same length as original
        - Exactly 2 adjacent consonants are swapped
        """
        vowels = 'aeiou'
        result = list(name)
        
        # Find adjacent consonant pairs that are different
        positions = []
        for i in range(len(result) - 1):
            c1, c2 = result[i].lower(), result[i+1].lower()
            if (c1.isalpha() and c1 not in vowels and
                c2.isalpha() and c2 not in vowels and c1 != c2):
                positions.append(i)
        
        if not positions:
            return name
        
        pos = random.choice(positions)
        result[pos], result[pos+1] = result[pos+1], result[pos]
        
        return ''.join(result)
    
    def delete_letter(self, name: str) -> str:
        """
        Validator check: is_letter_removed
        - Length must be original - 1
        - Levenshtein distance must be 1
        """
        if len(name) <= 1:
            return name
        
        # Find positions of letters (not spaces)
        positions = [i for i, c in enumerate(name) if c != ' ']
        if not positions:
            return name
        
        pos = random.choice(positions)
        return name[:pos] + name[pos+1:]
    
    def remove_vowel(self, name: str) -> str:
        """
        Validator check: is_vowel_removed
        - Length must be original - 1
        - Removed character must be a vowel
        """
        vowels = 'aeiou'
        positions = [i for i, c in enumerate(name) if c.lower() in vowels]
        
        if not positions:
            return name
        
        pos = random.choice(positions)
        return name[:pos] + name[pos+1:]
    
    def remove_consonant(self, name: str) -> str:
        """
        Validator check: is_consonant_removed
        - Length must be original - 1
        - Removed character must be a consonant
        """
        vowels = 'aeiou'
        positions = [i for i, c in enumerate(name) 
                    if c.isalpha() and c.lower() not in vowels]
        
        if not positions:
            return name
        
        pos = random.choice(positions)
        return name[:pos] + name[pos+1:]
    
    def remove_special_char(self, name: str) -> str:
        """
        Validator check: is_random_special_removed
        - Length must be original - 1
        - Removed character must be a special character
        """
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        positions = [i for i, c in enumerate(name) if c in special_chars]
        
        if not positions:
            return name
        
        pos = random.choice(positions)
        return name[:pos] + name[pos+1:]
    
    def remove_title(self, name: str) -> str:
        """
        Validator check: is_title_removed
        - Must start with a title followed by space
        - Variation is name without the title
        """
        titles = ["Mr.", "Mrs.", "Ms.", "Mr", "Mrs", "Ms", "Miss", "Dr.", "Dr",
                  "Prof.", "Prof", "Sir", "Lady", "Lord", "Dame", "Master", 
                  "Rev.", "Hon.", "Capt.", "Col.", "Lt.", "Sgt.", "Maj."]
        
        name_lower = name.lower()
        for title in titles:
            if name_lower.startswith(title.lower() + " "):
                return name[len(title)+1:]
        
        return name
    
    def remove_all_spaces(self, name: str) -> str:
        """
        Validator check: is_all_spaces_removed
        - Variation must be original with all spaces removed
        """
        if ' ' not in name:
            return name
        return name.replace(' ', '')
    
    def duplicate_letter(self, name: str) -> str:
        """
        Validator check: is_letter_duplicated
        - Length must be original + 1
        - One letter is duplicated (inserted next to itself)
        """
        if not name:
            return name
        
        # Find letter positions
        positions = [i for i, c in enumerate(name) if c.isalpha()]
        if not positions:
            return name
        
        pos = random.choice(positions)
        return name[:pos] + name[pos] + name[pos:]
    
    def insert_letter(self, name: str) -> str:
        """
        Validator check: is_random_letter_inserted
        - Length must be original + 1
        - Levenshtein distance must be 1
        """
        letters = 'abcdefghijklmnopqrstuvwxyz'
        pos = random.randint(0, len(name))
        new_letter = random.choice(letters)
        return name[:pos] + new_letter + name[pos:]
    
    def add_title_prefix(self, name: str) -> str:
        """
        Validator check: is_title_added
        - Variation starts with title + space + original name
        - Or Levenshtein distance <= 2 from that pattern
        """
        titles = ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sir"]
        title = random.choice(titles)
        return f"{title} {name}"
    
    def add_title_suffix(self, name: str) -> str:
        """
        Validator check: is_suffix_added
        - Variation ends with space + suffix
        - Or Levenshtein distance <= 2 from that pattern
        """
        suffixes = ["Jr.", "Sr.", "III", "IV", "PhD", "MD", "Esq."]
        suffix = random.choice(suffixes)
        return f"{name} {suffix}"
    
    def shorten_to_initials(self, name: str) -> str:
        """
        Validator check: is_initials_only
        - Multi-part name converted to initials
        - Formats: "J.S." or "J. S." or "JS"
        """
        parts = name.split()
        if len(parts) < 2:
            return name
        
        # Use lowercase with dots (validator checks lowercase)
        initials = ".".join([p[0].lower() for p in parts]) + "."
        return initials
    
    def permute_name_parts(self, name: str) -> str:
        """
        Validator check: is_name_parts_permutation
        - Same parts, different order
        - sorted(original_parts) == sorted(variation_parts)
        - original_parts != variation_parts
        """
        parts = name.split()
        if len(parts) < 2:
            return name
        
        # Shuffle until different from original
        shuffled = parts.copy()
        attempts = 0
        while shuffled == parts and attempts < 10:
            random.shuffle(shuffled)
            attempts += 1
        
        if shuffled == parts:
            # Just swap first two if shuffle didn't work
            shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
        
        return ' '.join(shuffled)
    
    def initial_first_name(self, name: str) -> str:
        """
        Validator check: is_first_name_initial
        - First name becomes initial with dot
        - Format: "J. Smith" or "J.Smith"
        """
        parts = name.split()
        if len(parts) < 2:
            return name
        
        # Use lowercase initial with dot and space
        return f"{parts[0][0].lower()}. {' '.join(parts[1:])}"
    
    def abbreviate_name(self, name: str) -> str:
        """
        Validator check: is_name_abbreviated
        - Each part is shortened (starts with original, shorter length)
        - For single-part: variation is shorter and original.lower().startswith(variation.lower())
        - For multi-part: all parts shortened, orig.startswith(var) - CASE SENSITIVE!
        """
        parts = name.split()
        
        if len(parts) == 1:
            # Single part: just shorten it (case-insensitive check in validator)
            if len(parts[0]) > 2:
                return parts[0][:len(parts[0])-1]
            return name
        
        # Multi-part: shorten each part - MUST preserve case for startswith check
        result = []
        for part in parts:
            if len(part) > 2:
                # Shorten to 2-3 characters, preserve original case
                new_len = random.randint(2, min(3, len(part)-1))
                result.append(part[:new_len])  # Keep original case
            else:
                result.append(part)
        
        return ' '.join(result)

# if __name__ == "__main__":
    # rule_generator = RuleBasedGenerator()
    # print(aaa("kaat"))
    # original_name = "john smith"
    # rule_count = 10
    # rules = ['replace_spaces_with_random_special_characters', 'swap_adjacent_consonants']
    # rule_generator = RuleBasedGenerator()
    # rule_variations = rule_generator.generate_rule_based_variations(
    #     original_name, rule_count, rules
    # )
    # print(rule_variations)
# rules: ['replace_spaces_with_random_special_characters', 'swap_adjacent_consonants']