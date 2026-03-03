from __future__ import annotations

from zoneinfo import available_timezones


# 40 commonly used UI languages.
LANGUAGE_OPTIONS: list[tuple[str, str]] = [
    ("uk", "Українська"),
    ("en", "English"),
    ("es", "Español"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("pl", "Polski"),
    ("cs", "Čeština"),
    ("sk", "Slovenčina"),
    ("ro", "Română"),
    ("hu", "Magyar"),
    ("nl", "Nederlands"),
    ("sv", "Svenska"),
    ("no", "Norsk"),
    ("da", "Dansk"),
    ("fi", "Suomi"),
    ("el", "Ελληνικά"),
    ("tr", "Türkçe"),
    ("bg", "Български"),
    ("sr", "Srpski"),
    ("hr", "Hrvatski"),
    ("sl", "Slovenščina"),
    ("lt", "Lietuvių"),
    ("lv", "Latviešu"),
    ("et", "Eesti"),
    ("ru", "Русский"),
    ("ar", "العربية"),
    ("he", "עברית"),
    ("hi", "हिन्दी"),
    ("bn", "বাংলা"),
    ("ur", "اردو"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("vi", "Tiếng Việt"),
    ("th", "ไทย"),
    ("id", "Bahasa Indonesia"),
    ("ms", "Bahasa Melayu"),
    ("fa", "فارسی"),
]

DEFAULT_LANGUAGE_CODE = "uk"
DEFAULT_TIMEZONE = "Europe/Kyiv"


def all_timezones() -> list[str]:
    values = sorted(available_timezones())
    if values:
        return values
    # Fallback for environments without bundled tzdata.
    return [
        "UTC",
        "Europe/Kyiv",
        "Europe/Warsaw",
        "Europe/Berlin",
        "Europe/London",
        "America/New_York",
        "America/Los_Angeles",
        "Asia/Tokyo",
    ]

