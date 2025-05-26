#!/usr/bin/env bash
set -e

# 1) Clean old artifacts
rm -rf build/ dist/ TranscriberApp-mac.zip

# 2) Install PyInstaller + gdown
pip install --no-cache-dir pyinstaller gdown huggingface-hub requests

# 3) Download all models (HF + Drive)
python download_models.py

# 4) Ensure ffmpeg and bundle it
if ! command -v ffmpeg &>/dev/null; then
  brew install ffmpeg
fi
mkdir -p tools
cp "$(which ffmpeg)" tools/ffmpeg
chmod +x tools/ffmpeg

# 5) Build the .app
pyinstaller TranscriberApp-macos.spec

# 6) Zip for distribution
ditto -c -k --sequesterRsrc dist/TranscriberApp.app TranscriberApp-mac.zip
