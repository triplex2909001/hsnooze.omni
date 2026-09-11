"""
HISTORYSNOOZE: GITHUB ACTIONS MATRIX WORKER
Module: voice_matrix_worker.py
Version: 1.3.0
Purpose:
  - Official runner using k2-fsa/OmniVoice zero-shot TTS engine.
  - Executed by GitHub Actions matrix job for a single part (e.g. part 1, 2, ... 15).
  - Divides part into sentence chunks (15-30 words).
  - Synthesizes each chunk with reference voice Milo (mainvoice/voice_preview_milo.mp3).
  - Stitches chunks into Part_{XX}.wav and validates STRICT GK4 acoustic criteria.
"""

import os
import sys
import argparse
from pathlib import Path

from voice_chunk_engine import (
    ChunkVoiceoverPipeline,
    OmniVoiceBackend,
    clean_voiceover_script
)


def run_matrix_worker(part_num: int, script_path: str, output_dir: str, voice_ref: str = None):
    print(f"==================================================")
    print(f"GITHUB ACTIONS MATRIX WORKER - PART {part_num:02d}")
    print(f"Engine: k2-fsa/OmniVoice (Zero-Shot Voice Cloning)")
    print(f"==================================================")
    
    script_p = Path(script_path)
    if not script_p.exists():
        raise FileNotFoundError(f"Script file not found: {script_p}")
        
    with open(script_p, "r", encoding="utf-8") as f:
        full_text = f.read()
        
    # Split into 15 parts cleanly using delimiter
    if "=== PART BREAK ===" in full_text:
        raw_parts = [p.strip() for p in full_text.split("=== PART BREAK ===") if p.strip()]
    else:
        raw_parts = [p.strip() for p in full_text.split("\n\n\n") if p.strip()]
        
    part_idx = part_num - 1
    if part_idx >= len(raw_parts):
        raise IndexError(f"Part {part_num} out of range in script (found {len(raw_parts)} parts).")
        
    part_text = clean_voiceover_script(raw_parts[part_idx])
    
    # Initialize real k2-fsa/OmniVoice backend (CPU on GitHub Actions, GPU on Colab)
    device = "cuda:0" if ("CUDA_VISIBLE_DEVICES" in os.environ or os.environ.get("USE_GPU") == "1") else "cpu"
    tts_backend = OmniVoiceBackend(device=device)
    
    # Initialize pipeline
    pipeline = ChunkVoiceoverPipeline(tts_backend=tts_backend, output_dir=output_dir)
    part_wav = pipeline.process_part(part_num=part_num, part_text=part_text, voice_ref=voice_ref)
    
    print(f"\nWorker Part {part_num:02d} completed successfully with OmniVoice: {part_wav}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniVoice Matrix Worker")
    parser.add_argument("--part", type=int, required=True, help="Part number (1-15)")
    parser.add_argument("--script", type=str, required=True, help="Path to combined_voiceover.txt")
    parser.add_argument("--output-dir", type=str, default="./audio_out", help="Output directory")
    parser.add_argument("--voice-ref", type=str, default=None, help="Path to reference audio")
    args = parser.parse_args()
    
    run_matrix_worker(args.part, args.script, args.output_dir, args.voice_ref)
