"""
High-accuracy non-Latin → Latin transliteration
with Arabic name-aware vowel restoration.
"""

import re

# ---- Try loading PyICU ----
try:
    import icu
    ICU_AVAILABLE = True
    ICU_TRANSLITERATOR = icu.Transliterator.createInstance(
        "Any-Latin; Latin-ASCII"
    )
except Exception:
    ICU_AVAILABLE = False
    ICU_TRANSLITERATOR = None

from unidecode import unidecode


# -------------------------------------------------
# Expanded Arabic NAME dictionary with phonetic-optimized transliterations
# -------------------------------------------------
ARABIC_NAME_FIXES = {
    # Common first names - optimized for phonetic similarity
    "محمد": "muhammad",
    "أحمد": "ahmad", 
    "احمد": "ahmad",
    "محمود": "mahmoud",
    "علي": "ali",
    "عمر": "omar",
    "خالد": "khalid",
    "يوسف": "youssef",
    "إبراهيم": "ibrahim",
    "ابراهيم": "ibrahim", 
    "عبدالله": "abdullah",
    "عبد": "abd",
    "حسن": "hassan",
    "حسين": "hussein",
    "سعد": "saad",
    "سعيد": "saeed",
    "سعدون": "saadoun",
    "تميم": "tamim",
    "فاطمة": "fatima",
    "مريم": "maryam",
    "نور": "nour",
    "ليلى": "layla",
    "سارة": "sarah",
    "زينب": "zainab",
    "أمير": "amir",
    "امير": "amir",
    "كريم": "karim",
    "طارق": "tariq",
    "جمال": "jamal",
    "رشيد": "rashid",
    "سليم": "salim",
    "ناصر": "nasser",
    "فيصل": "faisal",
    "سلطان": "sultan",
    "منصور": "mansour",
    "ياسر": "yasser",
    "وليد": "walid",
    "هشام": "hisham",
    "بلال": "bilal",
    "زياد": "ziad",
    "رامي": "rami",
    "سامي": "sami",
    "عادل": "adel",
    "نبيل": "nabil",
    "جميل": "jamil",
    "مصطفى": "mustafa",
    "رضا": "rida",
    "هاني": "hani",
    "ماجد": "majid",
    "عماد": "imad",
    "أسامة": "osama",
    "اسامة": "osama",
    
    # Additional common Arabic names for better coverage
    "عبدالرحمن": "abdulrahman",
    "عبدالعزيز": "abdulaziz", 
    "عبدالرحيم": "abdulrahim",
    "عبدالكريم": "abdulkarim",
    "عبدالحميد": "abdulhamid",
    "عبدالمجيد": "abdulmajid",
    "عبدالقادر": "abdulqader",
    "عبدالناصر": "abdulnasser",
    "عبدالسلام": "abdulsalam",
    "عبدالوهاب": "abdulwahab",
    "صالح": "saleh",
    "صلاح": "salah",
    "طه": "taha",
    "ياسين": "yaseen",
    "حمزة": "hamza",
    "عثمان": "othman",
    "إسماعيل": "ismail",
    "اسماعيل": "ismail",
    "موسى": "musa",
    "عيسى": "issa",
    "داود": "dawood",
    "سليمان": "sulaiman",
    "يحيى": "yahya",
    "زكريا": "zakariya",
    "إدريس": "idris",
    "ادريس": "idris",
    "أيوب": "ayoub",
    "ايوب": "ayoub",
    "يونس": "younes",
    "لقمان": "luqman",
    "ذو الكفل": "dhulkifl",
    
    # Female names
    "عائشة": "aisha",
    "خديجة": "khadija",
    "حفصة": "hafsa",
    "أم كلثوم": "umm kulthum",
    "رقية": "ruqayya",
    "سودة": "sawda",
    "جويرية": "juwayriya",
    "صفية": "safiyya",
    "ميمونة": "maymuna",
    "أم سلمة": "umm salama",
    "أم حبيبة": "umm habiba",
    "زينب": "zainab",
    "رملة": "ramla",
    "هند": "hind",
    "أسماء": "asma",
    "اسماء": "asma",
    "سمية": "sumayya",
    "لبنى": "lubna",
    "سلمى": "salma",
    "دعاء": "duaa",
    "رنا": "rana",
    "ريم": "reem",
    "لينا": "lina",
    "منى": "muna",
    "هالة": "hala",
    "نادية": "nadia",
    "سميرة": "samira",
    "كريمة": "karima",
    "جميلة": "jamila",
    "نعيمة": "naima",
    "حليمة": "halima",
    "رحمة": "rahma",
    "بركة": "baraka",
    "نجاة": "najat",
    "سعاد": "suad",
    "وداد": "widad",
    "إيمان": "iman",
    "ايمان": "iman",
    "أمل": "amal",
    "امل": "amal",
    "رجاء": "raja",
    "هدى": "huda",
    "نهى": "nuha",
    "سهى": "suha",
    "ضحى": "duha",
    "شروق": "shuruq",
    "غروب": "ghurub",
    
    # Common last names / family names
    "العلي": "al-ali",
    "الحسن": "al-hassan", 
    "الحسين": "al-hussein",
    "المحمد": "al-muhammad",
    "الأحمد": "al-ahmad",
    "الاحمد": "al-ahmad",
    "العمر": "al-omar",
    "الخالد": "al-khalid",
    "السعيد": "al-saeed",
    "الناصر": "al-nasser",
    "المنصور": "al-mansour",
    "الرشيد": "al-rashid",
    "السليم": "al-salim",
    "الفيصل": "al-faisal",
    "السلطان": "al-sultan",
    "الشريف": "al-sharif",
    "الهاشمي": "al-hashimi",
    "القاسم": "al-qasim",
    "الصالح": "al-saleh",
    "الطيب": "al-tayeb",
    "الكريم": "al-karim",
    "الجميل": "al-jamil",
    "النور": "al-nour",
    "الزهراء": "al-zahra",
    "البدر": "al-badr",
    "النجم": "al-najm",
    "الشمس": "al-shams",
    "القمر": "al-qamar",
    "الورد": "al-ward",
    "الياسمين": "al-yasmin",
    "الزهر": "al-zahr",
    "العود": "al-oud",
    "الطرب": "al-tarab",
    "الغناء": "al-ghina",
    "الموسيقى": "al-musiqa",
}


