# Модуль Observability

## Назначение

Observability module нужен, чтобы оператор понимал, что происходит с системой. Автоматизация без наблюдаемости опасна: задачи могут падать, файлы могут не скачиваться, устройства могут быть недоступны, а оператор увидит проблему слишком поздно.

Сейчас observability частично реализована через PostgreSQL и обычные Python logs. Отдельного web UI или exporter пока нет.

## Что уже есть

`netops_jobs` показывает текущее состояние задач.

`netops_job_events` хранит историю переходов.

`netops_artifacts` показывает, какие файлы были сохранены.

Python logging пишет события worker/scheduler в stdout/journald.

## Полезные SQL-запросы

Состояние очереди:

```sql
SELECT status, count(*)
FROM netops_jobs
GROUP BY status
ORDER BY status;
```

Последние ошибки:

```sql
SELECT id, job_type, device_id, attempt, error_code, error_message, updated_at
FROM netops_jobs
WHERE status IN ('FAILED', 'TIMEOUT')
ORDER BY updated_at DESC
LIMIT 50;
```

PMON-задачи, которые истекли:

```sql
SELECT id, device_id, payload->>'target_date' AS target_date, error_message
FROM netops_jobs
WHERE status = 'SKIPPED'
  AND error_code = 'expired'
ORDER BY updated_at DESC;
```

Последние artifacts:

```sql
SELECT device_id, artifact_type, path, size_bytes, created_at
FROM netops_artifacts
ORDER BY created_at DESC
LIMIT 50;
```

## Почему audit table важнее простого log.txt

Старые batch-скрипты писали вывод TFTP в `log.txt`. Это помогает только локально и только пока файл не потерян. PostgreSQL audit позволяет связать задачу, устройство, попытки, ошибку и artifact.

При расследовании важно видеть цепочку:

```text
created -> running -> retry -> running -> done
```

или:

```text
created -> retry -> skipped because expired
```

## План развития

Нужно добавить CLI:

```bash
netops-admin status
netops-admin jobs --failed
netops-admin pmon completeness --days 7
netops-admin retry <job-id>
```

Также нужны:

- structured JSON logs;
- Prometheus textfile exporter или `/metrics`;
- ежедневный отчёт полноты PMON;
- redaction секретов в logs;
- runbook для типовых ошибок: TFTP timeout, auth failed, unknown device profile.

