"""
HistorySnooze: Single Part Colab Worker
Executes synthesis for a single part on Colab GPU, immediately downloads to local attachments, and audits GK4.
"""

import sys
import os
import argparse
import subprocess
import wave
import numpy as np
from pathlib import Path

COLAB_CLI = os.path.expanduser("~/.local/bin/colab")
SESSION = "hsnooze-voice"
ATTACHMENTS_DIR = Path("/Users/hanario/.workspace-mcp/attachments")
SCRATCH_DIR = Path("/Users/hanario/.gemini/antigravity/brain/088cad0e-2171-40da-9f7f-2ae086579b89/scratch/basho_production")

def audit_wav_acoustic(filepath: str, min_size_kb: float = 50.0, min_rms: float = 0.003, min_peak: float = 0.02):
    path = Path(filepath)
    if not path.exists():
        return False, f"File {path.name} does not exist"
    
    size_kb = path.stat().st_size / 1024.0
    if size_kb < min_size_kb:
        return False, f"Size too small: {size_kb:.1f} KB < {min_size_kb} KB"
    
    try:
        with wave.open(str(path), 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            duration_sec = n_frames / float(framerate)
            raw_data = wf.readframes(n_frames)
            
        if sampwidth == 2:
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            data = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            return False, f"Unsupported sample width: {sampwidth}"
        
        rms = float(np.sqrt(np.mean(data ** 2)))
        peak = float(np.max(np.abs(data)))
        
        if rms < min_rms:
            return False, f"Audio too quiet: RMS={rms:.4f} < {min_rms}"
        if peak < min_peak:
            return False, f"Peak amplitude too low: Peak={peak:.4f} < {min_peak}"
        if peak > 1.05:
            return False, f"Audio clipping detected: Peak={peak:.4f} > 1.0"
        
        return True, f"Valid WAV ({duration_sec:.1f}s, {size_kb:.1f}KB, RMS={rms:.4f}, Peak={peak:.4f}, SR={framerate}Hz)"
    except Exception as e:
        return False, f"Failed acoustic audit: {e}"

def run_single_part(part_num: int):
    part_fname = f"Part_{part_num:02d}.wav"
    remote_wav = f"/content/basho_project/02. Media Generation/audio/{part_fname}"
    local_attachment = ATTACHMENTS_DIR / part_fname
    local_scratch = SCRATCH_DIR / part_fname

    print(f"\n{'='*30} EXECUTING PART {part_num:02d}/15 ON COLAB GPU {'='*30}")
    
    # 1. Create remote trigger script
    trigger_code = f"""
from colab_voiceover_runner import run_pipeline
print('Starting Part {part_num} on GPU...')
run_pipeline(
    project_folder_path='/content/basho_project',
    voice_ref_path='/content/voice_preview_milo.mp3',
    parts_to_process=[{part_num}],
    num_step=16
)
print('Finished Part {part_num}!')
"""
    trigger_file = SCRATCH_DIR / f"run_p{part_num}.py"
    with open(trigger_file, "w") as f:
        f.write(trigger_code.strip() + "\n")

    # 2. Execute on Colab
    print(f"Sending execution command to Colab session '{SESSION}' (timeout: 480s)...")
    exec_res = subprocess.run(
        [COLAB_CLI, "exec", "-s", SESSION, "--timeout", "480.0", "-f", str(trigger_file)],
        capture_output=True, text=True
    )
    print(exec_res.stdout)
    if exec_res.returncode != 0:
        print(f"[ERROR in exec] {exec_res.stderr}")
        sys.exit(1)

    # 3. Download immediately
    print(f"Downloading {part_fname} from Colab session '{SESSION}'...")
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    dl_res = subprocess.run(
        [COLAB_CLI, "download", "-s", SESSION, remote_wav, str(local_attachment)],
        capture_output=True, text=True
    )
    if dl_res.returncode != 0 or not local_attachment.exists():
        print(f"[DOWNLOAD FAILED] {dl_res.stderr}")
        sys.exit(1)

    # Copy to scratch
    import shutil
    shutil.copy2(local_attachment, local_scratch)

    # 4. Audit GK4
    is_valid, msg = audit_wav_acoustic(str(local_attachment))
    print(f"[GK4 AUDIT] {part_fname}: {msg}")
    if not is_valid:
        print(f"[GK4 FAILED] Part {part_num} violated GK4 acoustics!")
        sys.exit(1)

    print(f"🎉 [SUCCESS] Part {part_num:02d} ready for instant GDrive upload! Local path: {local_attachment}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, required=True)
    args = parser.parse_args()
    run_single_part(args.part)
