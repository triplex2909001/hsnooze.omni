"""
HISTORYSNOOZE: VOICE CHUNK ENGINE & MASTER ASSEMBLY
Module: voice_chunk_engine.py
Version: 1.5.0
Facade module providing clean backwards-compatible exports.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import sys
from pathlib import Path

# Submodule resolution
_CUR_DIR = Path(__file__).resolve().parent
if str(_CUR_DIR) not in sys.path:
    sys.path.insert(0, str(_CUR_DIR))

from voice_text_processor import (
    clean_voiceover_script,
    split_into_paragraphs,
    split_paragraph_into_sentences,
)
from voice_acoustic_auditor import (
    audit_wav_acoustic,
    generate_silence_wav,
    stitch_wav_chunks,
    stitch_master_audio,
)
from voice_omnivoice_backend import OmniVoiceBackend
from voice_chunk_pipeline import ChunkVoiceoverPipeline

__all__ = [
    "clean_voiceover_script",
    "split_into_paragraphs",
    "split_paragraph_into_sentences",
    "audit_wav_acoustic",
    "generate_silence_wav",
    "stitch_wav_chunks",
    "stitch_master_audio",
    "OmniVoiceBackend",
    "ChunkVoiceoverPipeline",
]
