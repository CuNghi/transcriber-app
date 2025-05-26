import os, torch

BASE_DIR = os.path.dirname(__file__)    # now points to backend/plugins root
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
CHUNKS_FOLDER = os.path.join(BASE_DIR, 'chunks')
ALLOWED_EXT = {'mp3', 'wav', 'm4a', 'mp4', 'mov', 'avi'}

# Defaults for plugins
default_diarizer = '1_pyannote_diarizer'
default_transcriber = '1_faster_whisper_transcriber'

# Plugin paths
PLUGIN_FOLDER = os.path.join(BASE_DIR, 'plugins')
DIARIZERS_FOLDER = 'diarizers'
TRANSCRIBERS_FOLDER = 'transcribers'

# Parallel workers
MAX_WORKERS = os.cpu_count() or 1

DEFAULT_DEVICE = os.getenv("TRANSCRIBER_DEVICE", "auto")  # "auto"|"cpu"|"cuda"
def get_device():
    pref = DEFAULT_DEVICE.lower()
    if pref == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        return torch.device(pref)