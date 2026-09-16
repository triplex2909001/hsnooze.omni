"""
HISTORYSNOOZE: GOOGLE COLAB RUNNER (COLAB-CLI COMPLIANT)
Module: colab_voiceover_runner.py
Version: 1.5.0
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional

_CUR_DIR = Path(__file__).resolve().parent
if str(_CUR_DIR) not in sys.path:
    sys.path.insert(0, str(_CUR_DIR))

from voice_chunk_engine import (
    ChunkVoiceoverPipeline,
    OmniVoiceBackend,
    clean_voiceover_script,
    audit_wav_acoustic,
    stitch_master_audio
)
from colab_voice_env import (
    mount_colab_drive,
    find_milo_voice_reference,
    parse_voiceover_args
)


def _assemble_master(audio_dir: Path, total_parts: int, proj_dir: Path):
    """Verifies all 15 parts pass GK4 and stitches master audio documentary."""
    master_part_list = []
    for p in range(1, total_parts + 1):
        p_path = audio_dir / f"Part_{p:02d}.wav"
        if p_path.exists():
            is_valid, msg = audit_wav_acoustic(str(p_path), min_size_kb=50, min_rms=0.003, min_peak=0.02)
            if is_valid:
                master_part_list.append(str(p_path))
            else:
                print(f"[INCOMPLETE] Part_{p:02d}.wav failed GK4: {msg}")
        else:
            print(f"[MISSING] Part_{p:02d}.wav does not exist.")

    if len(master_part_list) == total_parts:
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
        print(f"\n[INFO] Partial batch completed ({len(master_part_list)}/{total_parts}). Master assembly deferred.")


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

    for d in (audio_dir, chunks_dir):
        d.mkdir(parents=True, exist_ok=True)
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
    print(f"HISTORYSNOOZE COLAB OMNIVOICE RUNNER: {proj_dir.name} | Steps: {num_step}")
    print("=" * 75)

    with open(script_file, "r", encoding="utf-8") as f:
        full_text = f.read()

    sep = "=== PART BREAK ===" if "=== PART BREAK ===" in full_text else "\n\n\n"
    raw_parts = [p.strip() for p in full_text.split(sep) if p.strip()]
    total_parts = len(raw_parts)
    target_parts = parts_to_process if parts_to_process else list(range(1, total_parts + 1))

    tts_backend = OmniVoiceBackend(device="cuda:0")
    pipeline = ChunkVoiceoverPipeline(tts_backend=tts_backend, output_dir=str(audio_dir))

    for p_num in target_parts:
        if 1 <= p_num <= total_parts:
            print(f"\n{'='*30} PROCESSING PART {p_num:02d}/{total_parts:02d} {'='*30}")
            p_text = clean_voiceover_script(raw_parts[p_num - 1])
            pipeline.process_part(part_num=p_num, part_text=p_text, voice_ref=voice_ref_path)

    _assemble_master(audio_dir, total_parts, proj_dir)
    print("\n" + "=" * 75 + "\nCOLAB OMNIVOICE WORKER EXECUTION COMPLETED!\n" + "=" * 75)


if __name__ == "__main__":
    args = parse_voiceover_args()
    parts_list = [int(p.strip()) for p in args.parts.split(",") if p.strip().isdigit()] if args.parts else None
    run_pipeline(args.project_dir, args.voice_ref, parts_list, args.num_step)
