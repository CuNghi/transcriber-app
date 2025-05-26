import re

FILLERS = {'um', 'uh', 'like', 'you know'}

def clean_text(text: str) -> str:
    tokens = text.split()
    filtered = [t for t in tokens if t.lower() not in FILLERS]
    joined = ' '.join(filtered)
    return re.sub(r'\s+', ' ', joined).strip()