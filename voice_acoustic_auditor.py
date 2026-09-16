"""
Acoustic Auditing (GK4) and WAV Stitching Submodule.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import os
import math
import struct
import wave
from typing import List, Tuple


def audit_wav_acoustic(
    wav_path: str,
    min_size_kb: float = 10.0,
    min_rms: float = 0.003,
    min_peak: float = 0.02
) -> Tuple[bool, str]:
    """
    Performs Gatekeeper 4 (GK4) acoustic auditing on a WAV file.
    STRICT: Rejects silent audio (RMS < 0.003 or Peak < 0.02).
    """
    if not os.path.exists(wav_path):
        return False, f"File does not exist: {wav_path}"

    size_bytes = os.path.getsize(wav_path)
    size_kb = size_bytes / 1024.0
    if size_kb < min_size_kb:
        return False, f"File size too small: {size_kb:.1f} KB < {min_size_kb:.1f} KB"

    try:
        with wave.open(wav_path, 'rb') as wf:
            framerate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            n_channels = wf.getnchannels()
            n_frames = wf.getnframes()

            if n_frames == 0:
                return False, "WAV has 0 frames"

            raw_bytes = wf.readframes(n_frames)

            if sampwidth == 2:
                fmt = f"<{n_frames * n_channels}h"
                samples = struct.unpack(fmt, raw_bytes)
                sum_sq = sum(float(s) * float(s) for s in samples)
                rms = math.sqrt(sum_sq / len(samples)) / 32768.0
                peak = max(abs(s) for s in samples) / 32768.0

                if rms < min_rms:
                    return False, f"Acoustic RMS too low: {rms:.5f} < {min_rms:.5f} (SILENT / CORRUPT)"
                if peak < min_peak:
                    return False, f"Acoustic Peak too low: {peak:.5f} < {min_peak:.5f} (FLAT / SILENT)"

                duration_sec = n_frames / framerate
                return True, f"Valid WAV ({duration_sec:.1f}s, {size_kb:.1f}KB, RMS={rms:.4f}, Peak={peak:.4f})"
            return True, f"Valid WAV non-16bit ({size_kb:.1f}KB)"
    except Exception as e:
        return False, f"Error reading WAV: {str(e)}"


def generate_silence_wav(output_path: str, duration_sec: float, framerate: int = 24000, n_channels: int = 1):
    """Generates an uncompressed PCM silence WAV file for spacing padding."""
    n_frames = int(framerate * duration_sec)
    raw_silence = b'\x00\x00' * (n_frames * n_channels)
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(raw_silence)


def stitch_wav_chunks(
    chunk_paths: List[str],
    output_part_path: str,
    intra_silence_sec: float = 1.0,
    inter_silence_sec: float = 2.0
):
    """Stitches audio chunks into a complete Part WAV with multi-tier silence pacing."""
    if not chunk_paths:
        raise ValueError("No chunk paths provided to stitch.")

    with wave.open(chunk_paths[0], 'rb') as first_wf:
        channels = first_wf.getnchannels()
        sampwidth = first_wf.getsampwidth()
        framerate = first_wf.getframerate()

    intra_silence_data = b'\x00' * (int(framerate * intra_silence_sec) * channels * sampwidth)
    with wave.open(output_part_path, 'wb') as out_wf:
        out_wf.setnchannels(channels)
        out_wf.setsampwidth(sampwidth)
        out_wf.setframerate(framerate)
        for i, chunk_path in enumerate(chunk_paths):
            with wave.open(chunk_path, 'rb') as wf:
                out_wf.writeframes(wf.readframes(wf.getnframes()))
            if i < len(chunk_paths) - 1:
                out_wf.writeframes(intra_silence_data)


def stitch_master_audio(part_wav_paths: List[str], output_master_path: str, inter_part_silence_sec: float = 5.0) -> str:
    """Concatenates all 15 Part WAV files into a single master audio documentary."""
    if not part_wav_paths:
        raise ValueError("No part WAV paths provided for master assembly.")

    print(f"Assembling Master Audio from {len(part_wav_paths)} parts into {output_master_path}...")
    with wave.open(part_wav_paths[0], 'rb') as first_wf:
        channels = first_wf.getnchannels()
        sampwidth = first_wf.getsampwidth()
        framerate = first_wf.getframerate()

    inter_part_silence_data = b'\x00' * (int(framerate * inter_part_silence_sec) * channels * sampwidth)
    with wave.open(output_master_path, 'wb') as out_wf:
        out_wf.setnchannels(channels)
        out_wf.setsampwidth(sampwidth)
        out_wf.setframerate(framerate)
        for i, p_path in enumerate(part_wav_paths):
            with wave.open(p_path, 'rb') as wf:
                out_wf.writeframes(wf.readframes(wf.getnframes()))
            if i < len(part_wav_paths) - 1:
                out_wf.writeframes(inter_part_silence_data)

    print(f"Master Audio assembly complete: {output_master_path} ({os.path.getsize(output_master_path)/(1024*1024):.2f} MB)")
    return output_master_path
