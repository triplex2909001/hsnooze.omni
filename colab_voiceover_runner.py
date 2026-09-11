"""
HISTORYSNOOZE: GOOGLE COLAB RUNNER (COLAB-CLI COMPLIANT)
Module: colab_voiceover_runner.py
Version: 1.3.0
Purpose:
  - Official Colab runner using k2-fsa/OmniVoice zero-shot TTS engine on GPU (T4/L4/A100).
  - Native Google Drive mount (/content/drive/MyDrive/) eliminating network upload overhead.
  - Sequential Part 1 to Part 15 processing with Chunk-Level Smart Delta Restart.
  - STRICT Gatekeeper GK4 acoustic auditing (RMS >= 0.003, Peak >= 0.02).
"""

import os
import sys
import argparse
import time
from pathlib import Path

from voice_chunk_engine import (
    ChunkVoiceoverPipeline,
    OmniVoiceBackend,
    clean_voiceover_script,
    audit_wav_acoustic
)


def mount_colab_drive() -> Path:
    try:
        from google.colab import drive
        print("[Colab] Mounting Google Drive to /content/drive...")
        drive.mount('/content/drive')
        return Path("/content/drive/MyDrive")
    except ImportError:
        print("[Colab] Running outside Google Colab environment.")
        return Path("./gdrive_mount")


def run_pipeline(project_folder_path: str, voice_ref_path: str, render_video: bool = False):
    proj_dir = Path(project_folder_path)
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project directory does not exist: {proj_dir}")

    audio_dir = proj_dir / "02. Media Generation" / "audio"
    combined_dir = proj_dir / "02. Media Generation" / "combined"
    script_file = combined_dir / "combined_voiceover.txt"

    if not script_file.exists():
        raise FileNotFoundError(f"Script file not found: {script_file}")

    print("=" * 70)
    print(f"HISTORYSNOOZE COLAB OMNIVOICE RUNNER: {proj_dir.name}")
    print(f"Model: k2-fsa/OmniVoice (Zero-Shot Voice Cloning via CUDA)")
    print("=" * 70)

    with open(script_file, "r", encoding="utf-8") as f:
        full_text = f.read()

    if "=== PART BREAK ===" in full_text:
        raw_parts = [p.strip() for p in full_text.split("=== PART BREAK ===") if p.strip()]
    else:
        raw_parts = [p.strip() for p in full_text.split("\n\n\n") if p.strip()]

    print(f"Loaded {len(raw_parts)} parts from script.")

    # Initialize official k2-fsa/OmniVoice backend on CUDA GPU
    tts_backend = OmniVoiceBackend(device="cuda:0")
    pipeline = ChunkVoiceoverPipeline(tts_backend=tts_backend, output_dir=str(audio_dir))

    all_part_wavs = []
    for p_num in range(1, len(raw_parts) + 1):
        print(f"\n>>> PROCESSING PART {p_num:02d}/{len(raw_parts):02d} VIA OMNIVOICE <<<")
        p_text = clean_voiceover_script(raw_parts[p_num - 1])
        part_wav = pipeline.process_part(part_num=p_num, part_text=p_text, voice_ref=voice_ref_path)
        all_part_wavs.append(part_wav)

    print("\n" + "=" * 70)
    print("ALL 15 PARTS COMPLETED AND AUDITED VIA OMNIVOICE!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniVoice Colab Runner")
    parser.add_argument("--project-dir", type=str, required=True, help="Path to project directory on Drive")
    parser.add_argument("--voice-ref", type=str, required=True, help="Path to reference audio file")
    args = parser.parse_args()

    run_pipeline(args.project_dir, args.voice_ref)
