# AI PR Review for NetOps Automation

Автоматическое ревью PR работает через GitHub Actions и `self-hosted runner`.

## Как устроено

1. GitHub получает событие `pull_request`
2. workflow `.github/workflows/ai-pr-review.yml` запускается автоматически
3. job исполняется на `self-hosted runner` на локальной машине
4. runner:
   - checkout проекта
   - строит diff PR
   - читает docs и измененные файлы
   - вызывает DeepSeek
   - публикует комментарий в PR от имени бота

## Что анализируется

- `docs/netops-automation.md`
- `docs/technical-modules.md`
- `docs/modules/README.md`
- `pyproject.toml`
- измененные файлы PR

## Что публикуется в PR

- потенциальные баги
- архитектурные проблемы
- рекомендации
- основания со ссылкой на файлы проекта

## Что нужно для работы

- `AI_REVIEW_BOT_TOKEN` в GitHub Secrets
- `DEEPSEEK_KEY` в GitHub Secrets
- self-hosted runner на машине, где есть Node.js

Подробная настройка описана в ответе Codex и может быть вынесена в отдельный чек-лист.
