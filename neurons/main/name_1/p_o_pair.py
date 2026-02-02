"""
Generate phonetic-orthographic pairs for dual similarity satisfaction
"""

def create_p_o_pairs(goal_phonetic, goal_orthographic):
    """
    Create phonetic-orthographic pairs from distribution goals.
    
    Args:
        goal_phonetic: Dict like {'Light': 1, 'Medium': 5, 'Far': 4}
        goal_orthographic: Dict like {'Light': 1, 'Medium': 3, 'Far': 6}
    
    Returns:
        List of tuples with counts: [('L', 'L')-1, ('M', 'M')-3, ('M', 'F')-2, ('F', 'F')-4]
    """
    
    # Convert to short form
    level_map = {'Light': 'L', 'Medium': 'M', 'Far': 'F'}
    
    # Convert goals to short form
    p_goals = {level_map[k]: v for k, v in goal_phonetic.items() if v > 0}
    o_goals = {level_map[k]: v for k, v in goal_orthographic.items() if v > 0}
    
    # Create expanded lists
    p_list = []
    for level, count in p_goals.items():
        p_list.extend([level] * count)
    
    o_list = []
    for level, count in o_goals.items():
        o_list.extend([level] * count)
    
    # Create pairs by matching indices
    total_variations = len(p_list)
    pairs = []
    
    # Strategy: Distribute orthographic requirements across phonetic requirements
    # to create balanced pairs
    
    # Sort orthographic list to prioritize higher-weighted categories first
    # Assuming priority: L > M > F (but this can be adjusted based on weights)
    o_sorted = sorted(o_list, key=lambda x: {'L': 3, 'M': 2, 'F': 1}[x], reverse=True)
    
    # Create pairs
    for i in range(total_variations):
        if i < len(o_sorted):
            pairs.append((p_list[i], o_sorted[i]))
        else:
            # If we run out of orthographic requirements, use the last available
            pairs.append((p_list[i], o_sorted[-1]))
    
    # Count occurrences of each pair
    pair_counts = {}
    for pair in pairs:
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    # Format output
    result = []
    for pair, count in sorted(pair_counts.items()):
        result.append(f"('{pair[0]}', '{pair[1]}')-{count}")
    
    return result, pair_counts


def optimize_p_o_pairs(goal_phonetic, goal_orthographic):
    """
    Create optimized phonetic-orthographic pairs using systematic distribution.
    
    This version ensures better distribution by solving the dual constraint problem.
    """
    
    # Convert to short form
    level_map = {'Light': 'L', 'Medium': 'M', 'Far': 'F'}
    
    p_goals = {level_map[k]: v for k, v in goal_phonetic.items()}
    o_goals = {level_map[k]: v for k, v in goal_orthographic.items()}
    
    # Create matrix of all possible combinations
    combinations = []
    for p_level in ['L', 'M', 'F']:
        for o_level in ['L', 'M', 'F']:
            if p_goals.get(p_level, 0) > 0:  # Only if phonetic level is needed
                combinations.append((p_level, o_level))
    
    # Solve distribution problem
    pair_counts = {}
    remaining_p = p_goals.copy()
    remaining_o = o_goals.copy()
    
    # Distribute variations to satisfy both constraints
    while sum(remaining_p.values()) > 0 and sum(remaining_o.values()) > 0:
        # Find best combination to assign
        best_combo = None
        best_score = -1
        
        for p_level, o_level in combinations:
            if remaining_p.get(p_level, 0) > 0 and remaining_o.get(o_level, 0) > 0:
                # Score based on remaining needs (prioritize balanced distribution)
                p_need = remaining_p[p_level]
                o_need = remaining_o[o_level]
                score = min(p_need, o_need)  # Prioritize combinations that satisfy both needs
                
                if score > best_score:
                    best_score = score
                    best_combo = (p_level, o_level)
        
        if best_combo:
            # Assign one variation to this combination
            pair_counts[best_combo] = pair_counts.get(best_combo, 0) + 1
            remaining_p[best_combo[0]] -= 1
            remaining_o[best_combo[1]] -= 1
        else:
            break
    
    # Handle any remaining requirements (due to imbalanced totals)
    total_p_remaining = sum(remaining_p.values())
    total_o_remaining = sum(remaining_o.values())
    
    if total_p_remaining > 0:
        # More phonetic requirements than orthographic - distribute to existing pairs
        for p_level, count in remaining_p.items():
            if count > 0:
                # Find existing pairs with this phonetic level and add to them
                for combo in pair_counts:
                    if combo[0] == p_level:
                        pair_counts[combo] += count
                        break
    
    # Format output
    result = []
    for pair, count in sorted(pair_counts.items()):
        if count > 0:
            result.append(f"('{pair[0]}', '{pair[1]}')-{count}")
    
    # print("PPPPPPPPPPPPPPPPPPPOOOOOOOOOOOOOOOOOOOOOOOOO\n", result)
    # return result, pair_counts
    return pair_counts


def get_p_o_pairs_from_index():
    """
    Get phonetic-orthographic pairs from index.py goals.
    This function should be called from other modules.
    """
    try:
        # Import from index.py (assuming it's in the same directory)
        import sys
        import os
        
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from index import goal_phonetic, goal_orthographic
        
        # Create optimized pairs
        result, pair_counts = optimize_p_o_pairs(goal_phonetic, goal_orthographic)
        
        return result, pair_counts
        
    except ImportError as e:
        print(f"Could not import from index.py: {e}")
        # Fallback example
        example_phonetic = {'Light': 1, 'Medium': 5, 'Far': 4}
        example_orthographic = {'Light': 1, 'Medium': 3, 'Far': 6}
        return optimize_p_o_pairs(example_phonetic, example_orthographic)


if __name__ == "__main__":
    # Test with example data
    goal_phonetic = {'Light': 1, 'Medium': 5, 'Far': 4}
    goal_orthographic = {'Light': 1, 'Medium': 3, 'Far': 6}
    
    
    print("\n=== Optimized Pairing ===")
    result2, counts2 = optimize_p_o_pairs(goal_phonetic, goal_orthographic)
    for item in result2:
        print(item)
    
    print(f"\nPair counts: {counts2}")
    
    # Verify totals
    total_p = sum(goal_phonetic.values())
    total_o = sum(goal_orthographic.values())
    total_pairs = sum(counts2.values())
    