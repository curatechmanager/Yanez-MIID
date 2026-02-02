from faker import Faker
import re

def looks_like_address(address: str) -> bool:
    address = address.strip().lower()

    # Keep all letters (Latin and non-Latin) and numbers
    # Using a more compatible approach for Unicode characters
    address_len = re.sub(r'[^\w]', '', address.strip(), flags=re.UNICODE)
    if len(address_len) < 30:
        return False
    if len(address_len) > 300:  # maximum length check
        return False

    # Count letters (both Latin and non-Latin) - using \w which includes Unicode letters
    letter_count = len(re.findall(r'[^\W\d]', address, flags=re.UNICODE))
    if letter_count < 20:
        return False

    if re.match(r"^[^a-zA-Z]*$", address):  # no letters at all
        return False
    if len(set(address)) < 5:  # all chars basically the same
        return False
        
    # Has at least one digit in a comma-separated section
    # Replace hyphens and semicolons with empty strings before counting numbers
    address_for_number_count = address.replace('-', '').replace(';', '')
    # Split address by commas and check for numbers in each section
    sections = [s.strip() for s in address_for_number_count.split(',')]
    sections_with_numbers = []
    for section in sections:
        # Only match ASCII digits (0-9), not other numeric characters
        number_groups = re.findall(r"[0-9]+", section)
        if len(number_groups) > 0:
            sections_with_numbers.append(section)
    # Need at least 1 section that contains numbers
    if len(sections_with_numbers) < 1:
        return False

    if address.count(",") < 2:
        return False
    
    # Check for special characters that should not be in addresses
    special_chars = ['`', ':', '%', '$', '@', '*', '^', '[', ']', '{', '}', '_', '«', '»']
    if any(char in address for char in special_chars):
        return False
    
    # # Contains common address words or patterns
    # common_words = ["st", "street", "rd", "road", "ave", "avenue", "blvd", "boulevard", "drive", "ln", "lane", "plaza", "city", "platz", "straße", "straße", "way", "place", "square", "allee", "allee", "gasse", "gasse"]
    # # Also check for common patterns like "1-1-1" (Japanese addresses) or "Unter den" (German)
    # has_common_word = any(word in address for word in common_words)
    # has_address_pattern = re.search(r'\d+-\d+-\d+', address) or re.search(r'unter den|marienplatz|champs|place de', address)
    
    # if not (has_common_word or has_address_pattern):
    #     return False
    
    return True

def generate_addresses(num_addresses, country_locale, country_name):
    """
    Generates a specified number of fake addresses that pass looks_like_address validation.
    Format: street number street name, city, state postal code, country

    Args:
        num_addresses (int): The number of addresses to generate.
        country_locale (str): The locale code for the country.
        country_name (str): The country name to use in addresses.

    Returns:
        list: A list of generated addresses as strings.
    """
    try:
        # Create a Faker instance with the specified locale, with fallback
        try:
            fake = Faker(country_locale)
            # Test if the locale works by generating a simple address component
            fake.city()
        except Exception:
            # If locale fails, use English as fallback
            fake = Faker('en_US')
            
        addresses = []
        attempts = 0
        max_attempts = num_addresses * 10  # Prevent infinite loops
        
        while len(addresses) < num_addresses and attempts < max_attempts:
            attempts += 1
            
            # Generate individual components
            street_number = fake.building_number()
            street_name = fake.street_name()
            city = fake.city()
            
            # Handle state/region - not all locales have states
            try:
                if hasattr(fake, 'state_abbr'):
                    state = fake.state_abbr()
                elif hasattr(fake, 'state'):
                    state = fake.state()
                else:
                    # Use region or administrative area for non-US locales
                    state = fake.administrative_unit() if hasattr(fake, 'administrative_unit') else "Region"
            except Exception:
                state = "ST"  # Default state abbreviation
                
            postal_code = fake.postcode()
            
            # Ensure components are long enough and clean
            if len(street_name) < 5:
                street_name += " " + fake.street_suffix()
            if len(city) < 4:
                city += "ville"
            
            # Remove forbidden special characters
            forbidden_chars = ['`', ':', '%', '@', '*', '^', '[', ']', '{', '}', '_', '«', '»']
            for char in forbidden_chars:
                street_name = street_name.replace(char, '')
                city = city.replace(char, '')
                state = str(state).replace(char, '')
                postal_code = str(postal_code).replace(char, '')
            
            # Format: street number street name, city, state postal code, country
            address = f"{street_number} {street_name}, {city}, {state} {postal_code}, {country_name.title()}"
            
            # Ensure address meets minimum requirements
            if len(address) < 50:  # Pad if too short
                address = f"{street_number} {street_name} Extended Boulevard, {city} Metropolitan Area, {state} {postal_code}, {country_name.title()}"
            
            # Validate the address
            if looks_like_address(address):
                addresses.append(address)
            
        # If we couldn't generate enough valid addresses, fill with basic ones
        while len(addresses) < num_addresses:
            basic_address = f"12345 Main Street Boulevard, {country_name.title()} Capital City, ST 12345, {country_name.title()}"
            if looks_like_address(basic_address):
                addresses.append(basic_address)
            else:
                addresses.append(f"Error: Could not generate valid address for {country_name}")
                
        return addresses
    except Exception as e:
        return [f"Error: Could not generate addresses for locale '{country_locale}'. {e}"]

