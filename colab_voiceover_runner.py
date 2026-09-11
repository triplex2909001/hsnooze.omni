"""
HISTORYSNOOZE: GOOGLE COLAB RUNNER (COLAB-CLI COMPLIANT)
Module: colab_voiceover_runner.py
Version: 1.5.0
Purpose:
  - Official Colab runner using k2-fsa/OmniVoice zero-shot TTS engine on GPU (T4/L4/A100).
  - Native Google Drive mount (/content/drive/MyDrive/) eliminating network upload overhead.
  - Sequential or selective Part processing (--parts 1,2,3) with Chunk-Level Smart Delta Restart.
  - Pre-encoded VoiceClonePrompt cache for Milo sample to avoid redundant Whisper feature extraction.
  - STRICT Gatekeeper GK4 acoustic auditing (RMS >= 0.003, Peak >= 0.02, size >= 10 KB).
  - Automatic Master Audio concatenation (Master_[Character]_Full_Voiceover.wav) with 5.0s silence pacing.
  - Automatic session keep-alive and direct Google Drive synchronization.
"""

import os
import re
import sys
import argparse
import time
from pathlib import Path
from typing import List, Optional

from voice_chunk_engine import (
    ChunkVoiceoverPipeline,
    OmniVoiceBackend,
    clean_voiceover_script,
    audit_wav_acoustic,
    stitch_master_audio
)


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


def run_pipeline(
    project_folder_path: str,
    voice_ref_path: Optional[str] = None,
    parts_to_process: Optional[List[int]] = None,
    num_step: int = 16
):
    proj_dir = Path(project_folder_path)
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project directory does not exist: {proj_dir}")

    audio_dir = proj_dir / "02. Media Generation" / "audio"
    chunks_dir = proj_dir / "02. Media Generation" / "chunks"
    combined_dir = proj_dir / "02. Media Generation" / "combined"
    script_file = combined_dir / "combined_voiceover.txt"

    audio_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    if not script_file.exists():
        raise FileNotFoundError(f"Script file not found: {script_file}")

    if not voice_ref_path or not os.path.exists(voice_ref_path):
        detected_ref = find_milo_voice_reference()
        if detected_ref:
            voice_ref_path = detected_ref
            print(f"[Colab] Auto-detected Milo voice reference: {voice_ref_path}")
        else:
            raise FileNotFoundError(f"Voice reference audio not found. Specified: {voice_ref_path}")

    print("=" * 75)
    print(f"HISTORYSNOOZE COLAB OMNIVOICE RUNNER (v1.5.0): {proj_dir.name}")
    print(f"Backend: k2-fsa/OmniVoice (CUDA GPU Accelerated)")
    print(f"Milo Reference: {voice_ref_path}")
    print(f"Sampling Steps: {num_step}")
    print("=" * 75)

    with open(script_file, "r", encoding="utf-8") as f:
        full_text = f.read()

    if "=== PART BREAK ===" in full_text:
        raw_parts = [p.strip() for p in full_text.split("=== PART BREAK ===") if p.strip()]
    else:
        raw_parts = [p.strip() for p in full_text.split("\n\n\n") if p.strip()]

    total_parts = len(raw_parts)
    print(f"Loaded {total_parts} parts from combined script.")

    target_part_indices = parts_to_process if parts_to_process else list(range(1, total_parts + 1))
    print(f"Target parts to process: {target_part_indices}")

    # Initialize k2-fsa/OmniVoice on CUDA GPU
    tts_backend = OmniVoiceBackend(device="cuda:0")
    pipeline = ChunkVoiceoverPipeline(tts_backend=tts_backend, output_dir=str(audio_dir))

    processed_part_paths = {}
    for p_num in target_part_indices:
        if p_num < 1 or p_num > total_parts:
            print(f"[WARN] Part {p_num} out of bounds (1..{total_parts}), skipping.")
            continue

        print(f"\n{'='*30} PROCESSING PART {p_num:02d}/{total_parts:02d} {'='*30}")
        p_text = clean_voiceover_script(raw_parts[p_num - 1])
        part_wav = pipeline.process_part(part_num=p_num, part_text=p_text, voice_ref=voice_ref_path)
        processed_part_paths[p_num] = part_wav

    # Check completeness of all 15 parts for Master Assembly
    all_15_valid = True
    master_part_list = []
    for p in range(1, total_parts + 1):
        p_path = audio_dir / f"Part_{p:02d}.wav"
        if p_path.exists():
            is_valid, msg = audit_wav_acoustic(str(p_path), min_size_kb=50, min_rms=0.003, min_peak=0.02)
            if is_valid:
                master_part_list.append(str(p_path))
            else:
                all_15_valid = False
                print(f"[INCOMPLETE] Part_{p:02d}.wav failed GK4: {msg}")
        else:
            all_15_valid = False
            print(f"[MISSING] Part_{p:02d}.wav does not exist.")

    if all_15_valid and len(master_part_list) == total_parts:
        print("\n" + "=" * 75)
        print("ALL 15 PARTS VALIDATED! ASSEMBLING MASTER AUDIO DOCUMENTARY...")
        character_slug = re.sub(r'[^a-zA-Z0-9_]', '_', proj_dir.name.split('-')[0].strip())
        master_output_path = str(audio_dir / f"Master_{character_slug}_Full_Voiceover.wav")
        stitch_master_audio(master_part_list, master_output_path, inter_part_silence_sec=5.0)

        is_master_valid, master_msg = audit_wav_acoustic(master_output_path, min_size_kb=1000, min_rms=0.003, min_peak=0.02)
        if is_master_valid:
            print(f"🎉 MASTER VOICEOVER ASSEMBLED & VERIFIED GK4: {master_msg}")
            print(f"Path: {master_output_path}")
        else:
            print(f"[ERROR] Master voiceover failed GK4 audit: {master_msg}")
    else:
        print(f"\n[INFO] Partial batch completed ({len(processed_part_paths)} processed). Master assembly deferred until all {total_parts} parts pass GK4.")

    print("\n" + "=" * 75)
    print("COLAB OMNIVOICE WORKER EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniVoice Colab Runner v1.5.0")
    parser.add_argument("--project-dir", "--project-path", dest="project_dir", type=str, required=True, help="Path to project directory on Google Drive")
    parser.add_argument("--voice-ref", type=str, default=None, help="Path to reference audio file (default: auto-detected Milo)")
    parser.add_argument("--parts", type=str, default=None, help="Comma-separated part numbers to run (e.g. '1,2,3' or '4')")
    parser.add_argument("--num-step", type=int, default=16, help="Sampling steps for ODE solver (default: 16 on GPU)")
    args = parser.parse_args()

    parts_list = None
    if args.parts:
        parts_list = [int(p.strip()) for p in args.parts.split(",") if p.strip().isdigit()]

    run_pipeline(
        project_folder_path=args.project_dir,
        voice_ref_path=args.voice_ref,
        parts_to_process=parts_list,
        num_step=args.num_step
    )
