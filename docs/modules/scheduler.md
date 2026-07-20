# Модуль Scheduler

## Назначение

Scheduler создаёт задачи по расписанию. Он не подключается к оборудованию, не скачивает файлы и не выполняет команды. Его задача — посмотреть на inventory, посмотреть на schedule и положить в PostgreSQL корректные jobs.

Файл реализации:

```text
netops_automation/app/scheduler.py
```

Обычно scheduler запускается через `systemd timer`, например один раз в сутки.

## Почему scheduler отделён от worker

Если смешать расписание и выполнение, получится старый стиль batch-скриптов: цикл по IP, сразу TFTP, сразу лог в файл. Такой подход плохо восстанавливается после сбоев и плохо расширяется.

В новой архитектуре scheduler только создаёт намерение:

```text
"Для такого-то устройства нужно выполнить такую-то задачу"
```

Дальше очередь и worker сами решают, когда и как её выполнять.

## Входные данные

Scheduler использует:

- `netops.yml` — общие настройки.
- `schedules.yml` — описания расписаний.
- `netops_devices` — inventory устройств.
- `netops_device_credentials` — учётные данные, если нужны сценарию.

## Формат schedule

Пример PMON:

```yaml
pasolink-pmon-catchup:
  job_type: "pmon_download"
  scenario: "download_pmon"
  transport: "tftp"
  priority: 100
  max_attempts: 64
  timeout_sec: 30
  expires_after_days: 7
  idempotency_scope: "target_date"
  device_selector:
    vendor: "NEC"
  payload:
    target_dates: "last_7_days"
    processors: ["archive", "postgres_metadata"]
```

`job_type` нужен оператору и processors. `scenario` и `transport` нужны worker. `device_selector` выбирает устройства. `payload` передаётся сценарию.

## Как выбираются устройства

Сейчас поддерживаются простые equality-фильтры:

- `vendor`
- `model`
- `site`
- `region`

И всегда добавляется:

```sql
enabled = true
```

Для PMON это означает: выбрать все активные устройства NEC, у которых в `metadata` должен быть указан конкретный тип РРС через поле `device`.

## Как собирается payload

Scheduler делает несколько шагов:

1. Берёт payload из schedule.
2. Если указано `target_dates`, разворачивает один schedule в несколько payload'ов.
3. Если `target_date: yesterday`, заменяет на реальную дату `YYYYMMDD`.
4. Добавляет `host` из `mgmt_ip` или `host`.
5. Если указан `credential_purpose`, добавляет username/secret.
6. Добавляет объект `target` с именем, vendor, model, site, region.
7. Добавляет поля из `metadata` устройства.

Так PMON-сценарий получает `device = "Pasolink NEO/c"`, не зная о таблице inventory.

## Idempotency

Scheduler защищает очередь от дублей через `idempotency_key`.

Для ежедневных задач можно использовать `daily`. Для PMON используется `target_date`, потому что задача за конкретную дату может запускаться и повторяться несколько дней.

Например, PMON за `20260718` должен иметь один job на устройство, даже если scheduler запустился несколько раз.

Для PMON catch-up scheduler создаёт несколько payload'ов: вчера, позавчера и дальше до глубины окна. Каждый payload получает свой `target_date`, поэтому idempotency key тоже становится отдельным для каждой даты.

## Expiration

Если в schedule есть `expires_after_days`, scheduler считает `expires_at`.

Для PMON:

```text
target_date + 7 дней
```

Это значит, что пропущенные PMON-задачи можно догонять в течение 7 дней. После этого они становятся `SKIPPED`.

## План развития

Нужно добавить dry-run режим, чтобы видеть, какие задачи будут созданы, без записи в БД.

Также стоит добавить проверку полноты: scheduler сможет смотреть `netops_jobs`/`netops_artifacts` и создавать catch-up не за все последние 7 дней, а только за реально отсутствующие даты.