# Improved Arabic letter mapping with better phonetic representation
ARABIC_LETTER_MAP = {
    # Alif variants - optimized for phonetic matching
    "ا": "a",
    "أ": "a",  # Alif with hamza above
    "إ": "i",  # Alif with hamza below  
    "آ": "aa", # Alif madda
    "ى": "a",  # Alif maqsura
    
    # Consonants - optimized for English phonetic algorithms
    "ب": "b",
    "ت": "t", 
    "ث": "th",  # Keep 'th' for better phonetic matching
    "ج": "j",
    "ح": "h",   # Simplified from heavy 'H' sound
    "خ": "kh",  # Keep 'kh' for distinctiveness
    "د": "d",
    "ذ": "th",  # Map to 'th' like ث for consistency
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "sh",  # Keep 'sh' for distinctiveness
    "ص": "s",   # Simplified to 's' for better phonetic matching
    "ض": "d",   # Simplified to 'd' for better phonetic matching
    "ط": "t",   # Simplified to 't' for better phonetic matching
    "ظ": "z",   # Simplified to 'z' for better phonetic matching
    "ع": "a",   # Ayn - map to vowel for better phonetic flow
    "غ": "gh",  # Keep 'gh' for distinctiveness
    "ف": "f",
    "ق": "q",   # Keep 'q' for distinctiveness from 'k'
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "ة": "a",   # Ta marbuta - usually 'a' at end of words
    
    # Semi-vowels / long vowels - optimized for phonetic flow
    "و": "w",   # Simplified from 'ou' to 'w' for better consonant matching
    "ي": "y",   # Changed from 'i' to 'y' for better consonant matching
    
    # Hamza variants - simplified for better flow
    "ء": "",    # Standalone hamza - silent
    "ئ": "y",   # Hamza on ya - use 'y' for consonant sound
    "ؤ": "w",   # Hamza on waw - use 'w' for consonant sound
}


def arabic_fallback(text: str) -> str:
    """
    Improved Arabic fallback transliteration with vowel insertion.
    Arabic doesn't write short vowels, so we add them heuristically.
    """
    # Handle "ال" (al-) prefix specially
    if text.startswith("ال"):
        rest = text[2:]
        rest_transliterated = _transliterate_arabic_word(rest)
        return "al-" + rest_transliterated
    
    return _transliterate_arabic_word(text)


