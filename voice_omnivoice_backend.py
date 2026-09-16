"""
OmniVoice Zero-Shot TTS Model Integration Backend.
GitHub: https://github.com/k2-fsa/OmniVoice
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import os
from typing import Optional


class OmniVoiceBackend:
    """
    Official backend integrating k2-fsa/OmniVoice zero-shot TTS model.
    Output: 24,000 Hz, 16-bit PCM WAV.
    """
    def __init__(self, device: Optional[str] = None, model_id: str = "k2-fsa/OmniVoice"):
        self.device = device
        self.model_id = model_id
        self.model = None
        self.sampling_rate = 24000
        self.cached_prompts = {}
        self._load_model()

    def _load_model(self):
        import torch
        from omnivoice import OmniVoice

        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda:0"
                self.dtype = torch.float16
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
                self.dtype = torch.float32
            else:
                self.device = "cpu"
                self.dtype = torch.float32
        else:
            self.dtype = torch.float16 if "cuda" in self.device else torch.float32

        print(f"[OmniVoice] Loading {self.model_id} on {self.device} ({self.dtype})...")
        self.model = OmniVoice.from_pretrained(self.model_id, device_map=self.device, dtype=self.dtype)
        self.sampling_rate = getattr(self.model, "sampling_rate", 24000)
        print(f"[OmniVoice] Model loaded successfully! Native Sampling Rate: {self.sampling_rate} Hz")

    def get_or_create_clone_prompt(self, voice_ref: str):
        """Pre-encodes VoiceClonePrompt once from reference audio to avoid re-running Whisper."""
        if voice_ref not in self.cached_prompts:
            print(f"[OmniVoice] Pre-encoding VoiceClonePrompt for: {voice_ref}...")
            prompt = self.model.create_voice_clone_prompt(ref_audio=voice_ref)
            self.cached_prompts[voice_ref] = prompt
            print(f"[OmniVoice] VoiceClonePrompt created and cached successfully!")
        return self.cached_prompts[voice_ref]

    def synthesize(self, text: str, output_path: str, voice_ref: Optional[str] = None, instruct: Optional[str] = None, num_step: int = 10):
        """Synthesizes speech using k2-fsa/OmniVoice zero-shot voice cloning."""
        import soundfile as sf
        import torch

        kwargs = {"text": text, "language": "en", "num_step": num_step}
        if voice_ref and os.path.exists(voice_ref):
            kwargs["voice_clone_prompt"] = self.get_or_create_clone_prompt(voice_ref)
        elif instruct:
            kwargs["instruct"] = instruct

        audio = self.model.generate(**kwargs)
        if isinstance(audio, torch.Tensor):
            audio_np = audio.squeeze().cpu().float().numpy()
        elif isinstance(audio, (list, tuple)):
            first = audio[0]
            audio_np = first.squeeze().cpu().float().numpy() if isinstance(first, torch.Tensor) else first
        else:
            audio_np = audio

        sf.write(output_path, audio_np, self.sampling_rate)
