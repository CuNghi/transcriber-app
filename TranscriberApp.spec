# TranscriberApp.spec
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

# --- 2) Bundle on-disk model snapshots ---
model_datas = [
    # Bundles everything under backend/models → dist_folder/models
    ("backend/models", "models"),
]

# --- 3) Build steps ---
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

a = Analysis(
    ["backend/app.py"],
    pathex=["."],
    binaries=[("ffmpeg.exe", ".")] + sb_binaries + pn_binaries + ct_binaries + onnx_binaries,
    datas=[
        ("frontend",                      "frontend"),
        ("backend/plugins/diarizers",     "plugins/diarizers"),
        ("backend/plugins/transcribers",  "plugins/transcribers"),
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
    upx=True,
    console=True,    # set to False if you want no console window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="TranscriberApp",
)
