"""CLAUDE.md section 4 AI keyword dictionary, shared by the annual-report, announcement and transcript counters."""
import re

SEP = r"[\s\-]*"  # zero allowed: line-break de-hyphenation turns "machine-\nlearning" into "machinelearning"
# Acronyms must be delimited by whitespace or ordinary punctuation (not '*', '¶', '$' from legacy-font garble).
_L = r"(?<![^\s(\[{,;:/\"'“‘-])"
_R = r"(?![^\s)\]},.;:/\"'”’-])"
# Order matters: longer phrases first so a match is counted once (e.g. "generative AI" not also "AI").
TERMS = [
    ("artificial_intelligence", rf"(?i:artificial{SEP}intelligence)"),
    ("machine_learning", rf"(?i:machine{SEP}learning)"),
    ("deep_learning", rf"(?i:deep{SEP}learning)"),
    ("neural_network", rf"(?i:neural{SEP}networks?)"),
    ("nlp_full", rf"(?i:natural{SEP}language{SEP}processing)"),
    ("conversational_ai", rf"(?i:conversational{SEP}ai)\b"),
    ("generative_ai", rf"(?i:generative{SEP}ai)\b"),
    ("genai", r"(?i:\bgen[\s\-]?ai)\b"),
    ("llm_full", rf"(?i:large{SEP}language{SEP}models?)"),
    ("computer_vision", rf"(?i:computer{SEP}vision)"),
    ("rpa_full", rf"(?i:robotic{SEP}process{SEP}automation)"),
    ("predictive_analytics", rf"(?i:predictive{SEP}analytics)"),
    ("chatbot", r"(?i:\bchat[\s\-]?bots?)\b"),
    ("ai_ml", r"(?i:\bai\s*[/\-&]\s*ml)\b"),
    # Acronyms: case-sensitive as written (see docs/spec_changes.md); "LLMS" (loan lifecycle system) excluded.
    ("llm", rf"{_L}LLMs?{_R}"),
    ("nlp", rf"{_L}NLP{_R}"),
    ("rpa", rf"{_L}RPA{_R}"),
    ("ai", r"\bAI\b"),  # standalone uppercase only
]
PATTERN = re.compile("|".join(f"(?P<{k}>{p})" for k, p in TERMS))
EXCLUDE = re.compile(r"(?i:air\s+india)")  # spec false-positive example; removed before matching
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
ACRONYMS = {"llm", "nlp", "rpa"}
LAW_DEGREE = re.compile(r"(?i)\bLL\.?\s?B\b|\bLL\.?\s?M\.?\s+from\b|master\s+of\s+laws?|\blaw\b|universit")
LOWER = re.compile(r"[a-z]")


LIVESTOCK = re.compile(r"(?i)insemination|cattle|livestock|dairy|bovine|veterinar")


def accept(m, text):
    """Drop matches that are not about artificial intelligence.

    Acronyms must sit in ordinary prose: legacy-font Hindi renders as all-caps gibberish (e.g. '*LLMLTLWL4K').
    'AI' meaning artificial insemination (livestock CSR programmes) is dropped.
    """
    if m.lastgroup == "ai":
        return not LIVESTOCK.search(text[max(m.start() - 150, 0): m.end() + 150])
    if m.lastgroup not in ACRONYMS:
        return True
    near = text[max(m.start() - 20, 0): m.end() + 20]
    window = text[max(m.start() - 60, 0): m.end() + 60]
    if len(LOWER.findall(near)) < 6 or len(LOWER.findall(window)) < 15:
        return False
    return not (m.lastgroup == "llm" and LAW_DEGREE.search(window))


def iter_matches(text):
    text = EXCLUDE.sub(" ", text)
    for m in PATTERN.finditer(text):
        if accept(m, text):
            yield m, text


def normalise(text):
    text = text.replace("\u00ad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    return re.sub(r"\s+", " ", text)


def count_terms(text):
    """Return {term: count} over normalised text with the spec exclusions applied."""
    counts = dict.fromkeys([k for k, _ in TERMS], 0)
    for m, _ in iter_matches(text):
        counts[m.lastgroup] += 1
    return counts
