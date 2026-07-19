# Модуль PMON

## Назначение

PMON module отвечает за скачивание и первичную проверку файлов производительности с РРС. PMON больше не является названием всей системы. Это отдельный доменный модуль внутри NetOps Automation.

Текущие файлы:

```text
netops_automation/modules/pmon/profiles.py
netops_automation/scenarios/download_pmon.py
```

## Откуда взята логика

Основа взята из старого batch-файла:

```text
PMON/dowload_pasolink_log.bat
```

Несмотря на имя `log`, этот файл скачивает PMON:

```text
/pmon/daily-dmr-YYYYMMDD.pm
/pmon/daily-YYYYMMDD.pm
```

Старый скрипт делил устройства на две группы IP. В новой системе это заменено на поле `device` в target metadata.

## Типы РРС

Профили сейчас такие:

```text
Pasolink NEO/c -> /pmon/daily-dmr-{date}.pm
Pasolink NEO   -> /pmon/daily-{date}.pm
```

Поле `device` должно приходить из описания targets и храниться в `netops_devices.metadata`:

```json
{"device": "Pasolink NEO/c"}
```

Именно это значение выбирает PMON profile.

## Как работает сценарий

Сценарий `download_pmon` получает задачу с payload:

- `host` — IP РРС;
- `device` — тип РРС;
- `target_date` — дата файла в формате `YYYYMMDD`.

Дальше он:

1. Проверяет, что transport — TFTP.
2. Проверяет наличие `device`.
3. Проверяет формат `target_date`.
4. Находит профиль по `device`.
5. Собирает remote path.
6. Скачивает файл через TFTP.
7. Читает bytes.
8. Проверяет структуру файла.
9. Возвращает `ScenarioResult`.

## Проверка файла

Текущая проверка простая, но полезная:

```text
header_size = 16 bytes
record_size = 30 bytes
```

Если размер файла меньше или равен header, результат `empty`.

Если полезная часть не кратна размеру записи, результат `error`.

Если всё кратно, результат `ok`, и считается количество records.

Это не полная расшифровка PMON. Это первичная проверка, что скачанный файл похож на PMON.

## 7-дневное окно

В РРС PMON хранится в течение недели. Поэтому пропущенные задачи можно пробовать выполнять 7 дней.

В schedule это задаётся так:

```yaml
expires_after_days: 7
idempotency_scope: "target_date"
```

`idempotency_scope: target_date` важен: задача относится к дате PMON-файла, а не к дате запуска scheduler.

Если задача не выполнена за 7 дней, Queue Manager переводит её в `SKIPPED`. Это правильно: после недели файл на РРС уже может отсутствовать.

Scheduler умеет разворачивать PMON-задачи сразу на несколько дат. Для этого используется `target_dates: last_7_days`. При каждом запуске создаются jobs за последние 7 дат, начиная со вчерашней. Уже существующие jobs не дублируются, потому что idempotency key строится по `target_date`.

## Как должен выглядеть schedule

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

`target_dates: last_7_days` означает: scheduler создаёт отдельную задачу на каждую дату в окне хранения PMON. Это полезно после простоя сервера, проблем с сетью или недоступности РРС.

Большое `max_attempts` здесь допустимо, потому что настоящая граница — `expires_at`. Backoff не даст задаче крутиться слишком часто.

## Артефакты

Сценарий возвращает raw bytes. `archive` processor сохраняет `.pm` файл на диск. В metadata попадает:

- тип artifact: `pmon_raw`;
- имя файла;
- remote path;
- дата PMON;
- тип РРС;
- размер;
- количество records.

## План развития

Следующие шаги:

1. Добавить decoder PMON records.
2. Добавить проверку полноты 96 интервалов.
3. Сохранять decoded values в PostgreSQL.
4. Добавить отчёт: какие РРС/даты не скачаны.
5. Добавить новые profiles для других типов РРС.
