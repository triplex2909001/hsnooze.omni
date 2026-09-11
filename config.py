"""
HistorySnooze Director - Central Configuration Module
Version: 1.2.0 (100% Online Serverless & Colab CLI Edition)
Single Source of Truth (SSOT) compliant configuration for 90-minute sleep documentary pipeline.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, List

# Video Rendering Specifications
WIDTH = 3840
HEIGHT = 2160
FPS = 30
ASPECT_RATIO = "16:9"
RESOLUTION = f"{WIDTH}x{HEIGHT}"

# Ken Burns ASMR Motion Parameters
ZOOM_START = 1.00
ZOOM_MAX = 1.04          # Maximum 4% zoom over 75-90s
INTER_PART_SILENCE_SEC = 5.0  # 5-second silence between parts
INTRA_SENTENCE_SILENCE_SEC = 1.0 # 1.0s silence between sentences
INTER_PARAGRAPH_SILENCE_SEC = 2.0 # 2.0s silence between paragraphs

# Story Structure
TOTAL_PARTS = 15
EXPECTED_MIN_BEATS = 45
EXPECTED_MAX_BEATS = 60
CHUNK_MIN_WORDS = 15
CHUNK_MAX_WORDS = 35

# Google Workspace Integration IDs
PARENT_FOLDER_ID = "1UGkrUFQ62ghj1Lquy1HVsKIYR9nO60zf"  # 'historysnooze posts'
DASHBOARD_SHEET_ID = "1x2tcR4WyHXj_cvHjpPFWNsrtelkimUXJXNTw9hPbVeo"
SSOT_FOLDER_ID = "1aV8nBelLqXclJLScwKx-c4H-GMjtxGX0"
CODE_FOLDER_ID = "1mzeigkeg5vxapdHTQ8wHhYE8Y6gY3se9"

# Pipeline Status Lifecycle Flow
STATUS_FLOW = [
    "Proposed",    # New idea suggested
    "Pending",     # Approved by human, queued for agent execution
    "Script",      # Outline & 15-part script completed
    "Voiceover",   # 15 WAV audio files generated
    "Image",       # 45-60 4K keyframe images generated
    "Video",       # 15 chunks rendered & master video assembled
    "Ready",       # Passed all Gatekeepers (GK1-GK7), QA approved, ready for YouTube upload
    "Done"         # Successfully published to YouTube via Buffer API
]

# Image Generation Execution Modes
IMAGE_MODES = [
    "Automatic",   # Mode 1: Bot/VPS automatically sends prompts to ImageFX & downloads 4K images
    "Manual"       # Mode 2: Human manually generates images from combined_imageprompts.txt & uploads to keyframes/
]

# Online Execution Environments (0% VPS)
ONLINE_EXECUTION_MODES = [
    "github_actions", # 15 parallel matrix jobs on CPU (chunk-level immediate upload to GDrive)
    "google_colab"    # Colab CLI (T4/L4 GPU) sequential Part 1->15 with direct GDrive mount
]

# Voice Generation Execution Modes
VOICE_MODES = [
    "GHA",     # GitHub Actions: 15 parallel matrix jobs, chunk-level generation & immediate sync
    "Colab"    # Google Colab via colab-cli: T4/L4 GPU, sequential Part 1->15 with direct GDrive mount
]
DEFAULT_VOICE_MODE = "GHA"

# Google Sheet Column Schema (A - N)
COLUMNS = {
    "A": "Idea_ID",
    "B": "Historical_Figure",
    "C": "YouTube_Title",
    "D": "Status",
    "E": "GDrive",
    "F": "Outline",
    "G": "Script",
    "H": "Voice_Mode",   # "GHA" vs "Colab" (Default: "GHA")
    "I": "Voiceover",
    "J": "Image_Mode",   # "Automatic" vs "Manual" (Default: "Automatic")
    "K": "Image",
    "L": "Video",
    "M": "YouTube",      # Link YouTube video URL via Buffer API
    "N": "Updated_At"
}

# Gatekeeper Quality Thresholds
GK4_MIN_WAV_SIZE_KB = 10
GK4_RMS_THRESHOLD = 0.003
GK4_PEAK_THRESHOLD = 0.02
GK4_MIN_SEC_PER_WORD = 0.15

GK5_MIN_IMAGE_SIZE_KB = 30
GK7_MIN_VIDEO_DURATION_MIN = 80
GK7_MAX_VIDEO_DURATION_MIN = 95
