"""
Filter and score name variations for non-Latin names (phonetic-only) with guaranteed minimum count
"""
import sys
import os

# Add validator path
validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
if validator_path not in sys.path:
    sys.path.insert(0, validator_path)
from module import calculate_phonetic_similarity

# Phonetic boundaries only (no orthographic for non-Latin)
phonetic_boundaries = {
    "Light": (0.80, 1.00),
    "Medium": (0.60, 0.79),
    "Far": (0.30, 0.59)
}

def get_phonetic_boundary(score):
    """Get phonetic boundary label for a score"""
    for label, (low, high) in phonetic_boundaries.items():
        if low <= score <= high:
            return label[0]  # L, M, F
    return 'N'

def apply_quality_filters_phonetic(variations_with_scores, original_name, target_count):
    """Apply phonetic-only quality filters with smart stopping to preserve minimum count"""
    filtered = []
    
    for var, p_score, p_bound in variations_with_scores:
        # Smart stopping: if we're at or below target + 5, stop filtering to preserve count
        if len(filtered) <= target_count + 5:
            filtered.append((var, p_score, p_bound))
            continue
        
        # Apply quality filters (phonetic-only for non-Latin)
        # Filter 1: Too dissimilar phonetically
        if p_score < 0.3:
            continue
            
        # Filter 2: Too similar phonetically (since no orthographic for non-Latin)
        if p_score > 0.99:
            continue
            
        # Filter 3: Too short or too long
        if len(var) < 2 or len(var) > 20:
            continue
        
        # Variation passed all quality filters
        filtered.append((var, p_score, p_bound))
    
    return filtered

def filter_single_name_variations_nonlatin(variations: list, original_name: str, target_count: int) -> list:
    """Filter variations for a single name (phonetic-only) with quality filtering and guaranteed minimum count"""
    
    # Score all variations with phonetic-only scoring
    variations_with_scores = []
    for v in variations:
        p_score = calculate_phonetic_similarity(original_name, v)
        p_bound = get_phonetic_boundary(p_score)
        variations_with_scores.append((v, p_score, p_bound))
    
    # Apply quality filters with smart stopping
    filtered = apply_quality_filters_phonetic(variations_with_scores, original_name, target_count)
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$\n", filtered)
    return filtered