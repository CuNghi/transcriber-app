import csv
import os
from datetime import datetime
from config import UPLOAD_FOLDER

FIELDNAMES = [
    'Title',
    'Broadcast Date',
    'Guest Name',
    'Subtitle',
    'Image',
    'Broadcast Recording Audio File',
    'Transcription',
    'Tags',
    'Backlinks',
    'Image Alt Text'
]

def export_csv(metadata: dict, transcript: str) -> str:
    # Build row exactly matching FIELDNAMES
    row = {key: metadata.get(key, '') for key in FIELDNAMES}
    row['Transcription'] = transcript

    ts       = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"transcript_{ts}.csv"
    out_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(row)

    return filename
