"""The shared 50-language locale set used across all projects.

Top 50 languages by combined speaker population, using each language's
standard written/software-localization form.  Shared by Dawnlist, EasyPost
Desktop, Easy-Post Mobile Companion, Wren, and software-site so that store
listings stay comparable and a single translation run covers everyone.
"""
from __future__ import annotations

SUPPORTED_LOCALES: list[tuple[str, str, str]] = [
    ("en", "English", "English"),
    ("zh", "Mandarin Chinese", "中文"),
    ("hi", "Hindi", "हिन्दी"),
    ("es", "Spanish", "Español"),
    ("fr", "French", "Français"),
    ("ar", "Arabic", "العربية"),
    ("bn", "Bengali", "বাংলা"),
    ("pt", "Portuguese", "Português"),
    ("ru", "Russian", "Русский"),
    ("ur", "Urdu", "اردو"),
    ("id", "Indonesian", "Bahasa Indonesia"),
    ("de", "German", "Deutsch"),
    ("ja", "Japanese", "日本語"),
    ("mr", "Marathi", "मराठी"),
    ("te", "Telugu", "తెలుగు"),
    ("tr", "Turkish", "Türkçe"),
    ("ta", "Tamil", "தமிழ்"),
    ("vi", "Vietnamese", "Tiếng Việt"),
    ("ko", "Korean", "한국어"),
    ("fa", "Persian", "فارسی"),
    ("ha", "Hausa", "Hausa"),
    ("sw", "Swahili", "Kiswahili"),
    ("jv", "Javanese", "Basa Jawa"),
    ("it", "Italian", "Italiano"),
    ("pa", "Punjabi", "ਪੰਜਾਬੀ"),
    ("gu", "Gujarati", "ગુજરાતી"),
    ("am", "Amharic", "አማርኛ"),
    ("th", "Thai", "ไทย"),
    ("kn", "Kannada", "ಕನ್ನಡ"),
    ("my", "Burmese", "မြန်မာဘာသာ"),
    ("yo", "Yoruba", "Yorùbá"),
    ("uz", "Uzbek", "Oʻzbekcha"),
    ("ml", "Malayalam", "മലയാളം"),
    ("or", "Odia", "ଓଡ଼ିଆ"),
    ("uk", "Ukrainian", "Українська"),
    ("pl", "Polish", "Polski"),
    ("ms", "Malay", "Bahasa Melayu"),
    ("nl", "Dutch", "Nederlands"),
    ("ig", "Igbo", "Igbo"),
    ("si", "Sinhala", "සිංහල"),
    ("ne", "Nepali", "नेपाली"),
    ("ro", "Romanian", "Română"),
    ("zu", "Zulu", "isiZulu"),
    ("so", "Somali", "Soomaali"),
    ("hr", "Croatian", "Hrvatski"),
    ("el", "Greek", "Ελληνικά"),
    ("hu", "Hungarian", "Magyar"),
    ("cs", "Czech", "Čeština"),
    ("he", "Hebrew", "עברית"),
    ("sv", "Swedish", "Svenska"),
]

DEFAULT_LOCALE = "en"
LOCALE_CODES = [code for code, _, _ in SUPPORTED_LOCALES]
LOCALE_NAMES = {code: english for code, english, _ in SUPPORTED_LOCALES}
LOCALE_NATIVE = {code: native for code, _, native in SUPPORTED_LOCALES}
RTL_LOCALES = {"ar", "ur", "fa", "he"}
