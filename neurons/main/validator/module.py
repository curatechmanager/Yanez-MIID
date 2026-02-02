import re
import Levenshtein
import jellyfish
import math
import random
from to_latin import to_latin

from typing import List, Dict, Tuple, Any


def clean_transliteration_output(raw_response: str) -> str:
    """
    Extracts the transliterated name from LLM output, removes appended instructions,
    and any leading/trailing punctuation like '-'.
    """
    lines = raw_response.splitlines()
    transliterated = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip instruction/meta lines
        if any(keyword in line.lower() for keyword in [
            "output only", "do not", "end of output", "input", "latin script"
        ]):
            continue
        if re.search(r"[A-Za-zÀ-ÿ]", line):
            transliterated = line
            break

    # Remove known script words (case-insensitive)
    for word in ["latin", "cyrillic", "arabic", "chinese"]:
        transliterated = re.sub(rf"\b{word}\b", "", transliterated, flags=re.IGNORECASE)

    # Remove unwanted characters, keep letters, hyphens, apostrophes, spaces
    transliterated = re.sub(r"[^A-Za-zÀ-ÿ\s\-\']", "", transliterated)

    # Strip leading/trailing punctuation (like '-')
    transliterated = transliterated.strip(" -")

    # Collapse multiple spaces
    transliterated = re.sub(r"\s+", " ", transliterated).strip()
    
    return transliterated

def transliterate_name_with_llm(original_name: str, script: str, model_name: str = "tinyllama:latest", proxy_url=None) -> str:
    """
    Use LLM to transliterate a non-Latin name to Latin script for phonetic comparison.
    Tries tinyllama first, then falls back to llama3.1:latest.
    
    Args:
        original_name: The original non-Latin name to transliterate
        model_name: The Ollama model to use for transliteration (if specified, uses that first)
        proxy_url: Proxy URL for Ollama connection (e.g., "http://proxy:8080")
        
    Returns:
        The transliterated name in Latin script, or fallback transliteration if all models fail
    """
    # ADDED BY KIRO: Configure direct API call with proxy support
    import requests
    import json
    import os
    
    # Clear proxy environment variables for localhost connections
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    old_proxy_values = {}
    
    if not proxy_url:
        # Save and clear proxy settings for localhost
        for var in proxy_vars:
            if var in os.environ:
                old_proxy_values[var] = os.environ[var]
                del os.environ[var]
    llama_models = [
        "tinyllama:latest",
        # "llama3.1:latest",
    ]

    if model_name in llama_models:
        models_to_try = [model_name] + [m for m in llama_models if m != model_name]
    else:
        models_to_try = llama_models

    for current_model in models_to_try:
        attempts = 0
        while attempts < 5:
            try:
                prompt = f"Transliterate this {script} name to Latin script, output only the name:\n{original_name}"

                # MODIFIED BY KIRO: Use direct API call instead of ollama client
                url = "http://localhost:11434/api/generate"
                
                payload = {
                    "model": current_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        'temperature': 0.1,
                        'top_p': 0.9
                    }
                }
                
                # Configure proxy for the request
                request_proxies = {}
                if proxy_url:
                    request_proxies = {'http': proxy_url, 'https': proxy_url}
                else:
                    request_proxies = {'http': None, 'https': None}
                
                response = requests.post(url, json=payload, timeout=30, proxies=request_proxies)
                
                if response.status_code == 200:
                    result = response.json()
                    raw_output = result.get('response', '').strip()
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

                transliterated = clean_transliteration_output(raw_output)

                # Validate transliteration: must contain at least one letter
                if transliterated and re.match(r"^[A-Za-zÀ-ÿ\s\-\']+$", transliterated):
                    # print(f"Successfully transliterated '{original_name}' to '{transliterated}' using {current_model}")
                    return transliterated
                else:
                    print(f"WARNING - Invalid transliteration result for '{original_name}' with {current_model}, attempt {attempts + 1}/5")
                    attempts += 1

            except Exception as e:
                error_msg = str(e)
                # ADDED BY KIRO: Handle timeout specifically
                if "Read timed out" in error_msg or "timeout" in error_msg.lower():
                    print(f"Timeout in LLM transliteration for '{original_name}' with {current_model}, attempt {attempts + 1}/5: {error_msg}")
                else:
                    print(f"Error in LLM transliteration for '{original_name}' with {current_model}, attempt {attempts + 1}/5: {error_msg}")
                attempts += 1

        print(f"WARNING - Model {current_model} failed 5 times for '{original_name}', trying next model")

    print(f"All LLM attempts failed for '{original_name}', using fallback transliteration")
    fallback_result = to_latin(original_name)
    print(f"Fallback transliteration result for '{original_name}': '{fallback_result}'")
    return fallback_result

def has_excessive_letter_repetition(text: str, max_repetition: int = 2) -> bool:
    if not text:
        return False
    pattern = r'(.)\1{' + str(max_repetition) + r',}'
    return bool(re.search(pattern, text, re.IGNORECASE))

def calculate_phonetic_similarity(original_name: str, variation: str) -> float:
    """
    Calculate phonetic similarity between two strings using a randomized subset of phonetic algorithms.
    This makes it harder for miners to game the system by not knowing which algorithms will be used.
    The selection and weighting are deterministic for each original_name.

    We randomize the subset and weights of multiple phonetic algorithms (Soundex, Metaphone, NYSIIS)
    to reduce overfitting to any single encoding. Randomness is deterministically seeded per interpreter
    session using Python's salted hash of `original_name`, which yields:
      • Reproducibility for the same name within a single run (same selection/weights each time)
      • Variation across different runs (fresh selections/weights after interpreter restart)

    This per-run determinism and cross-run variability are intentional to balance auditability and
    anti-gaming. If strict cross-run reproducibility becomes a requirement, we can switch to a stable
    digest (e.g., SHA-256) and/or a local RNG seeded from that digest.

    """
    # Define available phonetic algorithms
    algorithms = {
        "soundex": lambda x, y: jellyfish.soundex(x) == jellyfish.soundex(y),
        "metaphone": lambda x, y: jellyfish.metaphone(x) == jellyfish.metaphone(y),
        "nysiis": lambda x, y: jellyfish.nysiis(x) == jellyfish.nysiis(y),
        # Add more algorithms if needed
    }

    # Deterministically seed the random selection based on the original name
    random.seed(hash(original_name) % 10000)
    selected_algorithms = random.sample(list(algorithms.keys()), k=min(3, len(algorithms)))

    # Generate random weights that sum to 1.0
    weights = [random.random() for _ in selected_algorithms]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Calculate the weighted phonetic score
    phonetic_score = sum(
        algorithms[algo](original_name, variation) * weight
        for algo, weight in zip(selected_algorithms, normalized_weights)
    )
    return float(phonetic_score)

