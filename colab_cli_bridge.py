"""
HISTORYSNOOZE: COLAB-CLI BRIDGE MODULE
Module: colab_cli_bridge.py
Version: 1.4.0
Purpose:
  - Programmatic wrapper for official Google Colab CLI (`colab`).
  - Allows AI agents and pipeline orchestrator to provision GPU VMs (T4/L4/A100) on Colab,
    mount Google Drive, execute voiceover/rendering scripts remotely, and clean up.
  - Supports selective parts processing (--parts 1,2,3), sampling steps (--num-step), and Milo voice cloning.
"""

import os
import sys
import shutil
import subprocess
import time
from typing import Dict, Any, Optional, List
from pathlib import Path


def get_colab_executable() -> Optional[str]:
    """Returns absolute path to `colab` CLI executable."""
    colab_path = shutil.which("colab")
    if colab_path:
        return colab_path
    user_local = os.path.expanduser("~/.local/bin/colab")
    if os.path.exists(user_local):
        return user_local
    return None


def is_colab_cli_available() -> bool:
    """Checks whether the official `colab` CLI executable is available."""
    return get_colab_executable() is not None


def run_colab_ephemeral(script_path: str, script_args: list = None, gpu: str = "T4", timeout_sec: int = 3600) -> Dict[str, Any]:
    """
    Executes a script on an ephemeral Colab VM using `colab run`.
    Provisions a fresh VM, mounts Drive, runs the script, and releases the VM automatically.
    """
    colab_bin = get_colab_executable()
    if not colab_bin:
        raise RuntimeError("colab CLI not found in PATH or ~/.local/bin/colab.")

    cmd = [colab_bin, "run", "--gpu", gpu, "--timeout", str(float(timeout_sec)), script_path]
    if script_args:
        cmd.extend(script_args)

    print(f"[COLAB-CLI] Launching ephemeral VM (GPU: {gpu})...")
    print(f"[COLAB-CLI] Command: {' '.join(cmd)}")
    
    start_time = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    success = (proc.returncode == 0)
    print(f"[COLAB-CLI] Finished in {duration:.1f}s (Exit code: {proc.returncode})")
    
    return {
        "success": success,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_sec": duration
    }


def run_colab_session(script_path: str, script_args: list = None, gpu: str = "T4", session_name: str = "hsnooze-worker") -> Dict[str, Any]:
    """
    Runs a job using an explicit Colab session with native Google Drive mount:
    1. colab new -s <session_name> --gpu <gpu>
    2. colab drivemount -s <session_name>
    3. colab exec -s <session_name> -f <script_path> <script_args>
    4. colab stop -s <session_name>
    """
    colab_bin = get_colab_executable()
    if not colab_bin:
        raise RuntimeError("colab CLI not found in PATH.")

    print(f"[COLAB-CLI] Creating session '{session_name}' with GPU {gpu}...")
    subprocess.run([colab_bin, "new", "-s", session_name, "--gpu", gpu], check=True)

    try:
        print(f"[COLAB-CLI] Mounting Google Drive in session '{session_name}'...")
        subprocess.run([colab_bin, "drivemount", "-s", session_name], check=True)

        print(f"[COLAB-CLI] Executing script '{script_path}' in session '{session_name}'...")
        exec_cmd = [colab_bin, "exec", "-s", session_name, "-f", script_path]
        if script_args:
            exec_cmd.extend(script_args)
            
        res = subprocess.run(exec_cmd, capture_output=True, text=True)
        print(f"[COLAB-CLI] Execution output:\n{res.stdout}")
        if res.stderr:
            print(f"[COLAB-CLI] Errors:\n{res.stderr}")
            
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout,
            "stderr": res.stderr
        }
    finally:
        print(f"[COLAB-CLI] Stopping session '{session_name}' to release resources...")
        subprocess.run([colab_bin, "stop", "-s", session_name])


def trigger_colab_voiceover(
    project_folder_name: str,
    parts: Optional[str] = None,
    voice_ref: Optional[str] = None,
    gpu: str = "T4",
    num_step: int = 16
) -> Dict[str, Any]:
    """
    High-level trigger called by pipeline orchestrator when Voice_Mode is 'Colab'.
    """
    drive_project_path = f"/content/drive/MyDrive/historysnooze posts/{project_folder_name}"
    script_path = "colab_voiceover_runner.py"
    
    args = ["--project-dir", drive_project_path, "--num-step", str(num_step)]
    if parts:
        args.extend(["--parts", parts])
    if voice_ref:
        args.extend(["--voice-ref", voice_ref])
        
    return run_colab_ephemeral(script_path=script_path, script_args=args, gpu=gpu)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HistorySnooze Colab CLI Bridge v1.4.0")
    parser.add_argument("--project-name", type=str, help="Name of project folder on Drive")
    parser.add_argument("--parts", type=str, default=None, help="Comma-separated parts to run (e.g. '1,2,3')")
    parser.add_argument("--gpu", type=str, default="T4", help="Colab GPU accelerator (T4, L4, A100)")
    parser.add_argument("--num-step", type=int, default=16, help="Sampling steps (default: 16)")
    parser.add_argument("--check", action="store_true", help="Check colab CLI availability")
    args = parser.parse_args()

    colab_bin = get_colab_executable()
    print(f"Colab CLI Available: {colab_bin is not None} (Path: {colab_bin})")

    if args.project_name:
        trigger_colab_voiceover(
            project_folder_name=args.project_name,
            parts=args.parts,
            gpu=args.gpu,
            num_step=args.num_step
        )
