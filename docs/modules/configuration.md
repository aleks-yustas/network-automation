# Модуль Configuration

## Назначение

Модуль конфигурации отвечает за настройки процесса: как подключиться к PostgreSQL, как называется worker, куда сохранять артефакты, какие значения использовать для timeout и backoff. Он не описывает устройства и расписания. Устройства живут в inventory, а расписания — в `schedules.yml`.

Файл реализации:

```text
netops_automation/core/config.py
```

Пример:

```text
config/netops.example.yml
```

## Почему YAML плюс environment

Система должна работать в изолированной инфраструктуре без внешних сервисов конфигурации. Поэтому основной формат — обычный YAML-файл. При этом важные значения можно переопределить переменными окружения. Это удобно для systemd: секреты и DSN можно держать в `/etc/netops/netops.env`, а обычные настройки — в `/etc/netops/netops.yml`.

Приоритет такой:

```text
environment > YAML > значение по умолчанию
```

## Основные параметры

`database_dsn` — строка подключения к PostgreSQL. Это обязательное значение. Система не использует SQLite.

`worker_id` — имя worker'а. Оно пишется в `locked_by`, чтобы было видно, какой процесс взял задачу.

`poll_interval_sec` — пауза между проверками очереди, когда задач нет.

`default_job_timeout_sec` — timeout по умолчанию, если schedule не задал свой.

`backoff_base_sec` и `backoff_max_sec` — параметры экспоненциального backoff.

`artifact_dir` — корневая директория для файлов, которые сохраняют processors.

## Переменные окружения

Поддерживаются:

- `NETOPS_DATABASE_DSN`
- `NETOPS_WORKER_ID`
- `NETOPS_POLL_INTERVAL_SEC`
- `NETOPS_DEFAULT_JOB_TIMEOUT_SEC`
- `NETOPS_BACKOFF_BASE_SEC`
- `NETOPS_BACKOFF_MAX_SEC`
- `NETOPS_ARTIFACT_DIR`

## Производственная схема файлов

Планируемая структура на Debian:

```text
/etc/netops/netops.yml
/etc/netops/netops.env
/etc/netops/schedules.yml
/var/lib/netops/artifacts/
/srv/netops/
```

## Что важно для эксплуатации

Файл `netops.env` может содержать пароль к PostgreSQL. Его права должны быть строгими: читать должен только пользователь `netops` и root. В schedule не нужно хранить пароли от устройств. Для этого есть таблица credentials.

## План развития

Следующий шаг — добавить команду проверки конфигурации, чтобы перед запуском worker можно было быстро увидеть ошибки: нет DSN, не существует artifact directory, schedule ссылается на неизвестный scenario или transport.

