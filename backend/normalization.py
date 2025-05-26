# backend/normalization.py
import os, ffmpeg
from config import UPLOAD_FOLDER

def normalize_audio(in_path):
    base = os.path.basename(in_path).rsplit('.',1)[0]
    out_name = f"{base}_norm.wav"
    out_path = os.path.join(UPLOAD_FOLDER, out_name)

    (
      ffmpeg
        .input(in_path)
        .output(out_path, ar='16k', ac=1, format='wav')
        .overwrite_output()
        .run(quiet=True)
    )
    return out_name
