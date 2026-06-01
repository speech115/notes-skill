# notes-skill context

`notes-skill` — локальный Codex skill `/notes`, который превращает YouTube, локальные transcript-файлы, audio/video и batch-директории в подробные учебные конспекты.

Этот repo — единственный нормальный слой разработки. Live install в `~/.codex/skills/notes` или похожей директории считается deployment target, а не местом для ручных правок.

## Сейчас важно

- Runtime runner-а живёт в `scripts/notes_runner_lib/`.
- Главный пользовательский контракт описан в `SKILL.md`.
- Установка и публичный workflow описаны в `README.md`.
- Release flow описан в `RELEASE.md`.
- Debug/forensics идут через файловые артефакты из `OBSERVABILITY.md` и `TROUBLESHOOTING.md`.
- `release-check` не должен молча пропускать `SKIP` в quick deterministic слое.

## Рабочий цикл

1. Читать `AGENTS.md`, этот файл и `REFERENCES.md`.
2. Проверить текущее состояние:

```bash
bin/status
```

3. Для runtime-изменений работать через reproduce -> fix -> verify.
4. Перед live promote:

```bash
git status --short
bash scripts/release-check.sh
bash scripts/promote-live.sh
```

`--allow-dirty` у `promote-live` — только для аварийной forensic-ситуации.

## Где что хранить

- `drafts/` — рабочие черновики, планы, временные audit notes.
- `outputs/` — существенные отчёты и синтезы, которые должны пережить чат.
- `final/` — готовые пользовательские/релизные артефакты вне runtime-кода.
- `references/` — дополнительные источники и материалы, на которые repo должен ссылаться.

## Что не делать

- Не править live skill руками при обычной разработке.
- Не считать локальный assemble с `--skip-telegram` финальным пользовательским `/notes`.
- Не добавлять платформенную архитектуру вокруг runner-а без конкретного бага или пользовательского workflow.
- Не читать полный transcript в основной контекст при обычном `/notes` запуске: extraction agents читают его сами.
