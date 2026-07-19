# Документация по модулям NetOps Automation

NetOps Automation проектируется как единая offline-система автоматизации эксплуатации сетевого оборудования. Это не набор отдельных скриптов и не микросервисная платформа. Это один понятный Python-сервис, который работает в LXC-контейнере на Debian, использует существующий PostgreSQL и запускается обычными средствами Linux через `systemd`.

Главная идея архитектуры: разделить систему не по протоколам или вендорам, а по ответственности. Расписание только создаёт задачи. Очередь только хранит состояние и решает, что можно выполнять. Worker только диспетчеризует выполнение. Transport только обменивается данными с устройством. Scenario описывает смысловую последовательность действий. Processor обрабатывает результат. Доменные модули, например PMON, живут поверх этой основы и не ломают ядро.

## Как читать документы

Сначала стоит прочитать документы про ядро:

- [Core Models](core-models.md) — общие модели данных и статусы задач.
- [Database](database.md) — таблицы PostgreSQL и зачем они нужны.
- [Queue Manager](queue-manager.md) — жизненный цикл задач, retry, backoff, блокировки.
- [Scheduler](scheduler.md) — как создаются задачи по расписанию.
- [Worker Dispatcher](worker-dispatcher.md) — как задача превращается в реальное действие.

Затем документы про расширение системы:

- [Transport Layer](transport-layer.md) — Telnet, FTP, TFTP и будущие SSH/SNMP/HTTP/SFTP.
- [Scenario Layer](scenario-layer.md) — сценарии работы с оборудованием.
- [Processor Layer](processor-layer.md) — обработка файлов, конфигураций, PMON, логов.
- [Inventory](inventory.md) — модель устройств и target metadata.
- [Credentials](credentials.md) — хранение и передача учётных данных.

И отдельно доменные модули:

- [PMON Module](pmon-module.md) — скачивание PMON с РРС и 7-дневное окно повторов.
- [Configuration Backup Module](configuration-backup-module.md) — резервное копирование конфигураций, первый сценарий NEC CX2200.
- [Logs Module](logs-module.md) — будущий модуль скачивания обычных логов, отдельно от PMON.
- [Observability Module](observability-module.md) — наблюдаемость, аудит, отчёты и диагностика.
- [Deployment/systemd](deployment-systemd.md) — как всё должно жить на Debian 13 в LXC.

## Сквозной поток работы

Типовой запуск выглядит так:

1. `systemd timer` запускает `netops-scheduler`.
2. Scheduler читает расписание и выбирает устройства из `netops_devices`.
3. Для каждого устройства создаётся запись в `netops_jobs`.
4. `netops-worker` берёт готовую задачу из PostgreSQL с блокировкой.
5. Worker создаёт нужный transport.
6. Worker запускает нужный scenario.
7. Scenario выполняет команды или скачивает файл.
8. Processor сохраняет результат и пишет metadata.
9. Queue Manager переводит задачу в финальный статус.

Такой поток позволяет добавлять новые устройства и новые сценарии без переписывания очереди, scheduler и worker.

