"""
Script Sanitization and Sentence Chunk Splitting Submodule.
Adheres to Documents/Structure/01_ARCHITECTURE_CONSTRAINED_AI.md (Rule <= 150 lines/file).
"""

import re
from typing import List


def split_into_paragraphs(text: str) -> List[str]:
    """Splits raw script text into paragraphs by double newlines."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def split_paragraph_into_sentences(paragraph: str, max_words: int = 35) -> List[str]:
    """
    Splits a paragraph into short, natural spoken sentences (15-30 words).
    Respects ellipses (...), periods, question marks, and exclamation points.
    If a sentence is too long, splits on natural pause markers (commas, semicolons).
    """
    text = paragraph.replace("...", " <ELLIPSIS> ")
    raw_sentences = re.split(r'(?<=[.?!])\s+', text)

    sentences = []
    for s in raw_sentences:
        s = s.replace("<ELLIPSIS>", "...").strip()
        if not s:
            continue

        words = s.split()
        if len(words) <= max_words:
            sentences.append(s)
        else:
            sub_clauses = re.split(r'(?<=[,;])\s+', s)
            current_clause = []
            for clause in sub_clauses:
                current_clause.append(clause)
                if len(" ".join(current_clause).split()) >= 18:
                    sentences.append(" ".join(current_clause).strip())
                    current_clause = []
            if current_clause:
                sentences.append(" ".join(current_clause).strip())

    return sentences


def clean_voiceover_script(raw_script: str) -> str:
    """
    Sanitizes raw script text to guarantee zero headings, markdown formatting,
    or structural notes leak into the voiceover audio.
    """
    lines = raw_script.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"^ACT\s+[I|V|X\d]+", stripped, re.IGNORECASE):
            continue
        if re.match(r"^Part\s+\d+", stripped, re.IGNORECASE):
            continue
        if re.match(r"^h\.[a-z0-9]+", stripped):
            continue
        if re.match(r"^\(Words?:?\s*\d+\)", stripped, re.IGNORECASE):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        line_clean = re.sub(r"\[.*?\]", "", line)
        line_clean = re.sub(r"^[\*\-\_]{3,}\s*$", "", line_clean)
        line_clean = re.sub(r"[\*\_\#]", "", line_clean)
        cleaned_lines.append(line_clean)
    return "\n".join(cleaned_lines).strip()