def _transliterate_arabic_word(text: str) -> str:
    """Transliterate a single Arabic word with improved vowel insertion and phonetic optimization."""
    out = []
    prev_was_consonant = False
    
    # Define consonant and vowel sets for better classification
    consonants = {'b', 't', 'th', 'j', 'h', 'kh', 'd', 'r', 'z', 's', 'sh', 
                  'f', 'q', 'k', 'l', 'm', 'n', 'gh', 'w', 'y'}
    vowels = {'a', 'i', 'u', 'e', 'o', 'aa'}
    
    for i, ch in enumerate(text):
        if ch == " ":
            out.append(" ")
            prev_was_consonant = False
            continue
        
        mapped = ARABIC_LETTER_MAP.get(ch, ch)
        
        # Better consonant/vowel classification
        is_consonant = any(cons in mapped for cons in consonants)
        is_vowel = any(vowel in mapped for vowel in vowels)
        
        # Improved vowel insertion logic
        if prev_was_consonant and is_consonant:
            # Context-aware vowel insertion
            next_char = text[i+1] if i+1 < len(text) else ""
            next_mapped = ARABIC_LETTER_MAP.get(next_char, next_char)
            
            # Choose vowel based on context
            if 'i' in next_mapped or 'y' in next_mapped:
                out.append('i')  # Use 'i' before i/y sounds
            elif 'u' in next_mapped or 'w' in next_mapped:
                out.append('u')  # Use 'u' before u/w sounds  
            elif mapped in ['k', 'q', 'kh', 'gh']:  # Guttural sounds
                out.append('a')  # Use 'a' with guttural consonants
            elif mapped in ['s', 'sh', 'z', 'th']:  # Sibilant sounds
                out.append('i')  # Use 'i' with sibilants
            else:
                out.append('a')  # Default to 'a'
        
        out.append(mapped)
        prev_was_consonant = is_consonant and not is_vowel
    
    result = "".join(out)
    
    # Enhanced cleanup with phonetic optimization
    result = re.sub(r"aa+", "a", result)      # Multiple a's
    result = re.sub(r"ii+", "i", result)      # Multiple i's  
    result = re.sub(r"uu+", "u", result)      # Multiple u's
    result = re.sub(r"([aeiou])\1+", r"\1", result)  # Any repeated vowels
    result = re.sub(r"hh+", "h", result)      # Multiple h's
    result = re.sub(r"([bcdfghjklmnpqrstvwxyz])\1{2,}", r"\1\1", result)  # Limit consonant repetition to max 2
    result = re.sub(r"''", "'", result)       # Double apostrophes
    result = re.sub(r"^'", "", result)        # Leading apostrophe
    result = re.sub(r"'$", "", result)        # Trailing apostrophe
    
    # Add final vowel if word ends with consonant (common in Arabic)
    if result and result[-1] in consonants:
        # Choose final vowel based on word pattern
        if any(x in result for x in ['sh', 'kh', 'gh', 'th']):
            result += 'a'  # Use 'a' for words with these sounds
        elif result.endswith(('m', 'n')):
            result += 'a'  # Common Arabic ending pattern
        elif result.endswith(('k', 'q')):
            result += 'i'  # Common pattern for these sounds
        else:
            result += 'a'  # Default
    
    return result


# -------------------------------------------------
# Main function
# -------------------------------------------------
def to_latin(name: str) -> str:
    if not name or not str(name).strip():
        return ""

    text = str(name).strip()

    # ---- Step 1: ICU (best possible) ----
    if ICU_AVAILABLE:
        try:
            latin = ICU_TRANSLITERATOR.transliterate(text)
            latin = unidecode(latin)
            return " ".join(latin.split()).lower()
        except Exception:
            pass

    # ---- Step 2: Arabic dictionary + improved fallback ----
    if re.search(r"[\u0600-\u06FF]", text):
        parts = text.split()
        restored = []

        for p in parts:
            # Check dictionary first (exact match)
            if p in ARABIC_NAME_FIXES:
                restored.append(ARABIC_NAME_FIXES[p])
            else:
                # Use improved fallback with vowel insertion
                restored.append(arabic_fallback(p))

        latin = " ".join(restored)
        latin = unidecode(latin)
        return " ".join(latin.split()).lower()

    # ---- Step 3: Generic fallback ----
    latin = unidecode(text)
    return " ".join(latin.split()).lower()


# -------------------------------------------------
# TEST
# -------------------------------------------------
if __name__ == "__main__":
    samples = [
        "أحمد العلي"
    ]

    for s in samples:
        print(f"{s} -> {to_latin(s)}")
