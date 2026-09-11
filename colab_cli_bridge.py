"""
HISTORYSNOOZE: COLAB-CLI BRIDGE MODULE
Module: colab_cli_bridge.py
Version: 1.2.0
Purpose:
  - Programmatic wrapper for official Google Colab CLI (`google-colab-cli`).
  - Allows AI agents and pipeline orchestrator to provision GPU VMs (T4/L4/A100) on Colab,
    mount Google Drive, execute voiceover/rendering scripts remotely, and clean up.
"""

import os
import sys
import shutil
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path


def is_colab_cli_available() -> bool:
    """Checks whether the official `colab` CLI executable is in PATH."""
    return shutil.which("colab") is not None


def run_colab_ephemeral(script_path: str, script_args: list = None, gpu: str = "T4", timeout_sec: int = 1800) -> Dict[str, Any]:
    """
    Executes a script on an ephemeral Colab VM using `colab run`.
    Provisions a fresh VM, runs the script, and releases the VM automatically.
    
    Usage:
        res = run_colab_ephemeral("colab_voiceover_runner.py", ["--project-path", "/content/drive/MyDrive/..."])
    """
    if not is_colab_cli_available():
        raise RuntimeError("colab CLI not found in PATH. Install via 'uv tool install google-colab-cli' or 'pip install google-colab-cli'.")

    cmd = ["colab", "run", "--gpu", gpu, "--timeout", str(float(timeout_sec)), script_path]
    if script_args:
        cmd.extend(script_args)

    print(f"[COLAB-CLI] Launching ephemeral VM ({gpu})...")
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
    if not is_colab_cli_available():
        raise RuntimeError("colab CLI not found in PATH.")

    print(f"[COLAB-CLI] Creating session '{session_name}' with GPU {gpu}...")
    subprocess.run(["colab", "new", "-s", session_name, "--gpu", gpu], check=True)

    try:
        print(f"[COLAB-CLI] Mounting Google Drive in session '{session_name}'...")
        subprocess.run(["colab", "drivemount", "-s", session_name], check=True)

        print(f"[COLAB-CLI] Executing script '{script_path}' in session '{session_name}'...")
        exec_cmd = ["colab", "exec", "-s", session_name, "-f", script_path]
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
        subprocess.run(["colab", "stop", "-s", session_name])


def trigger_colab_voiceover(project_folder_name: str, voice_ref: str = None, gpu: str = "T4") -> Dict[str, Any]:
    """
    High-level trigger called by pipeline orchestrator when Voice_Mode is 'Colab'.
    """
    drive_project_path = f"/content/drive/MyDrive/historysnooze posts/{project_folder_name}"
    script_path = "colab_voiceover_runner.py"
    
    args = ["--project-path", drive_project_path]
    if voice_ref:
        args.extend(["--voice-ref", voice_ref])
        
    return run_colab_ephemeral(script_path=script_path, script_args=args, gpu=gpu)


if __name__ == "__main__":
    print("Checking colab CLI availability...")
    avail = is_colab_cli_available()
    print(f"colab-cli installed: {avail} ({shutil.which('colab')})")
    if len(sys.argv) > 1 and avail:
        proj_name = sys.argv[1]
        trigger_colab_voiceover(proj_name)
