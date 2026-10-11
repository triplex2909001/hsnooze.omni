"""
Chunk-Level Voiceover Pipeline with Smart Delta Restart.
Enforces k2-fsa/OmniVoice and strict Gatekeeper GK4 acoustic auditing.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import hashlib
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

    def __init__(self, tts_backend=None, output_dir: str = "./audio_output", num_step: int = 10, seed: Optional[int] = None):
        if tts_backend is None:
            raise ValueError("[GK4 SECURITY VIOLATION] tts_backend cannot be None! A real k2-fsa/OmniVoice backend is required.")
        self.tts_backend = tts_backend
        self.output_dir = Path(output_dir)
        self.chunks_dir = self.output_dir / "chunks_raw"
        self.parts_dir = self.output_dir
        self.num_step = num_step
        self.seed = seed  # Fixed seed for voice consistency (fix 2026-10-10)

        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.parts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _text_hash(text: str) -> str:
        """SHA256 of the exact text a wav file must have been synthesized from."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _sidecar_path(wav_path: Path) -> Path:
        """Sidecar file storing the text hash, e.g. part_01_chunk_001.wav.sha."""
        return wav_path.with_name(wav_path.name + ".sha")

    def _sidecar_matches(self, wav_path: Path, text: str) -> bool:
        """True only if the sidecar exists and its hash matches the current text."""
        sha_path = self._sidecar_path(wav_path)
        if not sha_path.exists():
            return False
        try:
            return sha_path.read_text(encoding="utf-8").strip() == self._text_hash(text)
        except OSError:
            return False

    def _write_sidecar(self, wav_path: Path, text: str) -> None:
        self._sidecar_path(wav_path).write_text(self._text_hash(text), encoding="utf-8")

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
        # Fix 2026-10-11: never reuse a chunk whose audio was synthesized from
        # different text (Smart Delta Restart duplicate bug). Reuse only when the
        # sidecar text-hash matches AND the wav passes the acoustic audit.
        if c_path.exists() and self._sidecar_matches(c_path, c_text):
            is_valid, msg = audit_wav_acoustic(str(c_path), min_size_kb=5, min_rms=0.003, min_peak=0.02)
            if is_valid:
                return str(c_path)
            print(f"  [DELTA REBUILD] Corrupt/silent chunk {item['filename']}: {msg}")
        elif c_path.exists():
            print(f"  [DELTA REBUILD] Text changed for {item['filename']}: stale audio discarded.")
        c_path.unlink(missing_ok=True)
        self._sidecar_path(c_path).unlink(missing_ok=True)

        print(f"  [OMNIVOICE SYNTHESIS] {item['filename']} ({len(c_text.split())} words): '{c_text[:40]}...'")
        self.tts_backend.synthesize(text=c_text, output_path=str(c_path), voice_ref=voice_ref, instruct=None, num_step=self.num_step, seed=self.seed)
        is_valid, msg = audit_wav_acoustic(str(c_path), min_size_kb=1, min_rms=0.003, min_peak=0.02)
        if not is_valid:
            raise RuntimeError(f"Failed GK4 audit for synthesized chunk {item['filename']}: {msg}")
        self._write_sidecar(c_path, c_text)
        return str(c_path)

    def process_part(self, part_num: int, part_text: str, voice_ref: Optional[str] = None) -> str:
        final_part_path = self.parts_dir / f"Part_{part_num:02d}.wav"

        # 1. Smart Delta Top-Level Check (fix 2026-10-11: also verify text hash,
        # so a Part wav stitched from different text is never silently reused)
        if final_part_path.exists() and self._sidecar_matches(final_part_path, part_text):
            is_valid, msg = audit_wav_acoustic(str(final_part_path), min_size_kb=50, min_rms=0.003, min_peak=0.02)
            if is_valid:
                print(f"[SMART DELTA SKIP] Part_{part_num:02d}.wav already complete & valid: {msg}")
                return str(final_part_path)
            print(f"[REDO] Part_{part_num:02d}.wav failed GK4: {msg}. Re-synthesizing...")
        elif final_part_path.exists():
            print(f"[REDO] Part_{part_num:02d}.wav text changed: stale audio discarded.")
            final_part_path.unlink(missing_ok=True)
            self._sidecar_path(final_part_path).unlink(missing_ok=True)

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
        self._write_sidecar(final_part_path, part_text)

        print(f"[COMPLETED] Part_{part_num:02d}.wav verified GK4: {msg}")
        return str(final_part_path)
