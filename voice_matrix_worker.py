"""
HISTORYSNOOZE: GITHUB ACTIONS MATRIX WORKER
Module: voice_matrix_worker.py
Version: 1.2.0
Purpose:
  - Executed by GitHub Actions matrix job for a single part (e.g. part 1, 2, ... 15).
  - Divides part into sentence chunks (15-30 words).
  - Checks Google Drive for existing valid chunks (Smart Delta Restart).
  - Synthesizes missing chunks and immediately uploads each chunk to Google Drive.
  - Stitches chunks into Part_{XX}.wav, uploads to Drive, and validates GK4.
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

from voice_chunk_engine import (
    ChunkVoiceoverPipeline,
    split_into_paragraphs,
    split_paragraph_into_sentences,
    audit_wav_acoustic,
    stitch_wav_chunks,
    generate_silence_wav
)


def run_matrix_worker(part_num: int, script_path: str, output_dir: str, voice_ref: str = None):
    """Runs synthesis for a single part inside a GitHub Actions runner."""
    print(f"==================================================")
    print(f"GITHUB ACTIONS MATRIX WORKER - PART {part_num:02d}")
    print(f"==================================================")
    
    script_p = Path(script_path)
    if not script_p.exists():
        raise FileNotFoundError(f"Script file not found: {script_p}")
        
    with open(script_p, "r", encoding="utf-8") as f:
        full_text = f.read()
        
    # Split into parts
    raw_parts = [p.strip() for p in full_text.split("\n\n\n") if p.strip()]
    if len(raw_parts) < 15:
        raw_parts = [p.strip() for p in full_text.split("## Part") if p.strip()]
        
    part_idx = part_num - 1
    if part_idx >= len(raw_parts):
        raise IndexError(f"Part {part_num} out of range in script (found {len(raw_parts)} parts).")
        
    part_text = raw_parts[part_idx]
    
    # Initialize pipeline
    pipeline = ChunkVoiceoverPipeline(tts_backend=None, output_dir=output_dir)
    part_wav = pipeline.process_part(part_num=part_num, part_text=part_text, voice_ref=voice_ref)
    
    print(f"\nWorker Part {part_num:02d} completed successfully: {part_wav}")
    # In GitHub Actions, subsequent step calls Google Drive API / rclone / gdrive to sync part_wav and chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Matrix Worker")
    parser.add_argument("--part", type=int, required=True, help="Part number (1-15)")
    parser.add_argument("--script", type=str, required=True, help="Path to combined_voiceover.txt")
    parser.add_argument("--output-dir", type=str, default="./audio_out", help="Output directory")
    parser.add_argument("--voice-ref", type=str, default=None, help="Path to reference audio")
    args = parser.parse_args()
    
    run_matrix_worker(args.part, args.script, args.output_dir, args.voice_ref)
