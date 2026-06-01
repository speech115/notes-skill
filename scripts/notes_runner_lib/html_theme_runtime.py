from __future__ import annotations

import argparse
import re
from pathlib import Path


def _add_class_to_opening_tag(tag: str, class_name: str) -> str:
    if re.search(rf'\bclass="[^"]*\b{re.escape(class_name)}\b[^"]*"', tag):
        return tag
    class_match = re.search(r'\bclass="([^"]*)"', tag)
    if class_match:
        classes = class_match.group(1).strip()
        return tag[: class_match.start()] + f'class="{classes} {class_name}"' + tag[class_match.end() :]
    return tag[:-1] + f' class="{class_name}">'


def _mark_toc(html: str) -> str:
    return re.sub(
        r'<nav\b([^>]*\bid="TOC"[^>]*)>',
        lambda match: _add_class_to_opening_tag(match.group(0), "note-toc"),
        html,
        count=1,
    )


def _mark_quotes(html: str) -> str:
    return re.sub(
        r"<blockquote\b[^>]*>",
        lambda match: _add_class_to_opening_tag(match.group(0), "note-quote"),
        html,
    )


def _mark_outline(html: str) -> str:
    return re.sub(
        r"(<h3\b[^>]*>\s*Тезисы:?\s*</h3>\s*)(<ol\b[^>]*>)",
        lambda match: match.group(1) + _add_class_to_opening_tag(match.group(2), "note-outline"),
        html,
        flags=re.IGNORECASE,
    )


def _wrap_case_sections(html: str) -> str:
    pattern = re.compile(
        r"(<h3\b[^>]*>\s*Кейс[^<]*</h3>.*?)(?=<h[123]\b|<hr\b|</section>|</main>|</body>)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(lambda match: f'<aside class="note-case">\n{match.group(1)}\n</aside>', html)


def _wrap_h2_chapters(html: str) -> str:
    pattern = re.compile(
        r"(<h2\b[^>]*>.*?</h2>.*?)(?=<h2\b|<h1\b|</main>|</body>)",
        flags=re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        chunk = match.group(1)
        if 'class="note-chapter"' in chunk:
            return chunk
        return f'<section class="note-chapter">\n{chunk}\n</section>'

    return pattern.sub(replace, html)


def _wrap_appendix_sections(html: str) -> str:
    pattern = re.compile(
        r"(<h1\b[^>]*>\s*(Упомянутые[^<]*|План действий|Ключевые идеи[^<]*)</h1>.*?)(?=<h1\b|</main>|</body>)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip().lower()
        class_name = "note-appendix note-action-plan" if title.startswith("план действий") else "note-appendix"
        return f'<section class="{class_name}">\n{match.group(1)}\n</section>'

    return pattern.sub(replace, html)


def add_longform_semantics(html: str) -> str:
    original = html
    if not re.search(r"<(nav|h[123]|blockquote)\b", html):
        return original

    html = _mark_toc(html)
    html = _mark_quotes(html)
    html = _mark_outline(html)
    html = _wrap_case_sections(html)
    html = _wrap_h2_chapters(html)
    html = _wrap_appendix_sections(html)
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add longform semantic classes to assembled notes HTML.")
    parser.add_argument("html_path")
    args = parser.parse_args(argv)
    path = Path(args.html_path)
    path.write_text(add_longform_semantics(path.read_text(encoding="utf-8")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
