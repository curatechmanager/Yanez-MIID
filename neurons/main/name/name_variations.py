#!/usr/bin/env python3
"""
Basic Name Variations Generator

Simple phonetic transformations for generating name variations.
Used as a fallback when more sophisticated methods are not available.
"""

import random
from typing import List


def generate_name_variations(name: str, limit: int = 10) -> List[str]:
    """Generate basic phonetic variations using transformation rules"""
    
    # Basic phonetic substitution rules
    transformations = [
        ("ph", ["f"]),
        ("f", ["ph"]),
        ("c", ["k", "s"]),
        ("k", ["c", "ck"]),
        ("j", ["jh"]),
        ("s", ["z"]),
        ("z", ["s"]),
        ("x", ["ks"]),
        ("v", ["w"]),
        ("w", ["v"]),
        ("oo", ["u"]),
        ("u", ["oo"]),
        ("ee", ["i"]),
        ("i", ["ee", "y"]),
        ("y", ["i"]),
        ("o", ["oh", "o"]),
        ("a", ["ah", "aa"]),
        ("h", ["", "h"]),
        ("th", ["t"]),
        ("ck", ["k"]),
        ("qu", ["kw"]),
    ]
    
    def generate_variants_for_word(word):
        """Generate variants for a single word"""
        variants = set([word])
        lw = word.lower()

        for src, subs in transformations:
            if src in lw:
                for sub in subs:
                    new_word = lw.replace(src, sub)
                    variants.add(new_word)

        return {v.capitalize() for v in variants}

    # Split name into parts
    parts = name.split()
    
    # If single word, just apply transformations directly
    if len(parts) == 1:
        variants = generate_variants_for_word(parts[0])
        variants.discard(name)  # Remove original
        result = list(variants)[:limit]
        # print(f"    fallback: {result}")
        return result
    
    # For multi-part names, generate variations more efficiently
    all_variations = set()
    
    # Generate variations for each part separately
    for i, part in enumerate(parts):
        part_variants = generate_variants_for_word(part)
        part_variants.discard(part)  # Remove original part
        
        # Create full name variations by replacing this part
        for variant in part_variants:
            new_parts = parts.copy()
            new_parts[i] = variant
            full_variation = " ".join(new_parts)
            if full_variation != name:
                all_variations.add(full_variation)
            
            # Stop if we have enough variations
            if len(all_variations) >= limit * 2:
                break
        
        if len(all_variations) >= limit * 2:
            break
    
    # Remove original name
    all_variations.discard(name)
    result = list(all_variations)[:limit]
    print(f"    fallback: {result}")
    return result


def generate_simple_variations(name: str, count: int) -> List[str]:
    """Generate simple character-level variations"""
    variations = set()
    
    # Character removal
    for i in range(len(name)):
        if name[i].isalpha():
            var = name[:i] + name[i+1:]
            if var and var != name:
                variations.add(var)
    
    # Character duplication
    for i in range(len(name)):
        if name[i].isalpha():
            var = name[:i+1] + name[i] + name[i+1:]
            variations.add(var)
    
    # Character swapping
    for i in range(len(name) - 1):
        if name[i].isalpha() and name[i+1].isalpha():
            chars = list(name)
            chars[i], chars[i+1] = chars[i+1], chars[i]
            var = ''.join(chars)
            variations.add(var)
    
    # Remove original name
    variations.discard(name)
    return list(variations)[:count]


if __name__ == "__main__":
    # Test the function
    test_name = "CHERSTVOVA"
    variations = generate_name_variations(test_name, limit=15)
    print(f"Variations for '{test_name}':")
    for i, var in enumerate(variations, 1):
        print(f"{i:2d}. {var}")