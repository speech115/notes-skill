from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable


SUMMARY_LINE_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.+?)\s*$")
SOURCE_NAME_RE = re.compile(r"меня зовут\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2})", re.IGNORECASE)
LATIN_AI_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9+-]*)\s+AI\b")
CYRILLIC_AI_RE = re.compile(r"\bИИ\b", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9+-]*")
TITLE_ENDINGS = (
    "иями",
    "ями",
    "ами",
    "его",
    "ого",
    "ему",
    "ому",
    "ыми",
    "ими",
    "ии",
    "ия",
    "ие",
    "ый",
    "ий",
    "ой",
    "ая",
    "ое",
    "ые",
    "ам",
    "ям",
    "ах",
    "ях",
    "ов",
    "ев",
    "ей",
    "ом",
    "ем",
    "ую",
    "юю",
    "ы",
    "и",
    "а",
    "я",
    "е",
    "о",
    "у",
    "ю",
)
STOPWORDS = {
    "а",
    "без",
    "больше",
    "будет",
    "быть",
    "в",
    "во",
    "все",
    "всё",
    "всегда",
    "где",
    "даже",
    "для",
    "до",
    "его",
    "ее",
    "её",
    "если",
    "еще",
    "ещё",
    "же",
    "за",
    "и",
    "из",
    "или",
    "именно",
    "их",
    "к",
    "как",
    "когда",
    "который",
    "которая",
    "которые",
    "между",
    "мы",
    "на",
    "над",
    "надо",
    "не",
    "него",
    "нее",
    "неё",
    "но",
    "нужно",
    "о",
    "об",
    "она",
    "они",
    "оно",
    "от",
    "по",
    "после",
    "потом",
    "потому",
    "просто",
    "с",
    "со",
    "свои",
    "своих",
    "свою",
    "своей",
    "своего",
    "своим",
    "там",
    "то",
    "только",
    "у",
    "уже",
    "хотя",
    "через",
    "что",
    "это",
    "автор",
}
GENERIC_STEMS = {
    "важн",
    "внутренн",
    "длинн",
    "дистанц",
    "лучш",
    "можн",
    "нужн",
    "принят",
    "результат",
    "решен",
    "сильн",
    "точн",
    "быстр",
}
DISPLAY_OVERRIDES = {
    "manus ai": "Manus AI",
    "manus": "Manus",
    "деньг": "деньги",
    "мышлен": "мышление",
    "мысл": "мышление",
    "дисциплин": "дисциплина",
    "убежден": "убеждения",
    "убеждени": "убеждения",
    "эмоц": "эмоции",
    "траектор": "траектория",
    "бизнес": "бизнес",
    "кейс": "кейсы",
    "лид": "лиды",
    "сделк": "сделки",
    "контент": "контент",
    "конкурент": "конкуренты",
    "найм": "найм",
    "бренд": "личный бренд",
    "ии": "ИИ",
    "нейросет": "нейросети",
    "функц": "функция",
    "видени": "видение",
    "аномал": "аномалия",
}
PREFERRED_KEYWORDS = (
    "ии",
    "функц",
    "видени",
    "нейросет",
    "аномал",
    "manus ai",
    "manus",
    "деньг",
    "мышлен",
    "мысл",
    "дисциплин",
    "убеждени",
    "убежден",
    "эмоц",
    "траектор",
    "бизнес",
    "кейс",
    "лид",
    "сделк",
    "контент",
    "конкурент",
    "найм",
    "бренд",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _limit_text(value: str, limit: int) -> str:
    text = _normalize_text(value).strip(" .")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" ,;:") + "…"


def _sentence(value: str, limit: int = 180) -> str:
    text = _limit_text(value, limit)
    if not text:
        return ""
    return text.rstrip(".!?") + "."


def _title_stem(token: str) -> str:
    lowered = token.lower().replace("ё", "е")
    for ending in TITLE_ENDINGS:
        if len(lowered) >= 6 and lowered.endswith(ending):
            return lowered[: -len(ending)]
    return lowered


def _display_keyword(stem: str, display: str) -> str:
    if stem in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[stem]
    return display.lower()


def _title_case_topic(value: str) -> str:
    text = _normalize_text(value)
    if not text:
        return "Ключевые идеи разговора"
    return text[:1].upper() + text[1:]


