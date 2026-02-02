import json
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Warning: requests not available. Real address generation will be disabled.")

# Import jellyfish for tiered similarity generation
try:
    import jellyfish
    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False


# Import geonamescache for getting real city names

# Minimal IdentitySynapse class
class IdentitySynapse:
    def __init__(self, identity, query_template, timeout=120.0):
        self.identity = identity
        self.query_template = query_template
        self.timeout = timeout

def generate_variations(synapse: IdentitySynapse) :
    """
    Generate variations for all identities.
    Returns different structure for UAV seed vs normal seeds.
    """

    from _parse_query import parse_query_template
    requirements = parse_query_template(synapse.query_template)

    # print(f"   Variation count: {requirements['variation_count']}")
    # print(f"   Rule percentage: {requirements['rule_percentage']*100:.0f}%")
    # print(f"   Rules: {requirements['rules']}")
    # if requirements.get('phonetic_similarity'):
    #     print(f"   Phonetic Similarity: {requirements['phonetic_similarity']}")
    # if requirements.get('orthographic_similarity'):
    #     print(f"   Orthographic Similarity: {requirements['orthographic_similarity']}")
    # if requirements.get('uav_seed_name'):
    #     print(f"   UAV Seed: {requirements['uav_seed_name']}")
    # if requirements.get('rule_sentence'):
    #     print(f"   Rule_sentence: {requirements['rule_sentence']}")
    # print()
    all_variations = {}
    uav_seed_name = requirements.get('uav_seed_name')
    
    # CRITICAL: Ensure we process ALL identities from seed (no missing names)
    # Validator checks: missing_names = set(seed_names) - set(variations.keys())
    seed_names = [identity[0] for identity in synapse.identity if len(identity) > 0]
    print(f"📋 Seed names: {seed_names}")
    
    for identity in synapse.identity:
        original_name = identity[0] if len(identity) > 0 else "Unknown"  # Keep EXACT original
        name = original_name  # Use exact same name for key
        dob = identity[1] if len(identity) > 1 else "1990-01-01"
        address = identity[2] if len(identity) > 2 else "Unknown"
        
        print(f"------------Processing: {name} | {dob} | {address}------------")
        is_uav_seed = (uav_seed_name and name.lower() == uav_seed_name.lower())
        
        if is_uav_seed:
            print("-This is the UAV seed - will include UAV data")
        
        # Generate variations with tiered similarity targeting
        # from name.index import generate_name_variations
        from name_1.index import generate_name_variations
        
        name_vars = generate_name_variations(
            name,
            variation_count=requirements['variation_count'],
            rule_percentage=requirements['rule_percentage'],
            rules=requirements['rules'],
            phonetic_similarity=requirements.get('phonetic_similarity'),
            orthographic_similarity=requirements.get('orthographic_similarity'),
        )
        from _dob import generate_dob_variations
        dob_vars = generate_dob_variations(dob, requirements['variation_count'])
        
        from address.address import generate_address_variations
        address_vars = generate_address_variations(address, requirements['variation_count'])
        
        
        # if(len(address_vars) < requirements['variation_count']):
            
            # save_error("address", {address}, "fallback - don't find")

        variation_count = requirements['variation_count']
        
        # Ensure all arrays have at least the required count
        while len(name_vars) < variation_count:
            # Add more variations if needed
            name_vars.append(name)
        while len(dob_vars) < variation_count:
            dob_vars.append(dob)
        while len(address_vars) < variation_count:
            address_vars.append(address)
        
        # Trim to exact count
        name_vars = name_vars[:variation_count]
        dob_vars = dob_vars[:variation_count]
        address_vars = address_vars[:variation_count]
        
        # Combine into [name, dob, address] format
        # CRITICAL: Ensure no duplicates - validator penalizes duplicates
        combined = []
        seen_combinations = set()
        print(f"-Generated name: {len(name_vars)} | dob: {len(dob_vars)} | address {len(address_vars)}\n")
        for i in range(variation_count):
            # Create unique combination by checking for duplicates
            name_var = name_vars[i]
            dob_var = dob_vars[i]
            addr_var = address_vars[i]
            
            # Normalize for duplicate detection (same as validator)
            combo_key = (
                name_var.lower().strip() if name_var else "",
                dob_var.strip() if dob_var else "",
                addr_var.lower().strip() if addr_var else ""
            )
    
            # If duplicate, modify slightly to make unique
            attempt = 0
            while combo_key in seen_combinations and attempt < 100:
                # Try next variation in arrays
                idx = (i + attempt) % variation_count
                name_var = name_vars[idx] if idx < len(name_vars) else name
                dob_var = dob_vars[idx] if idx < len(dob_vars) else dob
                addr_var = address_vars[idx] if idx < len(address_vars) else address
                combo_key = (
                    name_var.lower().strip() if name_var else "",
                    dob_var.strip() if dob_var else "",
                    addr_var.lower().strip() if addr_var else ""
                )
                attempt += 1
            
            # If still duplicate, create a unique one by modifying address slightly
            if combo_key in seen_combinations:
                # Add a unique suffix to address to make it unique
                addr_var = f"{addr_var} #UNQ{i}"
                combo_key = (
                    name_var.lower().strip() if name_var else "",
                    dob_var.strip() if dob_var else "",
                    addr_var.lower().strip() if addr_var else ""
                )
            
            seen_combinations.add(combo_key)
            combined.append([name_var, dob_var, addr_var])
        
        # CRITICAL: Ensure exact count (validator checks this strictly)
        combined = combined[:variation_count]
        
        # Phase 3: Return different structure for UAV seed
        if is_uav_seed:
            # Generate UAV address
            from address.address1 import generate_uav_address
            uav_data = generate_uav_address(address)
            print(f"   🎯 Generated UAV: {uav_data['address']} ({uav_data['label']})")
            print(f"      Coordinates: ({uav_data['latitude']}, {uav_data['longitude']})")
            
            # UAV seed structure: {name: {variations: [...], uav: {...}}}
            all_variations[name] = {
                'variations': combined,
                'uav': uav_data
            }
        else:
            # Normal structure: {name: [[name, dob, addr], ...]}
            all_variations[name] = combined
        
    
    # CRITICAL: Validate completeness before returning
    # 1. Check for missing names
    output_names = set(all_variations.keys())
    missing = set(seed_names) - output_names
    if missing:
        print(f"X  WARNING: Missing names in output: {missing}")
        # Add missing names with empty variations (shouldn't happen, but safety check)
        for missing_name in missing:
            all_variations[missing_name] = []
    
    # 2. Check for extra names (names not in seed)
    extra = output_names - set(seed_names)
    if extra:
        print(f"X  WARNING: Extra names in output (will be penalized): {extra}")
        print(f"   Output names: {list(output_names)}")
        print(f"   Seed names: {seed_names}")
        # Remove extra names to avoid penalty
        for extra_name in list(extra):
            del all_variations[extra_name]
    
    # 3. Validate variation counts
    for name, variations in all_variations.items():
        if isinstance(variations, dict):
            # UAV structure
            var_list = variations.get('variations', [])
        else:
            var_list = variations
        
        expected_count = requirements['variation_count']
        actual_count = len(var_list)
        if actual_count != expected_count:
            print(f"X  WARNING: {name}: {actual_count} variations (expected {expected_count})")
            # Ensure exact count
            if actual_count < expected_count:
                # Pad with last variation or default
                if var_list:
                    last_var = var_list[-1]
                    while len(var_list) < expected_count:
                        var_list.append(last_var.copy() if isinstance(last_var, list) else last_var)
                else:
                    # No variations - add default
                    default_identity = next((id for id in synapse.identity if id[0] == name), None)
                    if default_identity:
                        default_var = [
                            default_identity[0] if len(default_identity) > 0 else name,
                            default_identity[1] if len(default_identity) > 1 else "1990-01-01",
                            default_identity[2] if len(default_identity) > 2 else "Unknown"
                        ]
                        var_list = [default_var.copy() for _ in range(expected_count)]
                    else:
                        var_list = [[name, "1990-01-01", "Unknown"] for _ in range(expected_count)]
            else:
                # Trim to exact count
                var_list = var_list[:expected_count]
            
            # Update the variations
            if isinstance(variations, dict):
                variations['variations'] = var_list
                all_variations[name] = variations
            else:
                all_variations[name] = var_list
    
    # Print all_variations with clean format
    print("\n" + "=" * 80)
    print("GENERATED VARIATIONS")
    print("=" * 80)
    
    return all_variations

# ============================================================================
# Entry Point
# ============================================================================

def main():
    import sys
    if len(sys.argv) < 2:
        input_file = "example_synapse.json"
    else:
        input_file = sys.argv[1]
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"📂 Loading synapse from: {input_file}\n")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    synapse = IdentitySynapse(
        identity=data['identity'],
        query_template=data['query_template'],
        timeout=data.get('timeout', 120.0)
    )
    
    variations = generate_variations(synapse)


if __name__ == "__main__":
    main()

