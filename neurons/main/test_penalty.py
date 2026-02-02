#!/usr/bin/env python3
"""
Extra Names Penalty Testing Tool for MIID Miners

This tool helps miners test their variations before submitting to avoid extra names penalties.
It simulates the validator's extra names penalty calculation logic.
"""

import re
from typing import Dict, List, Set, Tuple
from unicodedata import category as unicode_category


def normalize_variations_structure(all_variations):
    """
    Normalize variations structure from mixed UAV/standard format to legacy format.
    This replicates the validator's process_new_variations_structure normalization.
    
    Args:
        all_variations: Dictionary that may contain mixed UAV/standard format
        
    Returns:
        Dictionary with normalized variations in legacy format
    """
    normalized_variations = {}
    
    for seed_name, seed_data in all_variations.items():
        if isinstance(seed_data, list):
            # Old format: variations only
            normalized_variations[seed_name] = seed_data
        elif isinstance(seed_data, dict):
            # New format: { "variations": [...], "uav": {...} }
            if "variations" in seed_data:
                normalized_variations[seed_name] = seed_data.get("variations") or []
            else:
                # If no variations key, treat as empty
                normalized_variations[seed_name] = []
        else:
            # Unknown format, treat as empty
            normalized_variations[seed_name] = []
    
    return normalized_variations


def remove_disallowed_unicode(text: str, preserve_comma: bool = False) -> str:
    """Remove disallowed Unicode characters from text, keeping only:
    - Letters (any language)
    - Marks (diacritics)
    - ASCII digits and space
    - Comma (if preserve_comma=True)
    """
    allowed = []
    allowed_chars = " ,0123456789" if preserve_comma else " 0123456789"
    
    for c in text:
        codepoint = ord(c)
        
        # Exclude phonetic small-cap blocks + Latin Extended-D block
        if (
            0x1D00 <= codepoint <= 0x1D7F or  # Phonetic Extensions
            0x1D80 <= codepoint <= 0x1DBF or  # Phonetic Extensions Supplement
            0xA720 <= codepoint <= 0xA7FF      # Latin Extended-D
        ):
            continue
        
        cat = unicode_category(c)
        if cat.startswith("L"):       # Letter (any language)
            allowed.append(c)
        elif cat.startswith("M"):     # Mark (diacritics)
            allowed.append(c)
        elif c in allowed_chars:      # ASCII digits, space, and optionally comma
            allowed.append(c)
    
    return "".join(allowed)


def normalize_dob(dob_str: str) -> str:
    """Normalize DOB string by removing extra spaces and standardizing format"""
    if not dob_str:
        return ""
    # Remove all spaces and convert to lowercase
    normalized = dob_str.replace(" ", "").replace("-", "").replace("/", "").replace(".", "").lower()
    return normalized


def normalize_address(addr_str: str) -> str:
    """Normalize address string by removing extra spaces and standardizing format"""
    if not addr_str:
        return ""
    # Remove extra spaces, convert to lowercase, and standardize common separators
    normalized = " ".join(addr_str.split()).lower()
    # Replace common separators with spaces
    normalized = normalized.replace(",", " ").replace(";", " ").replace("-", " ")
    # Remove multiple spaces
    normalized = " ".join(normalized.split())
    return normalized