def _topic_phrase_for_sentence(value: str) -> str:
    text = _normalize_text(value)
    if not text:
        return "ключевые идеи разговора"
    if CYRILLIC_AI_RE.search(text):
        return text
    if re.search(r"[A-Z][A-Za-z0-9+-]*\s+AI\b", text):
        return text
    return text[:1].lower() + text[1:]


def _content_mode_format_label(content_mode: str) -> str:
    return {
        "conversation": "интервью",
        "monologue": "лекция",
        "workshop": "воркшоп",
    }.get(content_mode, "материал")


def _read_points(path: Path, *, read_summary_points_fn: Callable[[Path], list[str]]) -> list[str]:
    points = read_summary_points_fn(path)
    return [_normalize_text(item) for item in points if _normalize_text(item)]


def _read_manifest_rows(work_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest_path in sorted(work_dir.glob("manifest_chunk_*.tsv")):
        with manifest_path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                rows.append({str(key): _normalize_text(str(value or "")) for key, value in row.items()})
    return rows


def _informative_title_candidates(header_seed: dict, *, author_hint: str) -> list[str]:
    raw_candidates = []
    raw_title = _normalize_text(str(header_seed.get("raw_title") or ""))
    if raw_title:
        raw_candidates.append(raw_title)
    if isinstance(header_seed.get("title_candidates"), list):
        raw_candidates.extend(_normalize_text(str(item)) for item in header_seed.get("title_candidates", []))

    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        if not candidate:
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        if author_hint and key == author_hint.casefold():
            continue
        if len(TOKEN_RE.findall(candidate)) < 4:
            continue
        candidates.append(candidate)
    return candidates


def _extract_prescan_name(prescan_text: str) -> str:
    match = SOURCE_NAME_RE.search(prescan_text)
    return _normalize_text(match.group(1)) if match else ""


def _split_values(value: str) -> list[str]:
    return [
        item
        for item in (_normalize_text(part) for part in re.split(r"[;|,]\s*", value or ""))
        if item and not re.fullmatch(r"Speaker\s+\d+", item, flags=re.IGNORECASE)
    ]


def _extract_topic_scores(
    *,
    title_candidates: list[str],
    topic_texts: list[str],
    tldr_points: list[str],
    summary_points: list[str],
) -> tuple[Counter[str], dict[str, str]]:
    scores: Counter[str] = Counter()
    displays: dict[str, str] = {}

    def add_candidate(key: str, display: str, weight: int) -> None:
        norm_key = _normalize_text(key).lower()
        norm_display = _normalize_text(display)
        if not norm_key or not norm_display:
            return
        scores[norm_key] += weight
        displays.setdefault(norm_key, norm_display)

    for weight, texts in ((4, title_candidates), (3, topic_texts), (2, tldr_points), (1, summary_points)):
        for text in texts:
            for match in LATIN_AI_RE.finditer(text):
                phrase = _normalize_text(match.group(0))
                add_candidate(phrase.lower(), phrase, weight + 2)
            if CYRILLIC_AI_RE.search(text):
                add_candidate("ии", "ИИ", weight + 2)
            for token in TOKEN_RE.findall(text):
                lowered = token.lower().replace("ё", "е")
                if lowered == "ии":
                    add_candidate("ии", "ИИ", weight + 2)
                    continue
                if len(lowered) < 4 or lowered in STOPWORDS:
                    continue
                stem = _title_stem(lowered)
                if len(stem) < 4 or stem in STOPWORDS or stem in GENERIC_STEMS:
                    continue
                add_candidate(stem, token, weight)

    return scores, displays


def _choose_topic_label(
    *,
    title_candidates: list[str],
    topic_texts: list[str],
    tldr_points: list[str],
    summary_points: list[str],
    fallback_topic_hint: str,
) -> str:
    scores, displays = _extract_topic_scores(
        title_candidates=title_candidates,
        topic_texts=topic_texts,
        tldr_points=tldr_points,
        summary_points=summary_points,
    )
    chosen: list[str] = []
    seen: set[str] = set()

    for keyword in PREFERRED_KEYWORDS:
        if keyword not in scores:
            continue
        display = _display_keyword(keyword, displays.get(keyword, keyword))
        if display in seen:
            continue
        chosen.append(display)
        seen.add(display)
        if len(chosen) >= 3:
            break

    if len(chosen) < 3:
        for keyword, _score in scores.most_common():
            display = _display_keyword(keyword, displays.get(keyword, keyword))
            if display in seen:
                continue
            chosen.append(display)
            seen.add(display)
            if len(chosen) >= 3:
                break

    informative_source_title = title_candidates[0] if title_candidates else ""
    if not chosen:
        fallback = informative_source_title or _normalize_text(fallback_topic_hint).strip(" ,.")
        return _title_case_topic(fallback or "ключевые идеи разговора")
    if len(chosen) == 1:
        topic_label = _title_case_topic(chosen[0])
    elif len(chosen) == 2:
        topic_label = _title_case_topic(f"{chosen[0]} и {chosen[1]}")
    else:
        topic_label = _title_case_topic(f"{chosen[0]}, {chosen[1]} и {chosen[2]}")

    source_has_ai = bool(informative_source_title and (CYRILLIC_AI_RE.search(informative_source_title) or LATIN_AI_RE.search(informative_source_title)))
    topic_has_ai = bool(CYRILLIC_AI_RE.search(topic_label) or LATIN_AI_RE.search(topic_label))
    if informative_source_title and (("автор" in topic_label.casefold()) or (source_has_ai and not topic_has_ai)):
        return _title_case_topic(informative_source_title)
    return topic_label


def _effective_execution_mode(
    prepare_payload: dict,
    *,
    execution_mode_for_plan: Callable[..., str],
) -> str:
    total_chunks = int(prepare_payload.get("total_chunks") or 0)
    content_mode = str(prepare_payload.get("content_mode") or "conversation")
    telemetry = prepare_payload.get("telemetry") if isinstance(prepare_payload.get("telemetry"), dict) else {}
    duration_seconds = int(telemetry.get("duration_seconds") or 0)
    inferred = execution_mode_for_plan(
        total_chunks,
        content_mode=content_mode,
        duration_seconds=duration_seconds,
    )
    status_inferred = execution_mode_for_plan(
        total_chunks,
        content_mode=content_mode,
    )
    persisted = str(prepare_payload.get("execution_mode") or "").strip()
    if persisted == "multi" and status_inferred == "micro-multi":
        return status_inferred
    return persisted or inferred


def build_deterministic_header(
    work_dir: Path,
    *,
    load_prepare_payload: Callable[[Path], dict],
    load_json_if_exists: Callable[[Path], dict | None],
    write_text: Callable[[Path, str], None],
    write_stage_sentinel: Callable[[Path, dict], None],
    stage_sentinel_path: Callable[[Path, str], Path],
    update_prepare_state_fields: Callable[[Path, dict], object],
    execution_mode_for_plan: Callable[..., str],
    read_summary_points_fn: Callable[[Path], list[str]],
) -> dict:
    try:
        prepare_payload = load_prepare_payload(work_dir)
    except FileNotFoundError:
        prepare_payload = {}

    mode = _effective_execution_mode(
        prepare_payload if isinstance(prepare_payload, dict) else {},
        execution_mode_for_plan=execution_mode_for_plan,
    )
    if mode != "micro-multi":
        return {
            "work_dir": str(work_dir),
            "generated": False,
            "skipped": True,
            "reason": "deterministic header is enabled only for micro-multi",
            "mode": mode,
        }

    header_seed = load_json_if_exists(work_dir / "header-seed.json") or {}
    note_contract = load_json_if_exists(work_dir / "note-contract.json") or {}
    prescan_text = (work_dir / "prescan_context.txt").read_text(encoding="utf-8", errors="replace") if (work_dir / "prescan_context.txt").is_file() else ""
    manifest_rows = _read_manifest_rows(work_dir)
    summary_points: list[str] = []
    for summary_path in sorted(work_dir.glob("summary_chunk_*.md")):
        summary_points.extend(_read_points(summary_path, read_summary_points_fn=read_summary_points_fn))
    tldr_points = _read_points(work_dir / "tldr.md", read_summary_points_fn=read_summary_points_fn) if (work_dir / "tldr.md").is_file() else []

    title_candidates = _informative_title_candidates(header_seed, author_hint=_normalize_text(str(header_seed.get("author_hint") or "")))
    topic_texts = [row.get("topic", "") for row in manifest_rows if row.get("topic")]
    topic_label = _choose_topic_label(
        title_candidates=title_candidates,
        topic_texts=topic_texts,
        tldr_points=tldr_points,
        summary_points=summary_points,
        fallback_topic_hint=str(header_seed.get("topic_hint") or ""),
    )

    author_hint = _normalize_text(str(header_seed.get("author_hint") or ""))
    speaker_candidates = [
        _normalize_text(str(item))
        for item in header_seed.get("speaker_candidates", [])
        if _normalize_text(str(item))
    ] if isinstance(header_seed.get("speaker_candidates"), list) else []
    manifest_names = [
        name
        for row in manifest_rows
        for name in _split_values(row.get("names", ""))
    ]
    subject = (
        author_hint
        or _extract_prescan_name(prescan_text)
        or (speaker_candidates[0] if speaker_candidates else "")
        or (manifest_names[0] if manifest_names else "")
    )

    content_mode = str(
        note_contract.get("content_mode")
        or prepare_payload.get("content_mode")
        or "conversation"
    )
    format_label = _normalize_text(
        str((note_contract.get("header") or {}).get("format_label") or "")
    ) or _content_mode_format_label(content_mode)
    duration_hint = _normalize_text(str(header_seed.get("duration_estimate") or "unknown")) or "unknown"
    source_identity = header_seed.get("source_identity") if isinstance(header_seed.get("source_identity"), dict) else {}
    youtube_meta = source_identity.get("youtube") if isinstance(source_identity.get("youtube"), dict) else {}
    video_id = _normalize_text(str(youtube_meta.get("video_id") or ""))
    source_label = (
        f"https://www.youtube.com/watch?v={video_id}"
        if video_id
        else ", ".join(
            _normalize_text(str(item))
            for item in header_seed.get("source_files", [])
            if _normalize_text(str(item))
        )
        or "локальный источник"
    )

    title = f"{subject} — {topic_label}" if subject else topic_label
    lead = {
        "conversation": f"Большой разговор, в центре которого {_topic_phrase_for_sentence(topic_label)}.",
        "workshop": f"Практический разбор, в центре которого {_topic_phrase_for_sentence(topic_label)}.",
        "monologue": f"Материал, в центре которого {_topic_phrase_for_sentence(topic_label)}.",
    }.get(content_mode, f"Материал, в центре которого {_topic_phrase_for_sentence(topic_label)}.")
    abstract_parts = [lead]
    if tldr_points:
        abstract_parts.append(_sentence(tldr_points[0], limit=190))
    if len(tldr_points) > 1:
        abstract_parts.append(_sentence(f"Практический вектор: {tldr_points[1]}", limit=210))
    abstract = " ".join(part for part in abstract_parts if part)

    frame_points = tldr_points[:3] or summary_points[:3] or topic_texts[:3]
    while len(frame_points) < 3:
        frame_points.append(topic_label)
    frame_lines = [f"- {_sentence(point, limit=190)}" for point in frame_points[:3]]

    metadata_lines: list[str] = []
    if author_hint:
        metadata_lines.append(f"**Автор:** {author_hint}")
    metadata_lines.append(f"**Формат:** {format_label}")
    metadata_lines.append(f"**Тема:** {topic_label}")
    metadata_lines.append(f"**Длительность:** {duration_hint}")
    metadata_lines.append(f"**Источник:** {source_label}")
    metadata_block = "\n".join(metadata_lines)

    header_text = (
        f"# {title}\n\n"
        f"> {abstract}\n\n"
        f"{metadata_block}\n\n"
        "## Главная рамка автора\n"
        f"{frame_lines[0]}\n"
        f"{frame_lines[1]}\n"
        f"{frame_lines[2]}\n"
    )

    header_path = work_dir / "header.md"
    write_text(header_path, header_text)

    sentinel_path = stage_sentinel_path(work_dir, "header")
    write_stage_sentinel(
        sentinel_path,
        {
            "stage": "header",
            "strategy": "deterministic-build",
            "fingerprint": prepare_payload.get("fingerprint") if isinstance(prepare_payload, dict) else None,
            "output": "header.md",
            "completed": True,
            "completed_at": datetime.now().isoformat(),
            "title": title,
            "topic": topic_label,
        },
    )
    update_prepare_state_fields(work_dir, {"artifacts": {"header": str(header_path)}})

    return {
        "work_dir": str(work_dir),
        "generated": True,
        "skipped": False,
        "mode": mode,
        "strategy": "deterministic-build",
        "header_path": str(header_path),
        "title": title,
        "topic": topic_label,
        "subject": subject or None,
        "sentinel": str(sentinel_path),
    }


__all__ = [
    "build_deterministic_header",
]
