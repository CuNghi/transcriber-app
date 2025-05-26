# backend/plugins/diarizers/1_pyannote_diarizer.py

import os
import sys
import shutil

import huggingface_hub
# ─── 0) Nuke HF’s repo-id validation so local paths work ──────────────
import huggingface_hub.utils._validators as _hf_validators
_hf_validators.validate_repo_id = lambda *args, **kwargs: None

# ─── 1) Patch single-file & snapshot downloader ───────────────────────
def _offline_hf_hub_download(repo_id, filename=None, **kwargs):
    # allow passing a local path directly
    if os.path.isdir(repo_id):
        folder = repo_id
    else:
        mapping = {
            "pyannote/segmentation":        os.path.join(MODELS_DIR, "pyannote", "segmentation"),
            "pyannote/speaker-diarization": os.path.join(MODELS_DIR, "pyannote", "speaker-diarization"),
            "speechbrain/spkrec-ecapa-voxceleb": os.path.join(MODELS_DIR, "speechbrain", "spkrec-ecapa-voxceleb"),
        }
        folder = mapping.get(repo_id)
    if not folder or not os.path.isdir(folder):
        raise FileNotFoundError(f"No bundled folder for {repo_id!r}; looked in {folder!r}")
    if not filename:
        raise ValueError("hf_hub_download: missing filename")

    fn = filename.lower()
    # config
    if fn.endswith((".yml", ".yaml", ".json", ".txt")):
        cand = os.path.join(folder, filename)
        if os.path.exists(cand):
            return cand
    # weights
    if fn.endswith((".pt", ".bin", ".ckpt")):
        cand = os.path.join(folder, filename)
        if os.path.exists(cand):
            return cand
        for f in os.listdir(folder):
            if f.lower().endswith((".pt", ".bin", ".ckpt")):
                return os.path.join(folder, f)
    # SpeechBrain “custom.py” shim
    if fn.endswith(".py") and "speechbrain" in repo_id:
        return os.path.join(folder, "hyperparams.yaml")
    # fallback
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        return path
    raise FileNotFoundError(f"{filename!r} not found in {folder!r}")

huggingface_hub.hf_hub_download   = _offline_hf_hub_download
huggingface_hub.snapshot_download = lambda *args, local_dir=None, **kw: (
    local_dir if local_dir and os.path.isdir(local_dir)
    else (_ for _ in ()).throw(FileNotFoundError(f"Offline snapshot not found for {args[0]!r}"))
)

# ─── 2) Locate models directory ───────────────────────────────────────
if hasattr(sys, "_MEIPASS"):
    MODELS_DIR = os.path.join(sys._MEIPASS, "models")
else:
    here = os.path.dirname(__file__)
    MODELS_DIR = os.path.abspath(os.path.join(here, "..", "..", "models"))

# ─── 3) Patch PyAnnote internals for offline ──────────────────────────
import pyannote.audio.core.pipeline as _pp
_pp.hf_hub_download = _offline_hf_hub_download

from pyannote.audio.pipelines.utils.getter import get_model as _orig_get_model
from pyannote.audio.core.model import Model
def _offline_get_model(repo_id, use_auth_token=None, **kwargs):
    if repo_id == "pyannote/segmentation":
        seg_folder = os.path.join(MODELS_DIR, "pyannote", "segmentation")
        # now that we’ve disabled validate_repo_id, this will succeed
        return Model.from_pretrained(seg_folder)
    return _orig_get_model(repo_id, use_auth_token=use_auth_token, **kwargs)

import pyannote.audio.pipelines.utils.getter as _getter
_getter.get_model = _offline_get_model

# ─── 4) Disable Windows symlinks ──────────────────────────────────────
import speechbrain.utils.fetching as _sb_fetching
_sb_fetching.link_with_strategy = lambda src, dst, strategy=None: shutil.copy(src, dst)

# ─── 5) Finally load the pipeline offline ─────────────────────────────
from pyannote.audio import Pipeline

SD_FOLDER = os.path.join(MODELS_DIR, "pyannote", "speaker-diarization")
try:
    pipeline = Pipeline.from_pretrained(SD_FOLDER)
except Exception as e:
    raise RuntimeError(f"Failed to load pipeline offline from {SD_FOLDER!r}: {e}")

def diarize(path: str, num_speakers: int):
    return pipeline(path, num_speakers=num_speakers)