def calculate_orthographic_similarity(original_name: str, variation: str) -> float:
    """
    Calculate orthographic similarity between two strings using Levenshtein distance.
    
    Args:
        original_name: The original name
        variation: The variation to compare against
        
    Returns:
        Orthographic similarity score between 0 and 1
    """
    try:
        # Use Levenshtein distance to compare
        distance = Levenshtein.distance(original_name, variation)
        max_len = max(len(original_name), len(variation))
        
        # Calculate orthographic similarity score (0-1)
        return 1.0 - (distance / max_len)
    except Exception as e:
        print(f"Error calculating orthographic score: {str(e)}")
        return 0.0

def calculate_part_score(
    original_part: str,
    variations: List[str],
    phonetic_similarity: Dict[str, float],
    orthographic_similarity: Dict[str, float],
    expected_count: int
) -> Tuple[float, Dict]:
    
    # Define the boundaries for each similarity level with no overlaps
    # There is a gap so no code can be in 2 different bounds
    phonetic_boundaries = {
        "Light": (0.80, 1.00),   # High similarity range
        "Medium": (0.60, 0.79),  # Moderate similarity range
        "Far": (0.30, 0.59)      # Low similarity range
    }
    
    orthographic_boundaries = {
        "Light": (0.70, 1.00),   # High similarity range
        "Medium": (0.50, 0.69),  # Moderate similarity range
        "Far": (0.20, 0.49)      # Low similarity range
    }
    
    # 1. Check if count matches expected count with adaptive tolerance
    # Handle case where expected_count is 0 (100% rule-based scenario)
    if expected_count == 0:
        # If no variations are expected for non-rule-compliant part, give full score
        count_score = 1.0
    else:
        # Tolerance increases with expected count to be more forgiving for larger sets
        base_tolerance = 0.2  # 20% base tolerance
        tolerance = base_tolerance + (0.05 * (expected_count // 10))  # Add 5% per 10 expected variations
        tolerance = min(tolerance, 0.4)  # Cap at 40% maximum tolerance
        
        tolerance_range = expected_count * tolerance
        actual_count = len(variations)
        lower_bound = max(1, expected_count - tolerance_range)  # Ensure at least 1 variation required
        upper_bound = expected_count + tolerance_range
        # print(lower_bound, actual_count, upper_bound, expected_count)
        if lower_bound <= actual_count <= upper_bound:
            count_score = 1.0
        else:
            if actual_count < lower_bound:
                deviation = lower_bound - actual_count
            else:
                deviation = actual_count - upper_bound
            
            # Smoother penalty curve using exponential decay
            count_score = math.exp(-deviation / expected_count)
    
    # 2. Enhanced uniqueness check with similarity clustering and excessive repetition filtering
    unique_variations = []
    filtered_count = 0
    for var in variations:
        # Filter out variations with excessive letter repetition (more than 2 consecutive identical letters)
        if has_excessive_letter_repetition(var, max_repetition=2):
            filtered_count += 1
            continue
        
        # Check if this variation is too similar to any existing unique variation
        is_unique = True
        for unique_var in unique_variations:
            combined_similarity = (
                calculate_phonetic_similarity(var, unique_var) * 0.7 +
                calculate_orthographic_similarity(var, unique_var) * 0.3
            )
            if combined_similarity > 0.99:  # Very high similarity threshold
                is_unique = False
                break
        if is_unique:
            unique_variations.append(var)
    
    # Calculate penalty for filtered variations (excessive repetition)
    filter_penalty = 0.0
    if filtered_count > 0:
        filter_penalty = min(0.2, filtered_count * 0.05)  # Up to 20% penalty
    
    uniqueness_score = len(unique_variations) / len(variations) if variations else 0
    
    # 3. Improved length reasonableness with adaptive thresholds
    length_scores = []
    for var in unique_variations:
        original_len = len(original_part)
        var_len = len(var)
        
        # Adaptive threshold based on original name length
        min_ratio = 0.6 if original_len <= 5 else 0.7  # More forgiving for short names
        
        # Consider both absolute and relative length differences
        length_ratio = min(var_len / original_len, original_len / var_len)
        absolute_diff = abs(var_len - original_len)
        
        # Combine both metrics with smooth transition
        length_score = length_ratio * (1.0 - min(1.0, absolute_diff / original_len))
        length_scores.append(length_score)
        
    
    length_score = sum(length_scores) / len(length_scores) if length_scores else 0
    
    # Calculate similarity scores with improved distribution analysis
    phonetic_scores = []
    orthographic_scores = []
    
    for variation in unique_variations:
        p_score = calculate_phonetic_similarity(original_part, variation)
        o_score = calculate_orthographic_similarity(original_part, variation)
        
        phonetic_scores.append(p_score)
        orthographic_scores.append(o_score)
    
    # Sort scores for distribution analysis
    phonetic_scores.sort()
    orthographic_scores.sort()
    
    def calculate_distribution_quality(scores, boundaries, targets):
        quality = 0.0
        total_matched = 0
        
        for level, (lower, upper) in boundaries.items():
            target_percentage = targets.get(level, 0.0)
            if target_percentage == 0.0:
                continue
                
            # Count scores in this range
            count = sum(1 for score in scores if lower <= score <= upper)
            target_count = int(target_percentage * len(scores))
            
            if target_count > 0:
                # Calculate match quality with diminishing returns
                match_ratio = count / target_count
                if match_ratio <= 1.0:
                    match_quality = match_ratio  # Linear up to target
                else:    
                    match_quality = 1.0 - math.exp(-(match_ratio - 1.0))  
                quality += target_percentage * match_quality
                total_matched += count
                
        # Penalize unmatched variations
        unmatched = len(scores) - total_matched
        if unmatched > 0:
            penalty = 0.1 * (unmatched / len(scores))
            quality = max(0.0, quality - penalty)
        
        return quality
    
    phonetic_quality = calculate_distribution_quality(
        phonetic_scores, phonetic_boundaries, phonetic_similarity
    )
    orthographic_quality = calculate_distribution_quality(
        orthographic_scores, orthographic_boundaries, orthographic_similarity
    )
    
    similarity_score = (phonetic_quality + orthographic_quality) / 2  # Average of both similarities
    
    min_similarity_threshold = 0.2
    if similarity_score < min_similarity_threshold:
        similarity_score *= 0.1  # Keep only 10% of the similarity score
    
    similarity_weight = 0.6
    count_weight = 0.15
    uniqueness_weight = 0.1
    length_weight = 0.15
    
    final_score = (
        similarity_weight * similarity_score +
        count_weight * count_score +
        uniqueness_weight * uniqueness_score +
        length_weight * length_score
    )
    
    # Apply penalty for filtered variations with excessive letter repetition
    if filter_penalty > 0:
        final_score = max(0.0, final_score * (1.0 - filter_penalty))
    
    # Return score with detailed metrics
    metrics = {
        'similarity_score': similarity_score,
        'phonetic_quality': phonetic_quality,
        'orthographic_quality': orthographic_quality,
        'count_score': count_score,
        'uniqueness_score': uniqueness_score,
        'length_score': length_score,
        'filter_penalty': filter_penalty,
        'final_score': final_score
    }
    
    return final_score, metrics

def calculate_part_score_phonetic_only(
    original_part: str,
    variations: List[str],
    phonetic_similarity: Dict[str, float],
    expected_count: int
) -> Tuple[float, Dict]:
    """Calculate score and detailed metrics for a single part (first or last name) using only phonetic similarity"""
    
    if not variations:
        return 0.0, {}
    
    # Define the boundaries for phonetic similarity levels with no overlaps
    # There is a gap so no code can be in 2 different bounds
    phonetic_boundaries = {
        "Light": (0.80, 1.00),   # High similarity range
        "Medium": (0.60, 0.79),  # Moderate similarity range
        "Far": (0.30, 0.59)      # Low similarity range
    }
    
    # 1. Check if count matches expected count with adaptive tolerance
    # Handle case where expected_count is 0 (100% rule-based scenario)
    if expected_count == 0:
        # If no variations are expected for non-rule-compliant part, give full score
        count_score = 1.0
    else:
        # Tolerance increases with expected count to be more forgiving for larger sets
        base_tolerance = 0.2  # 20% base tolerance
        tolerance = base_tolerance + (0.05 * (expected_count // 10))  # Add 5% per 10 expected variations
        tolerance = min(tolerance, 0.4)  # Cap at 40% maximum tolerance
        
        tolerance_range = expected_count * tolerance
        actual_count = len(variations)
        lower_bound = max(1, expected_count - tolerance_range)  # Ensure at least 1 variation required
        upper_bound = expected_count + tolerance_range
        
        if lower_bound <= actual_count <= upper_bound:
            count_score = 1.0
        else:
            if actual_count < lower_bound:
                deviation = lower_bound - actual_count
            else:
                deviation = actual_count - upper_bound
            
            # Smoother penalty curve using exponential decay
            count_score = math.exp(-deviation / expected_count)
    
    # 2. Enhanced uniqueness check with phonetic similarity clustering and excessive repetition filtering
    unique_variations = []
    filtered_count = 0
    for var in variations:
        # Filter out variations with excessive letter repetition (more than 2 consecutive identical letters)
        if has_excessive_letter_repetition(var, max_repetition=2):
            filtered_count += 1
            continue
        
        # Check if this variation is too similar to any existing unique variation
        is_unique = True
        for unique_var in unique_variations:
            phonetic_sim = calculate_phonetic_similarity(var, unique_var)
            if phonetic_sim > 0.99:  # Very high similarity threshold
                is_unique = False
                break
        if is_unique:
            unique_variations.append(var)
    
    # Calculate penalty for filtered variations (excessive repetition)
    filter_penalty = 0.0
    if filtered_count > 0:
        filter_penalty = min(0.2, filtered_count * 0.05)  # Up to 20% penalty
    
    uniqueness_score = len(unique_variations) / len(variations) if variations else 0
    
    # 3. Improved length reasonableness with adaptive thresholds
    length_scores = []
    for var in unique_variations:
        original_len = len(original_part)
        var_len = len(var)
        
        # Adaptive threshold based on original name length
        min_ratio = 0.6 if original_len <= 5 else 0.7  # More forgiving for short names
        
        # Consider both absolute and relative length differences
        length_ratio = min(var_len / original_len, original_len / var_len)
        absolute_diff = abs(var_len - original_len)
        
        # Combine both metrics with smooth transition
        length_score = length_ratio * (1.0 - min(1.0, absolute_diff / original_len))
        length_scores.append(length_score)
        
    
    length_score = sum(length_scores) / len(length_scores) if length_scores else 0
    
    # Calculate phonetic similarity scores with improved distribution analysis
    phonetic_scores = []
    
    for variation in unique_variations:
        p_score = calculate_phonetic_similarity(original_part, variation)
        phonetic_scores.append(p_score)
        
    # Sort scores for distribution analysis
    phonetic_scores.sort()
    
    # Calculate quality scores with improved distribution matching
    def calculate_distribution_quality(scores, boundaries, targets):
        quality = 0.0
        total_matched = 0
        
        for level, (lower, upper) in boundaries.items():
            target_percentage = targets.get(level, 0.0)
            if target_percentage == 0.0:
                continue
                
            # Count scores in this range
            count = sum(1 for score in scores if lower <= score <= upper)
            target_count = int(target_percentage * len(scores))
            
            if target_count > 0:
                # Calculate match quality with diminishing returns
                match_ratio = count / target_count
                #match_quality = 1.0 - math.exp(-match_ratio)  # Smooth curve
                # Diminishing returns after target
                # this gives 100% at target, then diminishing returns for exceeding
                if match_ratio <= 1.0:
                    match_quality = match_ratio  # Linear up to target
                else:    
                    match_quality = 1.0 - math.exp(-(match_ratio - 1.0))  
                quality += target_percentage * match_quality
                total_matched += count
                
        # Penalize unmatched variations
        unmatched = len(scores) - total_matched
        if unmatched > 0:
            penalty = 0.1 * (unmatched / len(scores))
            quality = max(0.0, quality - penalty)
        
        return quality
    
    phonetic_quality = calculate_distribution_quality(
        phonetic_scores, phonetic_boundaries, phonetic_similarity
    )
    
    # Use only phonetic similarity score
    similarity_score = phonetic_quality
    
    # Apply minimum similarity threshold to prevent gaming
    # If similarity is very low, severely reduce the score
    min_similarity_threshold = 0.2
    if similarity_score < min_similarity_threshold:
        similarity_score *= 0.1  # Keep only 10% of the similarity score

    similarity_weight = 0.6
    count_weight = 0.15
    uniqueness_weight = 0.1
    length_weight = 0.15
    
    final_score = (
        similarity_weight * similarity_score +
        count_weight * count_score +
        uniqueness_weight * uniqueness_score +
        length_weight * length_score
    )
    
    # Apply penalty for filtered variations with excessive letter repetition
    if filter_penalty > 0:
        final_score = max(0.0, final_score * (1.0 - filter_penalty))
    
    # Return score with detailed metrics
    metrics = {
        'similarity_score': similarity_score,
        'phonetic_quality': phonetic_quality,
        'count_score': count_score,
        'uniqueness_score': uniqueness_score,
        'length_score': length_score,
        'filter_penalty': filter_penalty,
        'final_score': final_score
    }
    
    return final_score, metrics

def get_name_part_weights(name: str) -> dict:
    """Generate weights for different name parts based on name characteristics, with randomness."""
    random.seed(hash(name) % 10000)
    name_parts = name.split()
    if len(name_parts) < 2:
        return {"first_name_weight": 1.0, "last_name_weight": 0.0}
    lengths = [len(part) for part in name_parts]
    total_length = sum(lengths)
    weights = []
    for length in lengths:
        base_weight = length / total_length
        randomized_weight = base_weight * random.uniform(0.8, 1.2)  # 20% randomness
        weights.append(randomized_weight)
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    return {
        "first_name_weight": normalized_weights[0],
        "last_name_weight": normalized_weights[1]
    }

def calculate_variation_quality(
    original_name: str,  # Full name as a string
    variations: List[str],
    phonetic_similarity: Dict[str, float] = None,
    orthographic_similarity: Dict[str, float] = None,
    expected_count: int = 10,
    rule_based: Dict[str, Any] = None,  # New parameter for rule-based metadata
    verbose: bool = True  # Print detailed scores
) -> float:
    """
    Calculate the quality of execution vectors (name variations) for threat detection.
    Returns the final quality score.
    """
    # Default similarity preferences if none provided
    if phonetic_similarity is None:
        phonetic_similarity = {"Medium": 1.0}
    if orthographic_similarity is None:
        orthographic_similarity = {"Medium": 1.0}

    # First, calculate rule compliance to identify rule-based variations
    rule_compliance_score = 0.0
    rule_compliant_variations = set()
    target_percentage = 0.0
    effective_target_rules = []

    if rule_based and "selected_rules" in rule_based:
        target_rules = rule_based.get("selected_rules", [])
        # The pre-filtering logic has been moved to evaluate_rule_compliance
        effective_target_rules = target_rules

        if effective_target_rules:
            target_percentage = rule_based.get("rule_percentage", 30) / 100.0  # Convert to fraction
            rule_compliance_score, rule_compliance_metrics = calculate_rule_compliance_score(
                original_name,
                variations,
                effective_target_rules,
                target_percentage
            )
            # print("___________________")
            # print(f"{rule_compliance_score}, {len(rule_compliance_metrics)}")
            # print("___________________")
            if "rules_satisfied_by_variation" in rule_compliance_metrics:
                rule_compliant_variations = set(rule_compliance_metrics["rules_satisfied_by_variation"].keys())
    # Separate variations into rule-compliant and non-rule-compliant
    non_rule_compliant_variations = [
        var for var in variations if var not in rule_compliant_variations
    ]
    
    # Split the original name into first and last name
    name_parts = original_name.split()
    part_weights = get_name_part_weights(original_name)
    if len(name_parts) < 2:
        first_name = original_name
        last_name = None
    else:
        first_name = name_parts[0]
        last_name = name_parts[-1]
    
    # Process NON-RULE-COMPLIANT variations for base quality score
    first_name_variations = []
    last_name_variations = []
    
    for variation in non_rule_compliant_variations:
        parts = variation.split()
        if len(parts) >= 2:
            first_name_variations.append(parts[0])
            last_name_variations.append(parts[-1])
        elif len(parts) == 1:
            # If variation is a single word and we expect two names,
            # this should be considered a lower quality variation
            if last_name:
                # Only use it for first name with a penalty
                first_name_variations.append(parts[0])
            else:
                # If original is also single word, use normally
                first_name_variations.append(parts[0])
        else:
            print(f"Empty variation found for '{original_name}'")

    # Adjust expected count for non-rule-compliant part
    expected_base_count = expected_count * (1.0 - target_percentage)
    first_name_score, first_metrics = calculate_part_score(
        first_name,
        first_name_variations,
        phonetic_similarity,
        orthographic_similarity,
        expected_base_count
    )
    # Calculate score for last name if available
    last_name_score = 0.0
    last_metrics = {}
    if last_name:
        last_name_score, last_metrics = calculate_part_score(
            last_name,
            last_name_variations,
            phonetic_similarity,
            orthographic_similarity,
            expected_base_count
        )
        
        # Apply penalty for missing last names in non-rule-compliant variations
        if len(last_name_variations) < len(non_rule_compliant_variations):
            missing_ratio = (len(non_rule_compliant_variations) - len(last_name_variations)) / len(non_rule_compliant_variations) if len(non_rule_compliant_variations) > 0 else 0
            last_name_score *= (1.0 - missing_ratio)

    # Combine first/last name scores for the base_score
    if last_name:
        base_score = (
            part_weights.get("first_name_weight", 0.3) * first_name_score +
            part_weights.get("last_name_weight", 0.7) * last_name_score
        )
    else:
        # If no last name, use only first name score
        base_score = first_name_score
        
    # If no non-rule variations were expected, the base_score is not penalized.
    # This is separated from the case where they were expected but not provided.
    if expected_base_count == 0:
        base_score = 1.0 # Or some other neutral value, 1.0 seems fair to not penalize.
    
    # Apply rule compliance to final score using weights from the global config
    rule_compliance_weight = 0.2
    
    # If rules were requested but none were applicable to this name, adjust weights
    # to base the score entirely on similarity.
    if rule_based and "selected_rules" in rule_based and not effective_target_rules:
        base_weight = 1.0
        rule_compliance_weight = 0.0
    else:
        base_weight = 1.0 - rule_compliance_weight

    # The base_score already contains the other weighted components (length, count, uniqueness)
    # So we need to scale it down to make room for the rule compliance component
    final_score = (base_weight * base_score) + (rule_compliance_weight * rule_compliance_score)

    # Print detailed scores
    if verbose:
        # Calculate average metrics across first and last name
        avg_similarity = first_metrics.get('similarity_score', 0)
        avg_phonetic = first_metrics.get('phonetic_quality', 0)
        avg_orthographic = first_metrics.get('orthographic_quality', 0)
        avg_count = first_metrics.get('count_score', 0)
        avg_uniqueness = first_metrics.get('uniqueness_score', 0)
        avg_length = first_metrics.get('length_score', 0)
        
        if last_name and last_metrics:
            avg_similarity = (first_metrics.get('similarity_score', 0) + last_metrics.get('similarity_score', 0)) / 2
            avg_phonetic = (first_metrics.get('phonetic_quality', 0) + last_metrics.get('phonetic_quality', 0)) / 2
            avg_orthographic = (first_metrics.get('orthographic_quality', 0) + last_metrics.get('orthographic_quality', 0)) / 2
            avg_count = (first_metrics.get('count_score', 0) + last_metrics.get('count_score', 0)) / 2
            avg_uniqueness = (first_metrics.get('uniqueness_score', 0) + last_metrics.get('uniqueness_score', 0)) / 2
            avg_length = (first_metrics.get('length_score', 0) + last_metrics.get('length_score', 0)) / 2
        
        print(f"\n{'='*50}")
        print(f"LATIN: '{original_name}'")
        print(f"{'='*50}")
        print(f"Similarity:  {avg_similarity:.4f} (60%)")
        print(f"  Phonetic:     {avg_phonetic:.4f}")
        print(f"  Orthographic: {avg_orthographic:.4f}")
        print(f"Count:       {avg_count:.4f} (15%)")
        print(f"Uniqueness:  {avg_uniqueness:.4f} (10%)")
        print(f"Length:      {avg_length:.4f} (15%)")
        print(f"{'─'*50}")
        print(f"Base Score:  {base_score:.4f} (80%)")
        print(f"Rule Score:  {rule_compliance_score:.4f} (20%)")
        print(f"{'─'*50}")
        print(f"FINAL:       {final_score:.4f}")
        print(f"{'='*50}")

    return final_score

def calculate_variation_quality_phonetic_only(
    original_name1: str,  # Full name as a string
    variations: List[str],
    phonetic_similarity: Dict[str, float] = None,
    expected_count: int = 10,
    verbose: bool = True  # Print detailed scores
) -> float:
    """
    Calculate the quality of execution vectors (name variations) using ONLY phonetic similarity.
    No rule-based scoring, no orthographic similarity - just phonetic similarity for both first and last names.
    Returns the final quality score.
    """

    original_name = to_latin(original_name1)
    # Default phonetic similarity preferences if none provided
    if phonetic_similarity is None:
        phonetic_similarity = {"Medium": 1.0}

    # Split the original name into first and last name
    name_parts = original_name.split()
    part_weights = get_name_part_weights(original_name)
    if len(name_parts) < 2:
        first_name = original_name
        last_name = None
    else:
        first_name = name_parts[0]
        last_name = name_parts[-1]
    
    # Process ALL variations for phonetic-only scoring
    # IMPORTANT: Transliterate variations to Latin script for phonetic comparison
    first_name_variations = []
    last_name_variations = []
    
    for variation in variations:
        parts = variation.split()
        if len(parts) >= 2:
            first_name_variations.append(parts[0])
            last_name_variations.append(parts[-1])
        elif len(parts) == 1:
            # If variation is a single word and we expect two names,
            # this should be considered a lower quality variation
            if last_name:
                # Only use it for first name with a penalty
                first_name_variations.append(parts[0])
            else:
                # If original is also single word, use normally
                first_name_variations.append(parts[0])
        else:
            print(f"Empty variation found for '{original_name}'")

    # Calculate phonetic-only score for first name
    first_name_score, first_metrics = calculate_part_score_phonetic_only(
        first_name,
        first_name_variations,
        phonetic_similarity,
        expected_count
    )
    
    # Calculate phonetic-only score for last name if available
    last_name_score = 0.0
    last_metrics = {}
    if last_name:
        last_name_score, last_metrics = calculate_part_score_phonetic_only(
            last_name,
            last_name_variations,
            phonetic_similarity,
            expected_count
        )
        
        # Apply penalty for missing last names in variations
        if len(last_name_variations) < len(variations):
            missing_ratio = (len(variations) - len(last_name_variations)) / len(variations) if len(variations) > 0 else 0
            last_name_score *= (1.0 - missing_ratio)

    # Combine first/last name scores for the final score
    if last_name:
        final_score = (
            part_weights.get("first_name_weight", 0.3) * first_name_score +
            part_weights.get("last_name_weight", 0.7) * last_name_score
        )
    else:
        # If no last name, use only first name score
        final_score = first_name_score

    # Print detailed scores
    if verbose:
        # Calculate average metrics across first and last name
        avg_similarity = first_metrics.get('similarity_score', 0)
        avg_phonetic = first_metrics.get('phonetic_quality', 0)
        avg_count = first_metrics.get('count_score', 0)
        avg_uniqueness = first_metrics.get('uniqueness_score', 0)
        avg_length = first_metrics.get('length_score', 0)
        
        if last_name and last_metrics:
            avg_similarity = (first_metrics.get('similarity_score', 0) + last_metrics.get('similarity_score', 0)) / 2
            avg_phonetic = (first_metrics.get('phonetic_quality', 0) + last_metrics.get('phonetic_quality', 0)) / 2
            avg_count = (first_metrics.get('count_score', 0) + last_metrics.get('count_score', 0)) / 2
            avg_uniqueness = (first_metrics.get('uniqueness_score', 0) + last_metrics.get('uniqueness_score', 0)) / 2
            avg_length = (first_metrics.get('length_score', 0) + last_metrics.get('length_score', 0)) / 2
        print(f"\n{'='*50}")
        print(f"NON-LATIN: '{original_name1}' → '{original_name}'")
        print(f"{'='*50}")
        print(f"Similarity:  {avg_similarity:.4f} (60%)")
        print(f"  Phonetic:  {avg_phonetic:.4f}")
        print(f"Count:       {avg_count:.4f} (15%)")
        print(f"Uniqueness:  {avg_uniqueness:.4f} (10%)")
        print(f"Length:      {avg_length:.4f} (15%)")
        print(f"{'─'*50}")
        print(f"FINAL:       {final_score:.4f}")
        print(f"{'='*50}")

    return final_score

def calculate_rule_compliance_score(
    original_name: str,
    variations: List[str],
    target_rules: List[str],
    target_percentage: float = 0.3
) -> Tuple[float, Dict]:
    """
    Calculate how well the variations comply with the target rules.
    
    Args:
        original_name: The original name
        variations: List of name variations
        target_rules: List of rules that should be followed
        target_percentage: Percentage of variations that should comply with rules
        
    Returns:
        Tuple containing:
        - Compliance score (0-1)
        - Dictionary with detailed metrics
    """
    if not variations or not target_rules:
        return 0.0, {
            "compliant_variations_by_rule": {},
            "rules_satisfied_by_variation": {},
            "compliance_ratio_overall_variations": 0.0,
            "overall_compliant_unique_variations_count": 0,
            "expected_compliant_variations_count": 0,
            "quantity_score": 0.0,
            "rule_diversity_factor": 0.0,
            "num_target_rules_met": 0,
            "total_target_rules": len(target_rules) if target_rules else 0,
            "score": 0.0
        }
    
    # Evaluate rule compliance
    # compliant_variations_by_rule is Dict[str (rule_name), List[str (variation)]]
    from rule_evaluator import evaluate_rule_compliance
    compliant_variations_by_rule, compliance_ratio_from_evaluator = evaluate_rule_compliance(
        original_name, 
        variations, 
        target_rules
    )
    
    # Check if no rules were possible for this name structure
    # If target_rules were provided but evaluate_rule_compliance returned empty results,
    # it means no rules were applicable to this name structure
    if target_rules and not compliant_variations_by_rule:
        print(f"⚠️ No rules were applicable for '{original_name}' with target rules: {target_rules}")
        return 1.0, {
            "compliant_variations_by_rule": {},
            "rules_satisfied_by_variation": {},
            "compliance_ratio_overall_variations": 0.0,
            "overall_compliant_unique_variations_count": 0,
            "expected_compliant_variations_count": 0,
            "quantity_score": 1.0,
            "rule_diversity_factor": 1.0,
            "num_target_rules_met": 0,
            "total_target_rules": len(target_rules),
            "score": 1.0
        }
    
    # Create a dictionary to map each compliant variation to the list of rules it satisfied
    rules_satisfied_by_variation = {}
    for rule, rule_compliant_variations_list in compliant_variations_by_rule.items():
        for variation in rule_compliant_variations_list:
            if variation not in rules_satisfied_by_variation:
                rules_satisfied_by_variation[variation] = []
            # Ensure no duplicate rules (though unlikely with current evaluators)
            if rule not in rules_satisfied_by_variation[variation]:
                 rules_satisfied_by_variation[variation].append(rule)

    # Count unique variations that satisfied at least one rule (from the target_rules)
    overall_compliant_count = len(rules_satisfied_by_variation)
    expected_compliant_count = max(1, int(len(variations) * target_percentage))
    
    
    # for rule, variations_list in compliant_variations_by_rule.items():
    #     # This logging shows all rules returned by evaluate_rule_compliance, which should be the target_rules
    
    # Calculate the quantity-based compliance score
    ratio_of_actual_to_expected = overall_compliant_count / expected_compliant_count if expected_compliant_count > 0 else 0.0
    
    quantity_score = 0.0
    if ratio_of_actual_to_expected <= 0.0:
        quantity_score = 0.0
    elif ratio_of_actual_to_expected <= 1.0:  # At or below target
        quantity_score = ratio_of_actual_to_expected
    else:  # Above target - apply a gentler penalty
        quantity_score = max(0.5, 1.5 - 0.5 * ratio_of_actual_to_expected)
    

    # Calculate rule diversity factor
    num_target_rules_met = 0
    rule_diversity_factor = 0.0

    if not target_rules: # No specific rules targeted, so diversity is maximal or not applicable.
        rule_diversity_factor = 1.0
    elif overall_compliant_count == 0: # No variations complied with any target rule.
        # This case should have been handled earlier, but just in case
        rule_diversity_factor = 0.0
        num_target_rules_met = 0
    else:
        # Count how many of the *effective_rules* were satisfied by at least one variation.
        # compliant_variations_by_rule.keys() contains only the rules that were actually evaluated
        # (after filtering out impossible rules in evaluate_rule_compliance)
        satisfied_effective_rules = set()
        for rule_name, compliant_vars_for_rule_list in compliant_variations_by_rule.items():
            if compliant_vars_for_rule_list:  # Rule was satisfied by at least one variation
                satisfied_effective_rules.add(rule_name)
        num_target_rules_met = len(satisfied_effective_rules)
        
        # Calculate diversity based on effective rules (rules that were actually possible to apply)
        effective_rules_count = len(compliant_variations_by_rule)
        if effective_rules_count > 0:
            rule_diversity_factor = num_target_rules_met / effective_rules_count
        else:
            # No effective rules means no rules were possible for this name structure
            rule_diversity_factor = 1.0


    # Final score combines quantity and diversity
    final_score = quantity_score * rule_diversity_factor
    
    return final_score, {
        "compliant_variations_by_rule": compliant_variations_by_rule,
        "rules_satisfied_by_variation": rules_satisfied_by_variation,
        "compliance_ratio_overall_variations": compliance_ratio_from_evaluator, # Ratio of variations that matched any rule to total variations
        "overall_compliant_unique_variations_count": overall_compliant_count,
        "expected_compliant_variations_count": expected_compliant_count,
        "quantity_score": float(quantity_score),
        "rule_diversity_factor": float(rule_diversity_factor),
        "num_target_rules_met": num_target_rules_met,
        "total_target_rules": len(target_rules),
        "score": float(final_score) # This is the score based on meeting the target rule_percentage and diversity
    }

def parse_query_template(query_template: str) -> Dict:
    """Extract requirements from query template"""
    requirements = {
        'variation_count': 15,
        'rule_percentage': 0,
        'rules': [],
        'rule_sentence': None,  # Full sentence about rule-based transformations
        'phonetic_similarity': {},
        'orthographic_similarity': {},
        'uav_seed_name': None  # Phase 3: UAV seed name
    }
    
    # Extract variation count
    count_match = re.search(r'Generate\s+(\d+)\s+variations', query_template, re.I)
    if count_match:
        requirements['variation_count'] = int(count_match.group(1))
    
    # Extract rule percentage - look for patterns like "X% of", "approximately X%", "include X%"
    rule_pct_patterns = [
        r'approximately\s+(\d+)%\s+of',  # "Approximately 24% of"
        r'also\s+include\s+(\d+)%\s+of', # "also include 44% of"
        r'(\d+)%\s+of\s+the\s+total',     # "24% of the total"
        r'(\d+)%\s+of\s+variations',      # "24% of variations"
        r'include\s+(\d+)%',              # "include 24%"
        r'(\d+)%\s+should\s+follow'       # "24% should follow"
    ]
    for pattern in rule_pct_patterns:
        rule_pct_match = re.search(pattern, query_template, re.I)
        if rule_pct_match:
            pct = rule_pct_match.group(1)
            requirements['rule_percentage'] = int(pct) / 100
            break
    
    # Extract rules - check various phrasings
    # Character replacement
    if 'replace spaces with special characters' in query_template.lower() or 'replace spaces with random special characters' in query_template.lower():
        requirements['rules'].append('replace_spaces_with_special_characters')
    if 'replace double letters' in query_template.lower() or 'replace double letters with single letter' in query_template.lower():
        requirements['rules'].append('replace_double_letters')
    if 'replace random vowels' in query_template.lower() or 'replace vowels with different vowels' in query_template.lower():
        requirements['rules'].append('replace_random_vowels')
    if 'replace random consonants' in query_template.lower() or 'replace consonants with different consonants' in query_template.lower():
        requirements['rules'].append('replace_random_consonants')
    
    # Character swapping
    if 'swap adjacent consonants' in query_template.lower():
        requirements['rules'].append('swap_adjacent_consonants')
    if 'swap adjacent syllables' in query_template.lower():
        requirements['rules'].append('swap_adjacent_syllables')
    if 'swap random letter' in query_template.lower() or 'swap random adjacent letters' in query_template.lower():
        requirements['rules'].append('swap_random_letter')
    
    # Character removal
    if 'delete a random letter' in query_template.lower() or 'delete random letter' in query_template.lower():
        requirements['rules'].append('delete_random_letter')
    if 'remove random vowel' in query_template.lower() or 'remove a random vowel' in query_template.lower():
        requirements['rules'].append('remove_random_vowel')
    if 'remove random consonant' in query_template.lower() or 'remove a random consonant' in query_template.lower():
        requirements['rules'].append('remove_random_consonant')
    if 'remove all spaces' in query_template.lower() or 'remove spaces' in query_template.lower():
        requirements['rules'].append('remove_all_spaces')
    
    # Character insertion
    if 'duplicate a random letter' in query_template.lower() or 'duplicate random letter' in query_template.lower():
        requirements['rules'].append('duplicate_random_letter')
    if 'insert random letter' in query_template.lower() or 'insert a random letter' in query_template.lower():
        requirements['rules'].append('insert_random_letter')
    if 'add a title prefix' in query_template.lower() or 'title prefix' in query_template.lower() or 'add title prefix' in query_template.lower():
        requirements['rules'].append('add_title_prefix')
    if 'add a title suffix' in query_template.lower() or 'title suffix' in query_template.lower() or 'add title suffix' in query_template.lower():
        requirements['rules'].append('add_title_suffix')
    
    # Name formatting
    if 'use first name initial' in query_template.lower() or 'first name initial with last name' in query_template.lower():
        requirements['rules'].append('initial_only_first_name')
    if 'convert name to initials' in query_template.lower() or 'shorten name to initials' in query_template.lower():
        requirements['rules'].append('shorten_to_initials')
    if 'abbreviate name parts' in query_template.lower() or 'abbreviate' in query_template.lower() or 'shorten name to abbreviations' in query_template.lower():
        requirements['rules'].append('abbreviate_name_parts')
    
    # Structure change
    if 'reorder name parts' in query_template.lower() or 'reorder parts' in query_template.lower() or 'name parts permutations' in query_template.lower():
        requirements['rules'].append('reorder_name_parts')
    
    # Extract rule sentence (full sentence about rule-based transformations)
    rule_sentence_match = re.search(r'(Approximately\s+\d+%.*?rule-based transformations:[^.]+\.)', query_template, re.I)
    if rule_sentence_match:
        requirements['rule_sentence'] = rule_sentence_match.group(1)
    
    # Extract phonetic similarity distribution (Light/Medium/Far percentages)
    # Pattern 1: "20% Light, 60% Medium, and 20% Far variations"
    # Pattern 2: "30% of the variations using Light similarity, 40% using Medium similarity, and 30% using Far similarity"
    
    # First try VALIDATION HINTS section (more reliable format)
    phonetic_match = re.search(r'\[VALIDATION HINTS\].*?Phonetic similarity:\s*([^.;]+)', query_template, re.I | re.DOTALL)
    if phonetic_match:
        hints_text = phonetic_match.group(1)
        hints_match = re.search(r'(\d+)%\s+Light.*?(\d+)%\s+Medium.*?(\d+)%\s+Far', hints_text, re.I)
        if hints_match:
            requirements['phonetic_similarity'] = {
                'Light': int(hints_match.group(1)) / 100.0,
                'Medium': int(hints_match.group(2)) / 100.0,
                'Far': int(hints_match.group(3)) / 100.0
            }
    
    # If not found in VALIDATION HINTS, try main text patterns
    if not requirements['phonetic_similarity']:
        # Pattern 1: "phonetic similarity is reflected in 20% Light, 60% Medium, and 20% Far"
        phonetic_match = re.search(r'phonetic similarity.*?(\d+)%\s+Light.*?(\d+)%\s+Medium.*?(\d+)%\s+Far', query_template, re.I | re.DOTALL)
        if phonetic_match:
            requirements['phonetic_similarity'] = {
                'Light': int(phonetic_match.group(1)) / 100.0,
                'Medium': int(phonetic_match.group(2)) / 100.0,
                'Far': int(phonetic_match.group(3)) / 100.0
            }
        else:
            # Pattern 2: "30% of the variations using Light similarity, 40% using Medium similarity, and 30% using Far similarity"
            phonetic_match = re.search(r'phonetic similarity.*?(\d+)%.*?Light.*?(\d+)%.*?Medium.*?(\d+)%.*?Far', query_template, re.I | re.DOTALL)
            if phonetic_match:
                requirements['phonetic_similarity'] = {
                    'Light': int(phonetic_match.group(1)) / 100.0,
                    'Medium': int(phonetic_match.group(2)) / 100.0,
                    'Far': int(phonetic_match.group(3)) / 100.0
                }
            else:
                # Default fallback
                if 'phonetic similarity' in query_template.lower():
                    requirements['phonetic_similarity'] = {'Medium': 1.0}
    
    # Extract orthographic similarity distribution (Light/Medium/Far percentages)
    # First try VALIDATION HINTS section (more reliable format)
    orthographic_match = re.search(r'\[VALIDATION HINTS\].*?Orthographic similarity:\s*([^.;]+)', query_template, re.I | re.DOTALL)
    if orthographic_match:
        hints_text = orthographic_match.group(1)
        hints_match = re.search(r'(\d+)%\s+Light.*?(\d+)%\s+Medium(?:.*?(\d+)%\s+Far)?', hints_text, re.I)
        if hints_match:
            requirements['orthographic_similarity'] = {
                'Light': int(hints_match.group(1)) / 100.0,
                'Medium': int(hints_match.group(2)) / 100.0
            }
            if hints_match.group(3):
                requirements['orthographic_similarity']['Far'] = int(hints_match.group(3)) / 100.0
    
    # If not found in VALIDATION HINTS, try main text patterns
    if not requirements['orthographic_similarity']:
        # Pattern 1: "orthographic similarity is reflected in 20% Light, 60% Medium, and 20% Far"
        orthographic_match = re.search(r'orthographic similarity.*?(\d+)%\s+Light.*?(\d+)%\s+Medium.*?(\d+)%\s+Far', query_template, re.I | re.DOTALL)
        if orthographic_match:
            requirements['orthographic_similarity'] = {
                'Light': int(orthographic_match.group(1)) / 100.0,
                'Medium': int(orthographic_match.group(2)) / 100.0,
                'Far': int(orthographic_match.group(3)) / 100.0
            }
        else:
            # Pattern 2: "20% of the variations using Light similarity, 60% using Medium similarity, and 20% using Far similarity"
            orthographic_match = re.search(r'orthographic similarity.*?(\d+)%.*?Light.*?(\d+)%.*?Medium.*?(\d+)%.*?Far', query_template, re.I | re.DOTALL)
            if orthographic_match:
                requirements['orthographic_similarity'] = {
                    'Light': int(orthographic_match.group(1)) / 100.0,
                    'Medium': int(orthographic_match.group(2)) / 100.0,
                    'Far': int(orthographic_match.group(3)) / 100.0
                }
            else:
                # Default fallback
                if 'orthographic similarity' in query_template.lower():
                    requirements['orthographic_similarity'] = {'Medium': 1.0}
    
    # Extract UAV seed name from Phase 3 requirements
    uav_match = re.search(r'For the seed "([^"]+)" ONLY', query_template, re.I)
    if uav_match:
        requirements['uav_seed_name'] = uav_match.group(1)
    
    return requirements


if __name__ == "__main__":
    
    import sys
    import json
    if len(sys.argv) < 2:
        input_file = "example_synapse_2.json"
    else:
        input_file = sys.argv[1]
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"📂 Loading synapse from: {input_file}\n")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    query_template = data['query_template']
    
    print(parse_query_template(query_template))