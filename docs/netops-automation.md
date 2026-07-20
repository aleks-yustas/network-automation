# NetOps Automation

NetOps Automation — offline-система автоматизации эксплуатации сетевого оборудования. Она предназначена не только для скачивания PMON или резервного копирования конфигураций. Это общая платформа, в которую можно постепенно добавлять новые устройства, транспорты, сценарии и обработчики результатов.

Система рассчитана на Debian 13 в LXC-контейнере Proxmox. Она работает как обычный Linux-сервис через `systemd`, использует существующий PostgreSQL и не требует Redis, RabbitMQ, Kubernetes или внешних online-зависимостей.

## Главная архитектурная идея

Система разделена на слои:

```text
Scheduler -> PostgreSQL Queue -> Worker -> Transport -> Scenario -> Processors
```

Каждый слой отвечает только за свою часть работы.

Scheduler создаёт задачи, но не подключается к оборудованию.

Queue Manager хранит состояние задач, блокировки, retry, backoff и expiration.

Worker берёт задачи из очереди и вызывает нужные модули.

Transport отвечает только за протокол: Telnet, TFTP, FTP, позже SSH/SNMP/HTTP/SFTP.

Scenario описывает последовательность действий: скачать PMON, сохранить конфигурацию, собрать версию, получить MAC table.

Processor обрабатывает результат: сохраняет файл, пишет metadata, декодирует PMON, коммитит конфиг в Git, импортирует logs.

## Почему PMON теперь модуль

Изначально проект вырос из PMON-скриптов, но PMON — только один доменный сценарий. Поэтому название проекта заменено на NetOps Automation, а PMON вынесен в отдельный модуль:

```text
netops_automation/modules/pmon/
```

PMON-модуль отвечает за скачивание и проверку `.pm` файлов с РРС. Он использует TFTP transport и отдельные profiles для типов РРС.

## Текущие реализованные части

Реализовано ядро:

- PostgreSQL schema;
- Queue Manager;
- Scheduler;
- Worker Dispatcher;
- registry для transports/scenarios/processors;
- TFTP, FTP, Telnet transports;
- PMON download scenario;
- NEC CX2200 backup scenario;
- archive processor;
- PostgreSQL artifact metadata processor;
- systemd units.

## Подробная документация по модулям

Основной индекс:

```text
docs/modules/README.md
```

Ключевые документы:

- [Queue Manager](modules/queue-manager.md)
- [Scheduler](modules/scheduler.md)
- [Worker Dispatcher](modules/worker-dispatcher.md)
- [Transport Layer](modules/transport-layer.md)
- [Scenario Layer](modules/scenario-layer.md)
- [Processor Layer](modules/processor-layer.md)
- [PMON Module](modules/pmon-module.md)
- [Configuration Backup Module](modules/configuration-backup-module.md)
- [Logs Module](modules/logs-module.md)

## Быстрый пример запуска

Применить схему:

```bash
psql "$NETOPS_DATABASE_DSN" -f db/migrations/001_init.sql
```

Создать задачу по schedule:

```bash
netops-scheduler \
  --config config/netops.example.yml \
  --schedule config/schedules.example.yml \
  --name pasolink-pmon-catchup
```

Выполнить одну задачу:

```bash
netops-worker --config config/netops.example.yml --once
```

## PMON и 7 дней хранения

PMON на РРС хранится в течение недели. Поэтому schedule `pasolink-pmon-catchup` задаёт:

```yaml
expires_after_days: 7
idempotency_scope: "target_date"
```

Это значит: задачу можно повторять несколько дней, но только пока файл ещё потенциально есть на РРС. После истечения окна задача становится `SKIPPED`.

Schedule использует `target_dates: last_7_days`, поэтому после простоя scheduler создаёт задачи за последние 7 дат. Дубли не появляются из-за idempotency key по `target_date`.

## Inventory для PMON

Тип РРС хранится в metadata устройства:

```sql
INSERT INTO netops_devices (name, vendor, model, mgmt_ip, site, region, metadata)
VALUES (
  'rrs-172-18-0-107',
  'NEC',
  'Pasolink',
  '172.18.0.107',
  'site-1',
  'region-1',
  '{"device": "Pasolink NEO/c"}'::jsonb
);
```

Поддержанные профили:

- `Pasolink NEO/c`: `/pmon/daily-dmr-YYYYMMDD.pm`
- `Pasolink NEO`: `/pmon/daily-YYYYMMDD.pm`