def calculate_extra_names_penalty(
    all_variations: Dict, 
    seed_names: List[str], 
    variation_count: int
) -> Tuple[float, Dict]:
    """
    Calculate extra names penalty exactly like the validator does.
    First normalizes variations structure (handles UAV format), then calculates penalties.
    
    Args:
        all_variations: Dict with variations (can be mixed UAV/standard format)
        seed_names: List of expected names
        variation_count: Expected number of variations per name
        
    Returns:
        Tuple of (penalty_amount, penalty_breakdown)
    """
    
    # First normalize the variations structure (like validator does)
    variations = normalize_variations_structure(all_variations)
    
    extra_names_penalty = 0.0
    penalty_breakdown = {
        "invalid_names_penalty": 0.0,
        "too_many_names_penalty": 0.0,
        "too_many_dob_penalty": 0.0,
        "too_many_address_penalty": 0.0,
        "duplicate_names_penalty": 0.0,
        "duplicate_dob_penalty": 0.0,
        "duplicate_address_penalty": 0.0,
        "duplicate_first_sections_penalty": 0.0,
        "invalid_names": [],
        "details": []
    }
    
    # 1. Calculate penalty for unexpected names (extra variations)
    invalid_names = set(variations.keys()) - set(seed_names)
    if invalid_names:
        # 10% penalty per extra name, up to 70% max
        extra_penalty = min(0.7, len(invalid_names) * 0.1)
        extra_names_penalty += extra_penalty
        penalty_breakdown["invalid_names_penalty"] = extra_penalty
        penalty_breakdown["invalid_names"] = list(invalid_names)
        penalty_breakdown["details"].append(f"Invalid names: {invalid_names} → penalty {extra_penalty:.3f}")
    
    # 2. Penalty for too many variations per name, DOB, and addresses
    for name, vars_list in variations.items():
        if name not in seed_names:
            continue  # Skip invalid names (already penalized above)
            
        # Extract name, DOB, and address variations from the structure
        name_variations = [var[0] for var in vars_list if len(var) > 0]
        dob_variations = [var[1] for var in vars_list if len(var) > 1]
        address_variations = [var[2] for var in vars_list if len(var) > 2]
        
        if variation_count > 0:
            allowed_with_grace = int(variation_count * 1.2)  # 20% grace, rounded down
            
            # Check names for variation count
            if len(name_variations) > allowed_with_grace:
                too_many = len(name_variations) - allowed_with_grace
                penalty_too_many = too_many * 0.05  # 5% per extra
                extra_names_penalty += penalty_too_many
                penalty_breakdown["too_many_names_penalty"] += penalty_too_many
                penalty_breakdown["details"].append(f"{name}: Too many name variations {len(name_variations)}/{allowed_with_grace} → penalty {penalty_too_many:.3f}")
            
            # Check DOB for variation count
            if len(dob_variations) > allowed_with_grace:
                too_many = len(dob_variations) - allowed_with_grace
                penalty_too_many = too_many * 0.05  # 5% per extra
                extra_names_penalty += penalty_too_many
                penalty_breakdown["too_many_dob_penalty"] += penalty_too_many
                penalty_breakdown["details"].append(f"{name}: Too many DOB variations {len(dob_variations)}/{allowed_with_grace} → penalty {penalty_too_many:.3f}")
            
            # Check addresses for variation count
            if len(address_variations) > allowed_with_grace:
                too_many = len(address_variations) - allowed_with_grace
                penalty_too_many = too_many * 0.05  # 5% per extra
                extra_names_penalty += penalty_too_many
                penalty_breakdown["too_many_address_penalty"] += penalty_too_many
                penalty_breakdown["details"].append(f"{name}: Too many address variations {len(address_variations)}/{allowed_with_grace} → penalty {penalty_too_many:.3f}")
        
        # 3. Penalty for duplicate variations - names
        duplicates_names = len(name_variations) - len(set(name_variations))
        if duplicates_names > 0:
            penalty_duplicates = duplicates_names * 0.05  # 5% penalty per duplicate
            extra_names_penalty += penalty_duplicates
            penalty_breakdown["duplicate_names_penalty"] += penalty_duplicates
            penalty_breakdown["details"].append(f"{name}: Duplicate name variations {duplicates_names} → penalty {penalty_duplicates:.3f}")
        
        # 4. Penalty for duplicate variations - DOB (with normalization)
        dob_duplicates_penalty = 0.0
        if dob_variations:
            normalized_dobs = [normalize_dob(dob) for dob in dob_variations if dob]
            duplicates_dob = len(normalized_dobs) - len(set(normalized_dobs))
            if duplicates_dob > 0:
                penalty_duplicates = duplicates_dob * 0.05  # 5% penalty per duplicate
                dob_duplicates_penalty += penalty_duplicates
                penalty_breakdown["details"].append(f"{name}: Duplicate DOB variations {duplicates_dob} → penalty {penalty_duplicates:.3f}")
        
        dob_duplicates_penalty = min(dob_duplicates_penalty, 0.1)  # Max 10% penalty
        extra_names_penalty += dob_duplicates_penalty
        penalty_breakdown["duplicate_dob_penalty"] += dob_duplicates_penalty
        
        # 5. Penalty for duplicate variations - addresses (with normalization)
        address_duplicates_penalty = 0.0
        if address_variations:
            # Check for exact duplicates
            normalized_addresses = [normalize_address(addr) for addr in address_variations if addr]
            duplicates_addresses = len(normalized_addresses) - len(set(normalized_addresses))
            if duplicates_addresses > 0:
                penalty_duplicates = duplicates_addresses * 0.05  # 5% penalty per duplicate
                address_duplicates_penalty += penalty_duplicates
                penalty_breakdown["details"].append(f"{name}: Duplicate address variations {duplicates_addresses} → penalty {penalty_duplicates:.3f}")
            
            # Check for duplicate first sections (before first comma)
            first_sections = []
            for addr in address_variations:
                if addr and addr.strip():
                    # Remove disallowed Unicode characters but preserve commas
                    addr = remove_disallowed_unicode(addr, preserve_comma=True)
                    if not addr or not addr.strip():
                        continue
                    # Strip leading commas and spaces
                    normalized_addr = addr.strip().lstrip(',').strip()
                    if not normalized_addr:
                        continue
                    # Split on comma and get the first section
                    parts = normalized_addr.split(',')
                    if parts:
                        first_section = parts[0].strip()
                        # If first section is less than 4 characters, combine with second section
                        if len(first_section) < 4 and len(parts) > 1:
                            first_section = (parts[0].strip() + " " + parts[1].strip()).strip()
                        # Normalize the first section (lowercase, remove extra spaces, remove 2-letter words)
                        words = first_section.split()
                        filtered_words = [word for word in words if len(word) > 2]
                        normalized_first = " ".join(filtered_words).lower().strip()
                        if normalized_first:
                            first_sections.append(normalized_first)
            
            if first_sections:
                # Count how many addresses share the same first section
                first_section_counts = {}
                for section in first_sections:
                    first_section_counts[section] = first_section_counts.get(section, 0) + 1
                # Penalize if any first section appears more than once
                duplicate_first_sections = sum(count - 1 for count in first_section_counts.values() if count > 1)
                if duplicate_first_sections > 0:
                    penalty_first_section = duplicate_first_sections * 0.05  # 5% penalty per duplicate
                    address_duplicates_penalty += penalty_first_section
                    penalty_breakdown["duplicate_first_sections_penalty"] += penalty_first_section
                    penalty_breakdown["details"].append(f"{name}: Duplicate first sections {duplicate_first_sections} → penalty {penalty_first_section:.3f}")
        
        address_duplicates_penalty = min(address_duplicates_penalty, 0.5)  # Max 50% penalty
        extra_names_penalty += address_duplicates_penalty
        penalty_breakdown["duplicate_address_penalty"] += address_duplicates_penalty
    
    # Cap total penalty at 1.0 (100%)
    extra_names_penalty = min(extra_names_penalty, 1.0)
    
    return extra_names_penalty, penalty_breakdown


