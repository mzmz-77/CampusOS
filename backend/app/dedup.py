import hashlib
import unicodedata
import re


def fingerprint(content: str):
    # Keep punctuation and dates: changed deadlines must never be silently merged.
    normalized = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', content)).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
