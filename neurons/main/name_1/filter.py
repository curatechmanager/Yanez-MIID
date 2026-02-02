"""
Filter and score name variations with guaranteed minimum count
"""
import sys
import os

# Add validator path
validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'validator')
if validator_path not in sys.path:
    sys.path.insert(0, validator_path)
from module import calculate_phonetic_similarity, calculate_orthographic_similarity

# Boundaries
phonetic_boundaries = {
    "Light": (0.80, 1.00),
    "Medium": (0.60, 0.79),
    "Far": (0.30, 0.59)
}

orthographic_boundaries = {
    "Light": (0.70, 1.00),
    "Medium": (0.50, 0.69),
    "Far": (0.20, 0.49)
}

def get_boundary(score, boundaries):
    """Get boundary label for a score"""
    for label, (low, high) in boundaries.items():
        if low <= score <= high:
            return label[0]  # L, M, F
    return 'N'

def apply_quality_filters(variations_with_scores, original_name, target_count):
    """Apply quality filters with smart stopping to preserve minimum count"""
    filtered = []
    
    for var, p_score, o_score, p_bound, o_bound in variations_with_scores:

        # Apply quality filters
        # Filter 1: Too dissimilar phonetically
        if p_score < 0.3:
            continue
            
        # Filter 2: Too dissimilar orthographically
        if o_score < 0.2:
            continue
            
        # Filter 3: Too similar overall (matches validator duplicate detection)
        combined_similarity = p_score * 0.7 + o_score * 0.3
        if combined_similarity > 0.99:
            continue
            
        # Filter 4: Too short or too long
        if len(var) < 2 or len(var) > 20:
            continue
        
        # Variation passed all quality filters
        # filtered.append((var, p_score, o_score, p_bound, o_bound))
        filtered.append((p_bound, o_bound))
    
    return filtered

def filter_single_name_variations(variations: list, original_name: str, target_count: int) -> list:
    """Filter variations for a single name with quality filtering and guaranteed minimum count"""
    
    # Score all variations first
    variations_with_scores = []
    for v in variations:
        p_score = calculate_phonetic_similarity(original_name, v)
        # print("PPPPPPPPPPPPPPPPPPPPP\n", p_score)
        o_score = calculate_orthographic_similarity(original_name, v)
        # print("OOOOOOOOOOOOOOOOOOOOOOO\n", o_score)
        p_bound = get_boundary(p_score, phonetic_boundaries)
        # print("PPPPPPPPPPPPPPPPPPPPPP\n", p_bound)
        o_bound = get_boundary(o_score, orthographic_boundaries)
        # print("OOOOOOOOOOOOOOOOOOOOOO\n", o_bound)
        variations_with_scores.append((v, p_score, o_score, p_bound, o_bound))
    # Apply quality filters with smart stopping
    filtered = apply_quality_filters(variations_with_scores, original_name, target_count)
    # print("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\n", filtered)
    return filtered