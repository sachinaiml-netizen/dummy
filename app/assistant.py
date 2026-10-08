from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class KnowledgeDoc:
    name: str
    text: str


DEFAULT_DOCS = [
    KnowledgeDoc(
        name="Project Handbook",
        text=(
            "Project managers should review schedule variance, vendor delays, open issues, "
            "budget variance, and quality defects before every milestone. Escalate a project "
            "when schedule slippage and vendor delays occur together. Weekly project reviews "
            "should record blockers, owners, due dates, and recovery actions."
        ),
    ),
    KnowledgeDoc(
        name="Vendor Policy",
        text=(
            "Critical vendor delays should be reviewed within one business day. The project "
            "owner should confirm the dependency, request a recovery date, and document the "
            "impact on the milestone plan. Repeated delays should trigger escalation."
        ),
    ),
    KnowledgeDoc(
        name="Quality Checklist",
        text=(
            "Inspection defects should be logged with location, severity, owner, and target "
            "closure date. Repeated defects in the same work package should trigger a quality "
            "review before the next milestone is accepted."
        ),
    ),
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def answer_query(query: str, docs: list[KnowledgeDoc]) -> dict:
    query_tokens = _tokens(query)
    ranked: list[tuple[int, KnowledgeDoc]] = []

    for doc in docs:
        score = len(query_tokens & _tokens(doc.text))
        if score:
            ranked.append((score, doc))

    ranked.sort(key=lambda item: item[0], reverse=True)

    if not ranked:
        return {
            "answer": "I could not find that information in the uploaded knowledge base.",
            "sources": [],
            "confidence": 0.0,
        }

    top_score, top_doc = ranked[0]
    sentences = re.split(r"(?<=[.!?])\s+", top_doc.text)
    relevant = [
        sentence for sentence in sentences
        if query_tokens & _tokens(sentence)
    ]
    answer = " ".join(relevant[:2]) or top_doc.text[:450]
    confidence = min(0.95, 0.35 + (top_score / max(len(query_tokens), 1)) * 0.6)

    return {
        "answer": answer,
        "sources": [doc.name for _, doc in ranked[:3]],
        "confidence": round(confidence, 2),
    }
