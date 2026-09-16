"""
Chunk-Level Voiceover Pipeline with Smart Delta Restart.
Enforces k2-fsa/OmniVoice and strict Gatekeeper GK4 acoustic auditing.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import sys
from pathlib import Path
from typing import Optional

_CUR_DIR = Path(__file__).resolve().parent
if str(_CUR_DIR) not in sys.path:
    sys.path.insert(0, str(_CUR_DIR))

from voice_text_processor import split_into_paragraphs, split_paragraph_into_sentences
from voice_acoustic_auditor import audit_wav_acoustic, stitch_wav_chunks


class ChunkVoiceoverPipeline:
    """Orchestrates chunk-level voiceover generation with Smart Delta Restart and GK4 validation."""

    def __init__(self, tts_backend=None, output_dir: str = "./audio_output", num_step: int = 10):
        if tts_backend is None:
            raise ValueError("[GK4 SECURITY VIOLATION] tts_backend cannot be None! A real k2-fsa/OmniVoice backend is required.")
        self.tts_backend = tts_backend
        self.output_dir = Path(output_dir)
        self.chunks_dir = self.output_dir / "chunks_raw"
        self.parts_dir = self.output_dir
        self.num_step = num_step

        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.parts_dir.mkdir(parents=True, exist_ok=True)

    def _split_chunks_info(self, part_num: int, part_text: str):
        paragraphs = split_into_paragraphs(part_text)
        all_chunks = []
        chunk_counter = 1
        for paragraph in paragraphs:
            sentences = split_paragraph_into_sentences(paragraph)
            for s_idx, sentence in enumerate(sentences):
                c_filename = f"part_{part_num:02d}_chunk_{chunk_counter:03d}.wav"
                all_chunks.append({
                    "id": chunk_counter,
                    "filename": c_filename,
                    "path": self.chunks_dir / c_filename,
                    "text": sentence,
                    "is_paragraph_end": (s_idx == len(sentences) - 1)
                })
                chunk_counter += 1
        return all_chunks

    def _process_chunk_delta(self, item: dict, voice_ref: Optional[str]) -> str:
        c_path = item["path"]
        c_text = item["text"]
        if c_path.exists():
            is_valid, msg = audit_wav_acoustic(str(c_path), min_size_kb=5, min_rms=0.003, min_peak=0.02)
            if is_valid:
                return str(c_path)
            print(f"  [DELTA REBUILD] Corrupt/silent chunk {item['filename']}: {msg}")
            c_path.unlink(missing_ok=True)

        print(f"  [OMNIVOICE SYNTHESIS] {item['filename']} ({len(c_text.split())} words): '{c_text[:40]}...'")
        self.tts_backend.synthesize(text=c_text, output_path=str(c_path), voice_ref=voice_ref, instruct=None, num_step=self.num_step)
        is_valid, msg = audit_wav_acoustic(str(c_path), min_size_kb=1, min_rms=0.003, min_peak=0.02)
        if not is_valid:
            raise RuntimeError(f"Failed GK4 audit for synthesized chunk {item['filename']}: {msg}")
        return str(c_path)

    def process_part(self, part_num: int, part_text: str, voice_ref: Optional[str] = None) -> str:
        final_part_path = self.parts_dir / f"Part_{part_num:02d}.wav"

        # 1. Smart Delta Top-Level Check
        if final_part_path.exists():
            is_valid, msg = audit_wav_acoustic(str(final_part_path), min_size_kb=50, min_rms=0.003, min_peak=0.02)
            if is_valid:
                print(f"[SMART DELTA SKIP] Part_{part_num:02d}.wav already complete & valid: {msg}")
                return str(final_part_path)
            print(f"[REDO] Part_{part_num:02d}.wav failed GK4: {msg}. Re-synthesizing...")

        # 2. Split part into sentence chunks
        chunks_info = self._split_chunks_info(part_num, part_text)
        print(f"Part {part_num:02d}: Split into {len(chunks_info)} sentence chunks.")

        # 3. Generate each chunk with Smart Delta
        valid_chunk_paths = [self._process_chunk_delta(item, voice_ref) for item in chunks_info]

        # 4. Stitch chunks into master Part WAV
        print(f"Stitching {len(valid_chunk_paths)} chunks into {final_part_path.name}...")
        stitch_wav_chunks(valid_chunk_paths, str(final_part_path), intra_silence_sec=1.0, inter_silence_sec=2.0)

        # 5. Final GK4 audit
        is_valid, msg = audit_wav_acoustic(str(final_part_path), min_size_kb=10, min_rms=0.003, min_peak=0.02)
        if not is_valid:
            raise RuntimeError(f"Stitched Part_{part_num:02d}.wav failed GK4 acoustic audit: {msg}")

        print(f"[COMPLETED] Part_{part_num:02d}.wav verified GK4: {msg}")
        return str(final_part_path)
