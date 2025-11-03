from __future__ import annotations
from typing import List, Dict, Tuple
import re

# Legal-aware preprocessing and splitting utilities

_AMENDMENT_PAT = re.compile(r"\b(Ins\.|Subs\.|Amended|Inserted|Omitted)\s+by\b.*?(?:\.|\])", re.IGNORECASE)
_HEADER_FOOTER_CLUES = (
    "THE CONSTITUTION OF INDIA",
    "THE CONSTITUTION OF",  # generic header
    "(Part ",
)


def preprocess_legal_text(text: str) -> str:
    """Normalize whitespace and strip common non-substantive noise.

    - Collapses multiple spaces/newlines
    - Joins broken lines where a newline splits a sentence
    - Removes common amendment notes like "Ins. by ..." / "Subs. by ..."
    - Drops obvious header/footer lines by clue words
    """
    t = text or ""
    # Remove amendment notes (best-effort, conservative)
    t = _AMENDMENT_PAT.sub(" ", t)
    # Remove likely header/footer lines
    lines = []
    for line in t.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(clue in stripped for clue in _HEADER_FOOTER_CLUES):
            # keep only if it also contains Article/Section words (to avoid deleting headings)
            if not re.search(r"\b(Article|Section|Chapter|Part)\b", stripped, re.IGNORECASE):
                continue
        lines.append(stripped)
    t = "\n".join(lines)
    # Hyphenation at line wrap: e.g., "consti-\ntution" -> "constitution"
    t = re.sub(r"-\n\s*", "", t)
    # Join lines that likely belong to the same sentence (line break without terminal punctuation)
    t = re.sub(r"(?<![\.!?:;])\n(?!\n)", " ", t)
    # Normalize whitespace
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    return t


_PART_RE = re.compile(r"\bPart\s+([IVXLCDM]+|\d+)\b", re.IGNORECASE)
_CHAPTER_RE = re.compile(r"\bChapter\s+([IVXLCDM]+|\d+)\b(?:\s*[-–—:]\s*(.*))?", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"\bArticle\s+(\d+[A-Z]?)\b(?:\s*[-–—:]\s*(.*))?", re.IGNORECASE)
_SECTION_RE = re.compile(r"\bSection\s+(\d+[A-Z]?)\b(?:\s*[-–—:]\s*(.*))?", re.IGNORECASE)


def parse_legal_units(text: str) -> List[Dict]:
    """Parse text into legal units (Part/Chapter/Article/Section) with headings.

    Returns a list of dicts: {unit_type, identifier, heading, part, chapter, text}
    """
    units: List[Dict] = []
    current: Dict | None = None
    part = None
    chapter = None

    # Work line-by-line to detect headings
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Update part/chapter if encountered
        m_part = _PART_RE.search(line)
        if m_part:
            part = m_part.group(1)
        m_ch = _CHAPTER_RE.search(line)
        if m_ch:
            chapter = m_ch.group(1)

        # Article heading
        m_art = _ARTICLE_RE.search(line)
        if m_art:
            if current:
                units.append(current)
            current = {
                "unit_type": "Article",
                "identifier": m_art.group(1),
                "heading": (m_art.group(2) or "").strip(),
                "part": part,
                "chapter": chapter,
                "text": "",
            }
            continue

        # Section heading
        m_sec = _SECTION_RE.search(line)
        if m_sec:
            if current:
                units.append(current)
            current = {
                "unit_type": "Section",
                "identifier": m_sec.group(1),
                "heading": (m_sec.group(2) or "").strip(),
                "part": part,
                "chapter": chapter,
                "text": "",
            }
            continue

        # Accumulate body
        if current is None:
            # Start a generic unit until we find a formal heading
            current = {
                "unit_type": "Prose",
                "identifier": None,
                "heading": "",
                "part": part,
                "chapter": chapter,
                "text": line,
            }
        else:
            current["text"] = (current["text"] + " " + line).strip()

    if current:
        units.append(current)
    # Remove empty units
    units = [u for u in units if (u.get("text") or "").strip()]
    return units


