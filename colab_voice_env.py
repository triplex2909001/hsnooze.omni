"""
Colab Environment, Milo Reference Locator, and CLI Parser for Voiceover.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import os
import argparse
from pathlib import Path
from typing import Optional


def mount_colab_drive() -> Path:
    """Mounts Google Drive natively in Colab environment."""
    try:
        from google.colab import drive
        print("[Colab] Mounting Google Drive to /content/drive...")
        drive.mount('/content/drive')
        return Path("/content/drive/MyDrive")
    except ImportError:
        print("[Colab] Running outside Google Colab environment.")
        return Path("./gdrive_mount")


def find_milo_voice_reference() -> Optional[str]:
    """Finds official Milo voice reference audio sample in Drive or local directories."""
    candidates = [
        "/content/drive/MyDrive/00.codebases/mainvoice/voice_preview_milo - calm, soothing and meditative.mp3",
        "/content/drive/MyDrive/00.codebases/mainvoice/voice_preview_milo.mp3",
        "/content/voice_preview_milo.mp3",
        "./00.codebases/mainvoice/voice_preview_milo - calm, soothing and meditative.mp3",
        "./mainvoice/voice_preview_milo - calm, soothing and meditative.mp3",
        "./mainvoice/voice_preview_milo.mp3"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def parse_voiceover_args() -> argparse.Namespace:
    """Parses CLI arguments for Colab voiceover runner."""
    parser = argparse.ArgumentParser(description="OmniVoice Colab Runner v1.5.0")
    parser.add_argument("--project-dir", "--project-path", dest="project_dir", type=str, required=True, help="Path to project directory on Google Drive")
    parser.add_argument("--voice-ref", type=str, default=None, help="Path to reference audio file")
    parser.add_argument("--parts", type=str, default=None, help="Comma-separated part numbers to run")
    parser.add_argument("--num-step", type=int, default=16, help="Sampling steps for ODE solver")
    return parser.parse_args()
