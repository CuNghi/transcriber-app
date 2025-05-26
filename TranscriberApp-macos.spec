# TranscriberApp-macos.spec
# -*- mode: python ; coding: utf-8 -*-

import os, sys
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
)

# --- 1) Gather dependencies ---
import speechbrain, pyannote, ctranslate2, onnxruntime

sb_datas, sb_binaries, sb_hidden       = collect_all("speechbrain")
pn_datas, pn_binaries, pn_hidden       = collect_all("pyannote")
ct_datas, ct_binaries, ct_hidden       = collect_all("ctranslate2")
onnx_datas, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
lf_datas                              = collect_data_files("lightning_fabric")

hidden_mods = (
    collect_submodules("torch")
  + collect_submodules("faster_whisper")
  + collect_submodules("ctranslate2")
  + sb_hidden
  + pn_hidden
  + ct_hidden
  + onnx_hidden
  + ["pkg_resources.py2_warn"]
)

# --- 2) macOS-specific ffmpeg binary ---
# Place a macOS ffmpeg executable at tools/ffmpeg in your repo
ffmpeg_bin = ("tools/ffmpeg", ".")

# --- 3) Bundle on-disk model snapshots ---
model_datas = [
    ("backend/models", "models"),
]

# --- 4) Build steps ---
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

a = Analysis(
    ["backend/app.py"],
    pathex=["."],
    binaries=[ffmpeg_bin] + sb_binaries + pn_binaries + ct_binaries + onnx_binaries,
    datas=[
        ("frontend",                     "frontend"),
        ("backend/plugins/diarizers",    "plugins/diarizers"),
        ("backend/plugins/transcribers", "plugins/transcribers"),
    ]
    + sb_datas
    + pn_datas
    + ct_datas
    + onnx_datas
    + lf_datas
    + model_datas,
    hiddenimports=hidden_mods,
    hookspath=[],
    runtime_hooks=[],
    excludes=["speechbrain.lobes.models.spacy"],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="TranscriberApp",
    debug=False,
    strip=False,
    upx=False,       # disable UPX on macOS
    console=False,   # no terminal window, GUI .app
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="TranscriberApp",
)
