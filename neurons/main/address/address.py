import sys
import json
import os

sys.path.append("../main")
# from db import get_addresses_db
from address.fallback_address import fallback_generator
# from db import save_error

def find_addresses_from_dictionary(mapped_address):
    try:
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dictionary_path = os.path.join(current_dir, 'address_dictionary.json')
        
        with open(dictionary_path, 'r', encoding='utf-8') as f:
            address_dictionary = json.load(f)
        
        # Look for addresses using mapped_address (case-insensitive)
        for country, addresses in address_dictionary.items():
            if country.lower() == mapped_address.lower():
                return addresses
        
        return []  # Return empty list if country not found
        
    except Exception as e:
        print(f"Warning: Could not load address dictionary: {e}")
        return []

def generate_address_variations(address, count=15):
    
    # Address match step - handle special country name mappings
    address_mappings = {
        "north macedonia, the republic of": "north macedonia",
        "congo, democratic republic of the": "democratic republic of the congo",
        "palestinian": "palestinian territory",
        "macau": "macao",
        "burma": "myanmar",
        "ivory coast": "côte d'ivoire",
        "korea, south": "south korea",
        "korea, north": "north korea"
    }
    # Check if address needs mapping
    mapped_address = address_mappings.get(address.lower(), address)
    
    # db_addresses = find_addresses_from_dictionary(mapped_address)
    db_addresses = []
    # db_addresses = get_addresses_db(mapped_address, count)
    if len(db_addresses) >= count:
        return db_addresses[:count]
    else:
        # save_error("address",address,"dictionary")
        needed_count = count - len(db_addresses)
        try:
            fallback_addresses = fallback_generator(address, needed_count)
                
                # Combine database addresses with fallback addresses
            if isinstance(fallback_addresses, list):
                db_addresses.extend(fallback_addresses)
                return db_addresses[:count]  # Ensure exact count
            else:
                return db_addresses  # Return what we have from DB
                    
        except ImportError:
            print(f"Warning: Could not import fallback function from _address1.py")
            return db_addresses  # Return what we have from DB
        except Exception as e:
            print(f"Warning: Fallback function failed: {e}")
            return db_addresses  # Return what we have from DB
   

# Test function
if __name__ == "__main__":
    # Test the new function
    test_address = "russia"
    result = generate_address_variations(test_address, 5)
    print(f"Generated {len(result)} addresses:")
    for i, addr in enumerate(result, 1):
        print(f"{i}. {addr}")
   