def _sentence_split(text: str) -> List[str]:
    return re.split(r"(?<=[\.!?])\s+", text.strip())


def chunk_units(units: List[Dict], target_chars: int = 1600, overlap: int = 200) -> List[Tuple[str, Dict]]:
    """Chunk parsed legal units into approximately section-sized chunks.

    Returns list of (chunk_text, meta) tuples. meta includes unit info.
    """
    out: List[Tuple[str, Dict]] = []
    for u in units:
        body = (u.get("text") or "").strip()
        if not body:
            continue
        if len(body) <= target_chars:
            meta = {k: u.get(k) for k in ("unit_type", "identifier", "heading", "part", "chapter")}
            out.append((body, meta))
            continue
        # Split long unit by sentences with overlap
        sentences = _sentence_split(body)
        cur = ""
        for s in sentences:
            if len(cur) + len(s) + 1 <= target_chars:
                cur = (cur + " " + s).strip()
            else:
                if cur:
                    meta = {k: u.get(k) for k in ("unit_type", "identifier", "heading", "part", "chapter")}
                    out.append((cur, meta))
                # overlap
                if overlap > 0 and cur:
                    o = cur[-overlap:]
                else:
                    o = ""
                cur = (o + (" " if o else "") + s).strip()
        if cur:
            meta = {k: u.get(k) for k in ("unit_type", "identifier", "heading", "part", "chapter")}
            out.append((cur, meta))
    return out


# Backwards-compatible simple splitter (used as fallback)
def split_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> List[str]:
    text = text.strip()
    if not text:
        return []
    sentences = _sentence_split(text)
    chunks: List[str] = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= chunk_size:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            overlap = chunks[-1][-chunk_overlap:] if (chunk_overlap > 0 and chunks) else ""
            current = (overlap + (" " if overlap else "") + s).strip()
    if current:
        chunks.append(current)
    final: List[str] = []
    for c in chunks:
        if len(c) <= chunk_size:
            final.append(c)
        else:
            for i in range(0, len(c), chunk_size - chunk_overlap):
                final.append(c[i : i + (chunk_size - chunk_overlap)])
    return final


# Procedural/Reasoning tags for retrieval
_PROCEDURE_PATTERNS = [
    r"\bprocedure\b",
    r"\bprocedures\b",
    r"\bsafeguard(s)?\b",
    r"\breasons? to be recorded in writing\b",
    r"\bby order\b",
    r"\bsubject to the provisions of sub-section\b",
    r"\brules may be prescribed\b",
    r"\bintercept(ion|ing)?\b",
    r"\bmonitor(ing)?\b",
    r"\bdecrypt(ion|ing)?\b",
    r"\bblock(ing)?\b",
]


def derive_procedural_tags(text: str, unit_type: str | None, identifier: str | None, title: str | None) -> List[str]:
    """Heuristically derive retrieval tags for procedures/rules and link hints.

    - Adds generic tags like 'procedure', 'safeguard', 'blocking', 'interception' based on patterns.
    - Adds specific tags for well-known sections, e.g., IT Act 69A -> 'blocking', 'procedure', '69A'.
    """
    t = (text or "").lower()
    title_l = (title or "").lower()
    tags: List[str] = []

    # Generic procedure tags
    for pat in _PROCEDURE_PATTERNS:
        if re.search(pat, t):
            if "procedure" in pat and "procedure" not in tags:
                tags.append("procedure")
            if "safeguard" in pat and "safeguard" not in tags:
                tags.append("safeguard")
            if "block" in pat and "blocking" not in tags:
                tags.append("blocking")
            if any(k in pat for k in ["intercept", "monitor", "decrypt"]) and "interception" not in tags:
                tags.append("interception")

    uid = (identifier or "").upper()
    # Specific: IT Act 69 and 69A
    if unit_type == "Section" and ("information technology" in title_l or "it act" in title_l):
        if uid == "69A":
            for tg in ("blocking", "procedure", "public-order", "69A"):
                if tg not in tags:
                    tags.append(tg)
        if uid == "69":
            for tg in ("interception", "procedure", "69"):
                if tg not in tags:
                    tags.append(tg)

    return tags

