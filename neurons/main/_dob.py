import random

from datetime import datetime, timedelta


def generate_dob_variations(dob: str, count: int = 15):
    """Generate DOB variations"""
    try:
        base_date = datetime.strptime(dob, "%Y-%m-%d")
    except:
        base_date = datetime(1990, 1, 1)
    
    variations = []
    
    # ±1 day
    variations.append((base_date + timedelta(days=1)).strftime("%Y-%m-%d"))
    
    # ±3 days
    variations.append((base_date - timedelta(days=3)).strftime("%Y-%m-%d"))
    
    # ±30 days
    variations.append((base_date + timedelta(days=30)).strftime("%Y-%m-%d"))
    
    # ±90 days
    variations.append((base_date + timedelta(days=90)).strftime("%Y-%m-%d"))
    
    # ±365 days
    variations.append((base_date - timedelta(days=365)).strftime("%Y-%m-%d"))
    
    # Year+month only
    variations.append(base_date.strftime("%Y-%m"))
    
    variations.append((base_date - timedelta(days=1)).strftime("%Y-%m-%d"))
    variations.append((base_date + timedelta(days=3)).strftime("%Y-%m-%d"))
    variations.append((base_date - timedelta(days=30)).strftime("%Y-%m-%d"))
    variations.append((base_date - timedelta(days=90)).strftime("%Y-%m-%d"))
    variations.append((base_date + timedelta(days=365)).strftime("%Y-%m-%d"))
    
    # Fill remaining with random variations
    while len(variations) < count:
        days_offset = random.randint(-365, 365)
        new_date = base_date + timedelta(days=days_offset)
        new_date_str = new_date.strftime("%Y-%m-%d")
        if new_date_str not in variations:
            variations.append(new_date_str)
    
    return variations[:count]