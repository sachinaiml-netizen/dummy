from __future__ import annotations

import os
import re
from dataclasses import dataclass

from openai import OpenAI


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


def _rank_docs(query: str, docs: list[KnowledgeDoc]) -> list[tuple[int, KnowledgeDoc]]:
    query_tokens = _tokens(query)
    ranked: list[tuple[int, KnowledgeDoc]] = []
    for doc in docs:
        score = len(query_tokens & _tokens(doc.text))
        if score:
            ranked.append((score, doc))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def _fallback_answer(query: str, ranked: list[tuple[int, KnowledgeDoc]]) -> dict:
    query_tokens = _tokens(query)
    if not ranked:
        return {
            "answer": "I could not find that information in the uploaded knowledge base.",
            "sources": [],
            "confidence": 0.0,
            "mode": "retrieval",
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
        "mode": "retrieval",
    }


def answer_query(query: str, docs: list[KnowledgeDoc]) -> dict:
    ranked = _rank_docs(query, docs)
    if not ranked:
        return _fallback_answer(query, ranked)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_answer(query, ranked)

    selected = [doc for _, doc in ranked[:4]]
    context = "\n\n".join(
        f"SOURCE: {doc.name}\n{doc.text[:5000]}" for doc in selected
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            instructions=(
                "You are a document-grounded business knowledge assistant. "
                "Answer only from the supplied source text. Be concise and practical. "
                "If the source text does not support the answer, say that clearly. "
                "Do not invent policies, dates, people, metrics, or procedures."
            ),
            input=(
                f"Question:\n{query}\n\n"
                f"Source material:\n{context}\n\n"
                "Return a direct answer in plain text."
            ),
        )
        text = (response.output_text or "").strip()
        if not text:
            return _fallback_answer(query, ranked)

        return {
            "answer": text,
            "sources": [doc.name for doc in selected],
            "confidence": 0.9,
            "mode": "openai",
        }
    except Exception:
        return _fallback_answer(query, ranked)
