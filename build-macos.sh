#!/usr/bin/env bash
set -e

# 1) Clean up any old artifacts & models
rm -rf build/ dist/ TranscriberApp-mac.zip backend/models

# 2) Install Python deps (exactly as pinned)
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# 3) Download all models (Hugging Face + Google Drive)
python download_models.py

# 4) Bundle ffmpeg
if ! command -v ffmpeg &>/dev/null; then
  brew install ffmpeg
fi
mkdir -p tools
cp "$(which ffmpeg)" tools/ffmpeg
chmod +x tools/ffmpeg

# 5) Build the macOS .app
pyinstaller TranscriberApp-macos.spec

# 6) Zip for distribution
ditto -c -k --sequesterRsrc dist/TranscriberApp.app TranscriberApp-mac.zip