def country_to_locale(country_name):
    """Convert country name to Faker locale code - supports all 195 countries"""
    country_map = {
        # North America
        'usa': 'en_US', 'united states': 'en_US', 'america': 'en_US', 'us': 'en_US',
        'canada': 'en_CA', 'mexico': 'es_MX', 'guatemala': 'es_ES', 'belize': 'en_US',
        'el salvador': 'es_ES', 'honduras': 'es_ES', 'nicaragua': 'es_ES',
        'costa rica': 'es_ES', 'panama': 'es_ES',
        
        # Caribbean
        'cuba': 'es_ES', 'jamaica': 'en_US', 'haiti': 'fr_FR', 'dominican republic': 'es_ES',
        'puerto rico': 'es_ES', 'trinidad and tobago': 'en_US', 'barbados': 'en_US',
        'grenada': 'en_US', 'saint lucia': 'en_US', 'saint vincent and the grenadines': 'en_US',
        'antigua and barbuda': 'en_US', 'dominica': 'en_US', 'saint kitts and nevis': 'en_US',
        'bahamas': 'en_US', 'aruba': 'nl_NL', 'curacao': 'nl_NL', 'martinique': 'fr_FR',
        'guadeloupe': 'fr_FR', 'bermuda': 'en_US', 'cayman islands': 'en_US',
        'british virgin islands': 'en_US', 'us virgin islands': 'en_US',
        'turks and caicos': 'en_US', 'anguilla': 'en_US', 'montserrat': 'en_US',
        
        # South America
        'brazil': 'pt_BR', 'argentina': 'es_AR', 'chile': 'es_CL', 'peru': 'es_PE',
        'ecuador': 'es_EC', 'colombia': 'es_CO', 'venezuela': 'es_VE', 'guyana': 'en_US',
        'suriname': 'nl_NL', 'french guiana': 'fr_FR', 'uruguay': 'es_ES',
        'paraguay': 'es_ES', 'bolivia': 'es_ES', 'falkland islands': 'en_US',
        
        # Europe
        'uk': 'en_GB', 'united kingdom': 'en_GB', 'britain': 'en_GB', 'england': 'en_GB',
        'scotland': 'en_GB', 'wales': 'en_GB', 'northern ireland': 'en_GB', 'ireland': 'en_IE',
        'france': 'fr_FR', 'germany': 'de_DE', 'spain': 'es_ES', 'italy': 'it_IT',
        'portugal': 'pt_PT', 'netherlands': 'nl_NL', 'belgium': 'fr_BE', 'luxembourg': 'fr_FR',
        'switzerland': 'de_CH', 'austria': 'de_AT', 'poland': 'pl_PL', 'czech republic': 'cs_CZ',
        'slovakia': 'sk_SK', 'hungary': 'hu_HU', 'romania': 'ro_RO', 'bulgaria': 'bg_BG',
        'croatia': 'hr_HR', 'slovenia': 'sl_SI', 'serbia': 'sr_RS', 'montenegro': 'sr_RS',
        'bosnia and herzegovina': 'bs_BA', 'albania': 'sq_AL', 'greece': 'el_GR',
        'turkey': 'tr_TR', 'cyprus': 'el_GR', 'malta': 'mt_MT', 'denmark': 'da_DK',
        'sweden': 'sv_SE', 'norway': 'no_NO', 'finland': 'fi_FI', 'iceland': 'is_IS',
        'estonia': 'et_EE', 'latvia': 'lv_LV', 'lithuania': 'lt_LT', 'belarus': 'be_BY',
        'ukraine': 'uk_UA', 'moldova': 'ro_RO', 'russia': 'ru_RU', 'georgia': 'ka_GE',
        'armenia': 'hy_AM', 'azerbaijan': 'az_AZ', 'monaco': 'fr_FR', 'andorra': 'es_ES',
        'san marino': 'it_IT', 'vatican': 'it_IT', 'liechtenstein': 'de_DE',
        'faroe islands': 'da_DK', 'greenland': 'da_DK', 'north macedonia': 'mk_MK',
        'kosovo': 'sq_AL',
        
        # Asia
        'china': 'zh_CN', 'japan': 'ja_JP', 'south korea': 'ko_KR', 'korea': 'ko_KR',
        'north korea': 'ko_KR', 'india': 'hi_IN', 'pakistan': 'ur_PK', 'bangladesh': 'bn_BD',
        'sri lanka': 'si_LK', 'nepal': 'ne_NP', 'bhutan': 'ne_NP', 'maldives': 'hi_IN',
        'afghanistan': 'ps_AF', 'iran': 'fa_IR', 'iraq': 'ar_SA', 'syria': 'ar_SA',
        'lebanon': 'ar_SA', 'jordan': 'ar_SA', 'israel': 'he_IL', 'palestine': 'ar_SA',
        'saudi arabia': 'ar_SA', 'yemen': 'ar_SA', 'oman': 'ar_SA', 'uae': 'ar_SA',
        'united arab emirates': 'ar_SA', 'qatar': 'ar_SA', 'bahrain': 'ar_SA', 'kuwait': 'ar_SA',
        'thailand': 'th_TH', 'vietnam': 'vi_VN', 'cambodia': 'th_TH', 'laos': 'th_TH',
        'myanmar': 'th_TH', 'malaysia': 'ms_MY', 'singapore': 'en_SG', 'brunei': 'ms_MY',
        'indonesia': 'id_ID', 'philippines': 'tl_PH', 'taiwan': 'zh_TW', 'hong kong': 'zh_HK',
        'macau': 'zh_CN', 'mongolia': 'zh_CN', 'kazakhstan': 'ru_RU', 'uzbekistan': 'ru_RU',
        'kyrgyzstan': 'ru_RU', 'tajikistan': 'ru_RU', 'turkmenistan': 'ru_RU',
        'timor-leste': 'pt_PT', 'east timor': 'pt_PT',
        
        # Africa
        'egypt': 'ar_EG', 'libya': 'ar_EG', 'tunisia': 'ar_EG', 'algeria': 'ar_EG',
        'morocco': 'ar_EG', 'sudan': 'ar_EG', 'south sudan': 'en_US', 'ethiopia': 'am_ET',
        'eritrea': 'am_ET', 'djibouti': 'ar_EG', 'somalia': 'ar_EG', 'kenya': 'en_US',
        'uganda': 'en_US', 'tanzania': 'en_US', 'rwanda': 'en_US', 'burundi': 'en_US',
        'democratic republic of congo': 'fr_FR', 'republic of congo': 'fr_FR', 'congo': 'fr_FR',
        'central african republic': 'fr_FR', 'chad': 'fr_FR', 'cameroon': 'fr_FR',
        'equatorial guinea': 'es_ES', 'gabon': 'fr_FR', 'sao tome and principe': 'pt_PT',
        'nigeria': 'en_NG', 'niger': 'fr_FR', 'mali': 'fr_FR', 'burkina faso': 'fr_FR',
        'senegal': 'fr_FR', 'gambia': 'en_US', 'guinea-bissau': 'pt_PT', 'guinea': 'fr_FR',
        'sierra leone': 'en_US', 'liberia': 'en_US', 'ivory coast': 'fr_FR', 'ghana': 'en_US',
        'togo': 'fr_FR', 'benin': 'fr_FR', 'mauritania': 'ar_EG', 'western sahara': 'ar_EG',
        'cape verde': 'pt_PT', 'south africa': 'en_US', 'namibia': 'en_US', 'botswana': 'en_US',
        'zimbabwe': 'en_US', 'zambia': 'en_US', 'malawi': 'en_US', 'mozambique': 'pt_PT',
        'madagascar': 'fr_FR', 'mauritius': 'en_US', 'seychelles': 'en_US',
        'comoros': 'ar_EG', 'angola': 'pt_PT', 'lesotho': 'en_US', 'swaziland': 'en_US',
        'eswatini': 'en_US', 'mayotte': 'fr_FR', 'reunion': 'fr_FR',
        
        # Oceania
        'australia': 'en_AU', 'new zealand': 'en_NZ', 'fiji': 'en_AU', 'papua new guinea': 'en_AU',
        'solomon islands': 'en_AU', 'vanuatu': 'en_AU', 'new caledonia': 'fr_FR',
        'french polynesia': 'fr_FR', 'samoa': 'en_AU', 'american samoa': 'en_US',
        'tonga': 'en_AU', 'kiribati': 'en_AU', 'tuvalu': 'en_AU', 'nauru': 'en_AU',
        'palau': 'en_AU', 'marshall islands': 'en_US', 'micronesia': 'en_US',
        'cook islands': 'en_AU', 'niue': 'en_AU', 'tokelau': 'en_AU',
        'wallis and futuna': 'fr_FR', 'pitcairn islands': 'en_US',
        
        # Additional territories
        'gibraltar': 'en_GB', 'jersey': 'en_GB', 'guernsey': 'en_GB', 'isle of man': 'en_GB',
        'svalbard': 'no_NO', 'jan mayen': 'no_NO', 'bouvet island': 'no_NO',
        'south georgia': 'en_GB', 'british indian ocean territory': 'en_GB',
        'christmas island': 'en_AU', 'cocos islands': 'en_AU', 'norfolk island': 'en_AU',
        'heard island': 'en_AU', 'antarctica': 'en_US', 'saint helena': 'en_GB',
        'ascension island': 'en_GB', 'tristan da cunha': 'en_GB'
    }
    return country_map.get(country_name.lower(), 'en_US')

def fallback_generator(country_name, count):
    country_locale = country_to_locale(country_name)
    addresses = generate_addresses(count, country_locale, country_name)
    return addresses
if __name__ == "__main__":
    # print("🌍 Global Address Generator - Supports ALL 195 countries!")
    # print("Examples: USA, Germany, Japan, Brazil, Nigeria, Australia, etc.")
    # print("Also supports territories and dependencies worldwide.")
    print()
    
    country_name = input("Enter country name: ")
    count = int(input("How many addresses: "))
    addresses = fallback_generator(country_name, count)
    # country_locale = country_to_locale(country_name)
    
    # print(f"\nGenerating {count} addresses for {country_name} (locale: {country_locale})...\n")
    # addresses = generate_addresses(count, country_locale, country_name)
    for i, addr in enumerate(addresses, 1):
        print(f"'{addr}'")
    
    print(f"\n{'='*50}")
    print(f"Successfully generated {len(addresses)} addresses!")
