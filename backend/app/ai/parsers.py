"""Strict JSON parsers for AnthropicVertex responses (the AI output boundary).

Every parser raises AIFormatError when the raw text violates its contract, so
bad AI output surfaces as a 502 at the API boundary instead of corrupting
state.
"""

import json
import re

from app.ai.client import ExpertNoteDraft, LensDraft, ParagraphDraft, ToneSampleDraft
from app.errors import AIFormatError

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(raw: str) -> object:
    text = raw.strip()
    fenced = _FENCE_RE.search(text)
    if fenced is not None:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        start = next((i for i, ch in enumerate(text) if ch in "[{"), None)
        end = max(text.rfind("]"), text.rfind("}"))
        if start is None or end <= start:
            raise AIFormatError("AI response is not valid JSON") from err
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError as nested_err:
            raise AIFormatError("AI response is not valid JSON") from nested_err


def _require_list(obj: object, what: str) -> list[object]:
    if not isinstance(obj, list):
        raise AIFormatError(f"expected a JSON array of {what}, got {type(obj).__name__}")
    return obj


def _require_object(obj: object, what: str) -> dict[str, object]:
    if not isinstance(obj, dict):
        raise AIFormatError(f"expected a JSON object for {what}, got {type(obj).__name__}")
    return obj


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AIFormatError(f"AI response entry has no non-empty {field}")
    return value.strip()


def parse_lenses(raw: str) -> list[LensDraft]:
    items = _require_list(extract_json(raw), "lens proposals")
    drafts: list[LensDraft] = []
    for item in items:
        obj = _require_object(item, "lens proposal")
        drafts.append(
            LensDraft(
                title=_text(obj.get("title"), "title"),
                rationale=_text(obj.get("rationale"), "rationale"),
            )
        )
    if not drafts:
        raise AIFormatError("AI proposed no lenses")
    return drafts


def parse_expert_notes(raw: str) -> list[ExpertNoteDraft]:
    items = _require_list(extract_json(raw), "expert notes")
    drafts: list[ExpertNoteDraft] = []
    for item in items:
        if isinstance(item, str):
            drafts.append(ExpertNoteDraft(content=_text(item, "note content")))
            continue
        obj = _require_object(item, "expert note")
        drafts.append(ExpertNoteDraft(content=_text(obj.get("content"), "note content")))
    if not drafts:
        raise AIFormatError("AI expert produced no notes")
    return drafts


def parse_report(raw: str) -> list[ParagraphDraft]:
    obj = extract_json(raw)
    items = obj.get("paragraphs") if isinstance(obj, dict) else obj
    drafts: list[ParagraphDraft] = []
    for item in _require_list(items, "report paragraphs"):
        if isinstance(item, str):
            drafts.append(ParagraphDraft(text=_text(item, "paragraph")))
            continue
        block = _require_object(item, "report paragraph")
        text = _text(block.get("paragraph"), "paragraph")
        raw_ids = block.get("source_entry_ids", [])
        entry_ids: list[int] = []
        if isinstance(raw_ids, list):
            entry_ids = [
                int(i)
                for i in raw_ids
                if isinstance(i, int) or (isinstance(i, str) and i.strip().isdigit())
            ]
        drafts.append(ParagraphDraft(text=text, source_entry_ids=tuple(entry_ids)))
    if not drafts:
        raise AIFormatError("AI report generation produced no paragraphs")
    return drafts


def parse_tone_samples(raw: str) -> list[ToneSampleDraft]:
    items = _require_list(extract_json(raw), "tone samples")
    if len(items) != 5:
        raise AIFormatError(f"expected exactly 5 tone samples, got {len(items)}")
    drafts: list[ToneSampleDraft] = []
    for item in items:
        obj = _require_object(item, "tone sample")
        drafts.append(
            ToneSampleDraft(
                tone=_text(obj.get("tone"), "tone"), text=_text(obj.get("text"), "sample text")
            )
        )
    labels = [d.tone.casefold() for d in drafts]
    if len(set(labels)) != len(labels):
        raise AIFormatError("tone samples do not have distinct tones")
    return drafts


def parse_critique(raw: str) -> str:
    obj = _require_object(extract_json(raw), "critique")
    return _text(obj.get("critique"), "critique")
