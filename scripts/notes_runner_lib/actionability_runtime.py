from __future__ import annotations

import re


ACTION_VERB_STARTERS = (
    "сделай",
    "проверь",
    "зафиксируй",
    "запиши",
    "определи",
    "выбери",
    "сравни",
    "найди",
    "ответь",
    "сформулируй",
    "вернись",
    "ограничь",
    "убери",
    "избегай",
    "попробуй",
    "скажи",
    "спроси",
    "не",
    "опиши",
    "собери",
    "усиль",
    "оставь",
    "создай",
    "выпиши",
    "раздели",
    "отдели",
    "сверь",
    "перепиши",
    "сократи",
    "почини",
    "очисти",
    "задай",
    "поставь",
    "преврати",
    "проведи",
)
ACTION_VERB_RE = re.compile(
    r"^(?:" + "|".join(re.escape(item) for item in ACTION_VERB_STARTERS) + r")\b",
    re.IGNORECASE,
)
QUESTION_WORDS = {
    "кто",
    "что",
    "где",
    "когда",
    "зачем",
    "почему",
    "как",
    "какие",
    "какой",
    "какая",
    "какое",
    "каким",
    "какими",
    "какую",
    "сколько",
    "чего",
    "кому",
    "кем",
    "чем",
}


def normalize_action_candidate_text(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    text = re.sub(r"^\*\*[^*]+\*\*\s*:?\s*", "", text)
    text = re.sub(r"^[—–-]\s*", "", text)
    text = re.sub(r"\s*\*\([^)]+\)\*\s*$", "", text)
    text = text.rstrip(".").strip()
    if not text:
        return ""
    if ":" in text:
        prefix, suffix = text.split(":", 1)
        prefix_lower = prefix.lower()
        if not ACTION_VERB_RE.match(prefix_lower) and any(
            marker in prefix_lower
            for marker in ("вопрос", "метод", "совет", "критерий", "практик", "диагност", "вывод", "предупреждение")
        ):
            suffix = re.sub(r"\s+", " ", suffix.strip().strip("«»\""))
            if suffix:
                text = suffix
    return text.strip().strip("«»\"").rstrip(".")


def is_verbish_action(text: str) -> bool:
    normalized = normalize_action_candidate_text(text)
    return bool(normalized and ACTION_VERB_RE.match(normalized))


def imperative_action_text(value: str) -> str:
    text = normalize_action_candidate_text(value)
    if not text:
        return ""
    if is_verbish_action(text):
        return text
    first = text.split(" ", 1)[0].strip("«»\".,:;!?").casefold()
    if text.endswith("?") or first in QUESTION_WORDS:
        return f"Проверь: {text}"
    lowered = text.casefold()
    for token, prefix in (
        ("перв", "Зафиксируй "),
        ("вопрос", "Проверь: "),
        ("мысл", "Запиши мысль: "),
        ("страх", "Проверь страх: "),
        ("роль", "Определи роль: "),
        ("блокир", "Найди блокирующую мысль: "),
    ):
        if token in lowered:
            return prefix + text[0].lower() + text[1:] if text else ""
    return text


__all__ = [
    "ACTION_VERB_RE",
    "ACTION_VERB_STARTERS",
    "QUESTION_WORDS",
    "imperative_action_text",
    "is_verbish_action",
    "normalize_action_candidate_text",
]
