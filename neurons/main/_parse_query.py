import re
from typing import Dict, List, Optional, Any


class RobustQueryParser:
    """
    Robust query parser that handles multiple formats and edge cases
    
    This class uses a hierarchical pattern matching approach:
    - Most specific patterns first, general patterns last
    - Multiple extraction methods for the same data
    - Comprehensive fallbacks and defaults
    - Easy to extend and maintain
    """
    
    def __init__(self):
        """Initialize the parser with all pattern definitions"""
        
        # Rule patterns - ordered from most specific to most general
        self.rule_patterns = {
            # Character replacement rules - flexible matching with verb forms
            r'(?:replace|replacing).*spaces?.*special.*characters?': 'replace_spaces_with_random_special_characters',
            r'(?:replace|replacing).*double.*letters?.*single': 'replace_double_letters_with_single_letter',
            r'(?:replace|replacing).*vowels?.*(?:different|other).*vowels?': 'replace_random_vowel_with_random_vowel',
            r'(?:replace|replacing).*consonants?.*(?:different|other).*consonants?': 'replace_random_consonant_with_random_consonant',
            r'(?:replace|replacing).*(?:first|one).*letters?.*(?:similar|sound)': 'replace_random_vowel_with_random_vowel',
            
            # Character swapping rules - flexible matching with verb forms (active and passive)
            r'(?:swap|swapping).*adjacent.*consonants?': 'swap_adjacent_consonants',
            r'(?:swap|swapping).*adjacent.*syllables?': 'swap_adjacent_syllables',
            r'adjacent.*syllables?.*(?:have been|been|are).*(?:swap|swapped)': 'swap_adjacent_syllables',
            r'(?:swap|swapping).*(?:random.*)?(?:adjacent.*)?letters?': 'swap_random_letter',
            r'(?:transpose|transposing).*adjacent.*letters?': 'swap_random_letter',
            
            # Character removal rules - flexible matching with verb forms
            r'(?:delete|deleting).*random.*letters?': 'delete_random_letter',
            r'(?:remove|removing).*random.*vowels?': 'remove_random_vowel',
            r'(?:remove|removing).*random.*consonants?': 'remove_random_consonant',
            r'(?:remove|removing).*all.*spaces?': 'remove_all_spaces',
            r'(?:remove|removing).*or.*(?:add|adding).*vowels?': 'remove_random_vowel',
            
            # Character insertion rules - flexible matching with verb forms
            r'(?:duplicate|duplicating).*random.*letters?': 'duplicate_random_letter_as_double_letter',
            r'(?:insert|inserting).*random.*letters?': 'insert_random_letter',
            r'(?:add|adding).*(?:title.*)?prefix': 'add_random_leading_title',
            r'(?:add|adding).*(?:title.*)?suffix': 'add_random_trailing_title',
            r'(?:add|adding).*leading.*title': 'add_random_leading_title',
            r'(?:add|adding).*trailing.*title': 'add_random_trailing_title',
            
            # Name formatting rules - flexible matching with verb forms
            r'(?:use|using).*first.*name.*initial.*last.*name': 'initial_only_first_name',
            r'(?:convert|converting).*name.*initials?': 'shorten_name_to_initials',
            r'(?:shorten|shortening).*name.*initials?': 'shorten_name_to_initials',
            r'(?:abbreviate|abbreviating).*name.*parts?': 'shorten_name_to_abbreviations',
            r'(?:shorten|shortening).*name.*abbreviations?': 'shorten_name_to_abbreviations',
            
            # Structure change rules - flexible matching with verb forms
            r'(?:reorder|reordering).*name.*parts?': 'name_parts_permutations',
            r'name.*parts?.*permutations?': 'name_parts_permutations'
        }
        
        # Phonetic similarity patterns - ordered by specificity
        self.phonetic_patterns = [
            # Pattern 1: Parentheses format
            (r'phonetic similarity\s*\(([^)]+)\)', self._parse_parentheses_format),
            
            # Pattern 2: "Based on a X% threshold" format
            (r'phonetic similarity based on a\s+(\d+)%\s+(Light|Medium|Far)\s+threshold',
             lambda m: {m.group(2).title(): int(m.group(1))/100}),
            
            # Pattern 3: "Based on a distribution of" format with "sound-alike names"
            (r'phonetic similarity based on a distribution of\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far\s+sound-alike names', 
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 4: "Based on a distribution of" format
            (r'phonetic similarity based on a distribution of\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far', 
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 4: "Apply transformations in a ratio" format
            (r'For phonetic similarity, apply Light, Medium, and Far transformations in a ratio of\s+(\d+)%,\s+(\d+)%,\s+and\s+(\d+)%\s+respectively',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 5: "With a distribution of" format
            (r'phonetic similarity with a distribution of\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far', 
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 6: Percentage list format (20%, 30% and 50%)
            (r'phonetic similarity.*?(\d+%(?:,\s*\d+%)*\s+and\s+\d+%)', self._parse_percentage_list),
            
            # Pattern 7: Proportions format
            (r'phonetic similarity.*?proportions of\s+(\d+)%,\s+(\d+)%,\s+and\s+(\d+)%\s+respectively',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 8: Validation hints format
            (r'\[VALIDATION HINTS\].*?Phonetic similarity:\s*([^.;]+)', self._parse_validation_hints),
            
            # Pattern 9: Standard text patterns (general)
            (r'phonetic similarity.*?(\d+)%\s+Light.*?(\d+)%\s+Medium.*?(\d+)%\s+Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 10: Alternative text patterns
            (r'phonetic similarity.*?(\d+)%.*?Light.*?(\d+)%.*?Medium.*?(\d+)%.*?Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
        ]
        
        # Orthographic similarity patterns - ordered by specificity
        self.orthographic_patterns = [
            # Pattern 1: Parentheses format
            (r'orthographic similarity\s*\(([^)]+)\)', self._parse_parentheses_format),
            
            # Pattern 2: "According to the following distribution" format
            (r'orthographic similarity according to the following distribution:\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 3: "Is at X% Level" format
            (r'orthographic similarity is at\s+(\d+)%\s+(Light|Medium|Far)\s+visual similarity level',
             lambda m: {m.group(2).title(): int(m.group(1))/100}),
            
            # Pattern 4: "Apply transformations in a ratio" format
            (r'For orthographic similarity, apply Light, Medium, and Far transformations in a ratio of\s+(\d+)%,\s+(\d+)%,\s+and\s+(\d+)%\s+respectively',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 5: "Based on a distribution of" format - two levels
            (r'orthographic similarity based on a distribution of\s+(\d+)%\s+Light\s+and\s+(\d+)%\s+Medium',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100}),
            
            # Pattern 6: "Based on a distribution of" format - three levels
            (r'orthographic similarity based on a distribution of\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 7: "With a distribution of" format - two levels
            (r'orthographic similarity with\s+(\d+)%\s+Light\s+and\s+(\d+)%\s+Medium',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100}),
            
            # Pattern 8: "With a distribution of" format - three levels
            (r'orthographic similarity with a distribution of\s+(\d+)%\s+Light,\s+(\d+)%\s+Medium,\s+and\s+(\d+)%\s+Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 7: Percentage list format (20%, 30% and 50%)
            (r'orthographic similarity.*?(\d+%(?:,\s*\d+%)*\s+and\s+\d+%)', self._parse_percentage_list),
            
            # Pattern 8: Proportions format
            (r'orthographic similarity.*?proportions of\s+(\d+)%,\s+(\d+)%,\s+and\s+(\d+)%\s+respectively',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 9: Validation hints format
            (r'\[VALIDATION HINTS\].*?Orthographic similarity:\s*([^.;]+)', self._parse_validation_hints),
            
            # Pattern 10: Standard text patterns (general)
            (r'orthographic similarity.*?(\d+)%\s+Light.*?(\d+)%\s+Medium.*?(\d+)%\s+Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
            
            # Pattern 11: Alternative text patterns
            (r'orthographic similarity.*?(\d+)%.*?Light.*?(\d+)%.*?Medium.*?(\d+)%.*?Far',
             lambda m: {'Light': int(m.group(1))/100, 'Medium': int(m.group(2))/100, 'Far': int(m.group(3))/100}),
        ]
        
        # Rule percentage patterns - ordered by specificity
        self.rule_percentage_patterns = [
            r'approximately\s+(\d+)%\s+of\s+the\s+total\s+\d+\s+variations\s+should\s+follow',
            r'approximately\s+(\d+)%\s+of',
            r'also\s+include\s+(\d+)%\s+of',
            r'(\d+)%\s+of\s+the\s+total',
            r'(\d+)%\s+of\s+variations',
            r'include\s+(\d+)%',
            r'(\d+)%\s+should\s+follow'
        ]
    
    def _parse_parentheses_format(self, match) -> Dict[str, float]:
        """Parse parentheses format like (50% Light, 50% Medium)"""
        content = match.group(1) if hasattr(match, 'group') else match
        
        # Look for multiple percentages first
        light_match = re.search(r'(\d+)%\s+(?:with\s+)?Light', content, re.I)
        medium_match = re.search(r'(\d+)%\s+(?:with\s+)?Medium', content, re.I)
        far_match = re.search(r'(\d+)%\s+(?:with\s+)?Far', content, re.I)
        
        result = {}
        if light_match:
            result['Light'] = int(light_match.group(1)) / 100.0
        if medium_match:
            result['Medium'] = int(medium_match.group(1)) / 100.0
        if far_match:
            result['Far'] = int(far_match.group(1)) / 100.0
        
        # If no multiple percentages, look for single percentage
        if not result:
            single_match = re.search(r'(\d+)%\s+(Light|Medium|Far)', content, re.I)
            if single_match:
                level = single_match.group(2).title()
                percentage = int(single_match.group(1)) / 100.0
                result = {level: percentage}
        
        return result
    
    def _parse_percentage_list(self, match) -> Dict[str, float]:
        """Parse percentage list format like '20%, 30% and 50%' and map to Light, Medium, Far"""
        percentages = []
        
        # Extract all percentages from the match
        pct_matches = re.findall(r'(\d+)%', match.group(0))
        percentages = [int(pct) / 100.0 for pct in pct_matches]
        
        # Map percentages to Light, Medium, Far in order
        result = {}
        levels = ['Light', 'Medium', 'Far']
        
        for i, pct in enumerate(percentages):
            if i < len(levels):
                result[levels[i]] = pct
        
        return result
    
    def _parse_validation_hints(self, match) -> Dict[str, float]:
        """Parse validation hints format"""
        hints_text = match.group(1)
        hints_match = re.search(r'(\d+)%\s+Light.*?(\d+)%\s+Medium(?:.*?(\d+)%\s+Far)?', hints_text, re.I)
        
        if hints_match:
            result = {
                'Light': int(hints_match.group(1)) / 100.0,
                'Medium': int(hints_match.group(2)) / 100.0
            }
            if hints_match.group(3):
                result['Far'] = int(hints_match.group(3)) / 100.0
            return result
        
        return {}
    
    def _normalize_percentages(self, percentages: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize percentages to ensure they sum to 1.0
        
        Args:
            percentages: Dictionary with similarity levels and their percentages
            
        Returns:
            Normalized dictionary where all percentages sum to 1.0
        """
        if not percentages:
            return percentages
        
        total = sum(percentages.values())
        
        # If total is already 1.0 (within small tolerance), return as-is
        if abs(total - 1.0) < 0.001:
            return percentages
        
        # If total is 0, return empty dict
        if total == 0:
            return {}
        
        # Normalize all percentages
        normalized = {}
        for level, pct in percentages.items():
            normalized[level] = pct / total
        
        return normalized
    
    def extract_variation_count(self, query: str) -> int:
        """Extract variation count with multiple fallback patterns"""
        patterns = [
            r'Generate exactly\s+(\d+)\s+variations',
            r'Generate\s+(\d+)\s+variations',
            r'(\d+)\s+variations',
            r'total\s+(\d+)\s+variations'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.I)
            if match:
                return int(match.group(1))
        
        return 15  # Default fallback
    
    def extract_rule_percentage(self, query: str) -> float:
        """Extract rule percentage with multiple fallback patterns"""
        for pattern in self.rule_percentage_patterns:
            match = re.search(pattern, query, re.I)
            if match:
                return int(match.group(1)) / 100.0
        
        return 0.0  # Default fallback
    
    def _extract_rules_intelligently(self, query: str) -> List[str]:
        """
        Intelligent rule extraction using semantic understanding
        
        This method identifies rule transformations regardless of exact wording
        by looking for action keywords and their targets.
        """
        rules = []
        query_lower = query.lower()
        
        # Rule action mappings - more flexible approach
        rule_actions = {
            # Character replacement
            'replace_spaces_with_random_special_characters': [
                'replace spaces', 'spaces with', 'special characters', 'replace space'
            ],
            'replace_double_letters_with_single_letter': [
                'double letters', 'single letter', 'replace double'
            ],
            'replace_random_vowel_with_random_vowel': [
                'replace vowel', 'different vowel', 'other vowel', 'vowel with'
            ],
            'replace_random_consonant_with_random_consonant': [
                'replace consonant', 'different consonant', 'other consonant', 'consonant with'
            ],
            
            # Character swapping
            'swap_adjacent_consonants': [
                'swap consonant', 'adjacent consonant', 'consonant swap'
            ],
            'swap_adjacent_syllables': [
                'swap syllable', 'adjacent syllable', 'syllable swap'
            ],
            'swap_random_letter': [
                'swap letter', 'adjacent letter', 'transpose letter', 'letter swap'
            ],
            
            # Character removal
            'delete_random_letter': [
                'delete letter', 'remove letter', 'delete random'
            ],
            'remove_random_vowel': [
                'remove vowel', 'delete vowel'
            ],
            'remove_random_consonant': [
                'remove consonant', 'delete consonant'
            ],
            'remove_all_spaces': [
                'remove spaces', 'remove all space', 'delete space'
            ],
            
            # Character insertion
            'duplicate_random_letter_as_double_letter': [
                'duplicate letter', 'double letter', 'repeat letter'
            ],
            'insert_random_letter': [
                'insert letter', 'add letter'
            ],
            'add_random_leading_title': [
                'add title', 'title prefix', 'leading title', 'add prefix'
            ],
            'add_random_trailing_title': [
                'title suffix', 'trailing title', 'add suffix'
            ],
            
            # Name formatting
            'initial_only_first_name': [
                'first name initial', 'initial first', 'first initial'
            ],
            'shorten_name_to_initials': [
                'name to initial', 'convert initial', 'shorten initial', 'name initial'
            ],
            'shorten_name_to_abbreviations': [
                'abbreviate name', 'name abbreviation', 'shorten name'
            ],
            
            # Structure changes
            'name_parts_permutations': [
                'reorder name', 'name parts', 'permutation', 'rearrange name'
            ]
        }
        
        # Score each rule based on keyword matches
        rule_scores = {}
        
        for rule_name, keywords in rule_actions.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            
            if score > 0:
                rule_scores[rule_name] = score
        
        # Add rules with highest scores first
        for rule_name, score in sorted(rule_scores.items(), key=lambda x: x[1], reverse=True):
            if rule_name not in rules:
                rules.append(rule_name)
        
        return rules
    
    def extract_rules(self, query: str) -> List[str]:
        """Extract rules using both pattern matching and intelligent parsing"""
        
        # First try pattern-based extraction
        rules = []
        query_lower = query.lower()
        
        for pattern, rule_name in self.rule_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                if rule_name not in rules:  # Avoid duplicates
                    rules.append(rule_name)
        
        # If pattern matching found rules, return them
        if rules:
            return rules
        
        # Otherwise, use intelligent extraction
        return self._extract_rules_intelligently(query)
    
    def _extract_percentages_and_levels(self, text: str, similarity_type: str) -> Dict[str, float]:
        """
        Intelligent extraction of percentages and similarity levels using semantic parsing
        
        This method finds all percentages and their associated levels (Light/Medium/Far)
        regardless of the specific format used.
        """
        result = {}
        
        # Method 1: Direct percentage-level associations with exact matching
        for level in ['Light', 'Medium', 'Far']:
            # Pattern: "based on X% Level" - most specific
            based_on_match = re.search(rf'based on\s+(\d+)%\s+{level}', text, re.I)
            if based_on_match:
                pct = based_on_match.group(1)
                result[level] = int(pct) / 100.0
                return result  # Return immediately for exact match
            
            # Pattern: "X% Level" or "Level X%" 
            level_pct_match = re.search(rf'(\d+)%\s+{level}|{level}\s+(\d+)%', text, re.I)
            if level_pct_match:
                pct = level_pct_match.group(1) or level_pct_match.group(2)
                result[level] = int(pct) / 100.0
                return result  # Return immediately for exact match
        
        # Method 2: Sequential mapping when percentages and levels are separate
        percentage_matches = re.findall(r'(\d+)%', text)
        level_matches = re.findall(r'\b(Light|Medium|Far)\b', text, re.I)
        
        if len(percentage_matches) > 0 and len(level_matches) > 0:
            # If we have equal numbers of percentages and levels, map them in order
            if len(percentage_matches) == len(level_matches):
                for i, (pct, level) in enumerate(zip(percentage_matches, level_matches)):
                    result[level.title()] = int(pct) / 100.0
            
            # If we have 3 percentages but fewer levels mentioned, assume Light/Medium/Far order
            elif len(percentage_matches) == 3 and len(level_matches) == 0:
                levels = ['Light', 'Medium', 'Far']
                for i, pct in enumerate(percentage_matches):
                    if i < len(levels):
                        result[levels[i]] = int(pct) / 100.0
        
        # Method 3: Single percentage with level context
        if not result and len(percentage_matches) == 1:
            pct = int(percentage_matches[0]) / 100.0
            
            # Look for level context around the percentage
            for level in ['Light', 'Medium', 'Far']:
                if level.lower() in text.lower():
                    result[level] = pct
                    return result  # Return immediately
        
        return result
    
    def extract_similarity_distribution(self, query: str, similarity_type: str) -> Dict[str, float]:
        """
        Enhanced similarity distribution extraction using intelligent parsing
        
        This method combines pattern matching with semantic understanding
        to handle any format Ollama might generate.
        """
        
        # First, try the existing pattern-based approach for known formats
        patterns = self.phonetic_patterns if similarity_type == 'phonetic' else self.orthographic_patterns
        
        for pattern, parser_func in patterns:
            match = re.search(pattern, query, re.I | re.DOTALL)
            if match:
                try:
                    result = parser_func(match)
                    if result:  # Only return if we got valid results
                        return self._normalize_percentages(result)
                except Exception as e:
                    print(f"Warning: Pattern parsing failed: {e}")
                    continue
        
        # If pattern matching fails, use intelligent semantic extraction
        # Extract the relevant section of text for this similarity type
        similarity_section = ""
        
        # More specific keyword matching for each similarity type
        if similarity_type == 'phonetic':
            # Look for phonetic similarity mentions - be more specific
            phonetic_patterns = [
                r'phonetic similarity[^,]*(?:based on|with|using|of)[^.]*',
                r'ensuring phonetic similarity[^.]*',
            ]
            for pattern in phonetic_patterns:
                matches = re.findall(pattern, query, re.I)
                if matches:
                    similarity_section = matches[0]  # Take first match only
                    break
        
        elif similarity_type == 'orthographic':
            # Look for orthographic similarity mentions - be more specific  
            orthographic_patterns = [
                r'orthographic similarity[^,]*(?:based on|with|using|of|according to)[^.]*',
                r'ensure orthographic similarity[^.]*',
            ]
            for pattern in orthographic_patterns:
                matches = re.findall(pattern, query, re.I)
                if matches:
                    similarity_section = matches[0]  # Take first match only
                    break
        
        # If we found a relevant section, extract percentages and levels
        if similarity_section:
            result = self._extract_percentages_and_levels(similarity_section, similarity_type)
            if result:
                # Normalize percentages to ensure they sum to 1.0
                return self._normalize_percentages(result)
        
        # Final fallback: search the entire query
        result = self._extract_percentages_and_levels(query, similarity_type)
        if result:
            return self._normalize_percentages(result)
        
        # Ultimate fallback: look for any mention of similarity type
        if similarity_type.lower() in query.lower():
            return {'Medium': 1.0}
        
        return {}
    
    def extract_uav_seed_name(self, query: str) -> Optional[str]:
        """Extract UAV seed name from Phase 3 requirements"""
        uav_match = re.search(r'For the seed "([^"]+)" ONLY', query, re.I)
        return uav_match.group(1) if uav_match else None
    
    def parse_query_template(self, query_template: str) -> Dict[str, Any]:
        """
        Main parsing function that extracts all requirements
        
        This demonstrates the complete parsing methodology:
        1. Initialize with defaults
        2. Extract each component using specialized methods
        3. Apply fallbacks where needed
        4. Return comprehensive results
        """
        
        # Initialize with sensible defaults
        requirements = {
            'variation_count': 15,
            'rule_percentage': 0.0,
            'rules': [],
            'phonetic_similarity': {},
            'orthographic_similarity': {},
            'uav_seed_name': None,
            'rule_sentence': None
        }
        
        # Extract each component using specialized methods
        requirements['variation_count'] = self.extract_variation_count(query_template)
        requirements['rule_percentage'] = self.extract_rule_percentage(query_template)
        requirements['rules'] = self.extract_rules(query_template)
        requirements['phonetic_similarity'] = self.extract_similarity_distribution(query_template, 'phonetic')
        requirements['orthographic_similarity'] = self.extract_similarity_distribution(query_template, 'orthographic')
        requirements['uav_seed_name'] = self.extract_uav_seed_name(query_template)
        
        # Extract rule sentence for logging
        rule_sentence_match = re.search(r'(Approximately\s+\d+%.*?rule-based transformations:[^.]+\.)', query_template, re.I)
        if rule_sentence_match:
            requirements['rule_sentence'] = rule_sentence_match.group(1)
        
        return requirements


# Create global parser instance
_parser = RobustQueryParser()

def parse_query_template(query_template: str) -> Dict:
    """Extract requirements from query template using robust parsing system"""
    return _parser.parse_query_template(query_template)

if __name__ == "__main__":
    import sys
    import json
    
    # Check if we should run test mode with test.txt
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("=== TEST MODE: Reading from test.txt ===\n")
        
        try:
            with open("test.txt", 'r', encoding='utf-8') as f:
                test_query = f.read().strip()

            # Parse the query
            result = parse_query_template(test_query)
            
            # Print only the rules
            print(f"Variation Count: {result['variation_count']}")
            print(f"Rule Percentage: {result['rule_percentage']:.1%}")
            print(f"Rules Found: {len(result['rules'])}")
            print(f"Phonetic: {result['phonetic_similarity']}")
            print(f"Orthographic: {result['orthographic_similarity']}")
            print("✅ Parsed successfully")
            
            
        except FileNotFoundError:
            print("❌ test.txt file not found!")
        except Exception as e:
            print(f"❌ Error reading test.txt: {e}")
    
    else:
        # Original JSON file parsing mode
        if len(sys.argv) < 2:
            input_file = "example_synapse.json"
        else:
            input_file = sys.argv[1]
        
        print(f"📂 Loading synapse from: {input_file}\n")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        query_template = data['query_template']
        
        result = parse_query_template(query_template)
        print("Parsed requirements:")
        for key, value in result.items():
            print(f"  {key}: {value}")