def test_variations(all_variations: Dict, seed_names: List[str], variation_count: int):
    """
    Test variations and provide detailed feedback about potential penalties.
    Handles both UAV and standard format variations.
    """
    # First normalize the variations structure (like validator does)
    variations = normalize_variations_structure(all_variations)
    
    # Calculate penalty
    penalty, breakdown = calculate_extra_names_penalty(variations, seed_names, variation_count)
    print(penalty,breakdown)
    
    return penalty, breakdown


# Example usage and test cases
if __name__ == "__main__":
    
    # Test Case 1: Perfect submission (no penalties)
    print("TEST CASE 1: Perfect Submission")
    perfect_variations = {
        "John Smith": [
            ["John Smith", "1990-01-01", "302, Wenhui Road, Zhaohui, Gongshu District, Hangzhou City, Zhejiang, 310014, China"],
            ["Jon Smith", "1990-01-02", "348, Wenhui Road, Zhaohui, Gongshu District, Hangzhou City, Zhejiang, 310014, China"],
            ["J. Smith", "1990-01-03", "108, Wenhui Road, 打铁关社区, Wenhui, Gongshu District, Hangzhou City, Zhejiang, 310014, China"]
        ],
        "Mary Johnson": [
            ["Mary Johnson", "1985-05-15", "456 Elm St, Boston, MA"],
            ["M. Johnson", "1985-05-16", "457 Maple Ave, Boston, MA"],
            ["Mary J.", "1985-05-17", "458 Cedar St, Boston, MA"]
        ]
    }
    test_variations(perfect_variations, ["John Smith", "Mary Johnson"], 3)
