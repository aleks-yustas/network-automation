# Техническое описание архитектуры NetOps Automation

Этот документ даёт цельную картину архитектуры. Подробные описания каждого модуля находятся в `docs/modules/`.

## Зачем нужна система

NetOps Automation создаётся как промышленный offline-сервис для автоматизации эксплуатации сетевого оборудования. Он должен заменить набор ручных и batch-скриптов общей платформой, где можно надёжно планировать задачи, выполнять их через разные протоколы, сохранять результаты и видеть историю выполнения.

Система не должна быть тяжёлой. Для текущей инфраструктуры достаточно одного Python-приложения, PostgreSQL и systemd. Микросервисы, брокеры сообщений и Kubernetes здесь не дают пользы, но усложняют установку и сопровождение в изолированной сети.

## Базовый поток данных

```text
systemd timer
  -> Scheduler
  -> PostgreSQL queue
  -> Worker Dispatcher
  -> Transport
  -> Scenario
  -> Processors
  -> Artifacts + PostgreSQL metadata
```

Такой поток выбран, чтобы отделить факт планирования задачи от её выполнения. Если устройство недоступно, задача не теряется. Если worker перезапущен, очередь восстанавливается. Если нужно добавить новый тип оборудования, ядро очереди не меняется.

## Слои системы

### Scheduler

Scheduler — генератор задач. Он читает расписание, выбирает устройства из inventory и создаёт jobs. Он не должен подключаться к оборудованию. Благодаря этому scheduler можно запускать через `systemd timer` как короткий one-shot процесс.

Подробно: [Scheduler](modules/scheduler.md)

### Queue Manager

Queue Manager — механизм надёжности. Он хранит статусы, attempts, locks, retry, backoff и expiration. PostgreSQL используется как durable queue через транзакции и `FOR UPDATE SKIP LOCKED`.

Подробно: [Queue Manager](modules/queue-manager.md)

### Worker Dispatcher

Worker — исполнитель. Он берёт задачу из очереди, находит scenario и transport по registry key, запускает scenario и отдаёт результат processors.

Подробно: [Worker Dispatcher](modules/worker-dispatcher.md)

### Transport Layer

Transport — протокольный адаптер. Он не знает, что такое PMON или NEC. Он умеет только обмениваться данными: скачать файл по TFTP, выполнить Telnet-команду, позже выполнить SSH-команду или SNMP walk.

Подробно: [Transport Layer](modules/transport-layer.md)

### Scenario Layer

Scenario — бизнес-последовательность. Он знает, какой remote path собрать, какую команду отправить, какой prompt ждать и как понять, что операция успешна.

Подробно: [Scenario Layer](modules/scenario-layer.md)

### Processor Layer

Processor — обработка результата. Он сохраняет файлы, пишет metadata, декодирует данные, делает diff, импортирует logs. Scenario не должен заниматься долговременным хранением.

Подробно: [Processor Layer](modules/processor-layer.md)

## Доменные модули

PMON — первый доменный модуль. Он скачивает `.pm` файлы с РРС по TFTP. Тип РРС берётся из поля `device` в metadata target. PMON хранится на РРС 7 дней, поэтому задача имеет `expires_at`.

Подробно: [PMON Module](modules/pmon-module.md)

Configuration Backup — модуль резервного копирования конфигураций. Первый сценарий работает с NEC CX2200 через Telnet и инициирует сохранение конфигурации на заранее настроенный FTP-сервер.

Подробно: [Configuration Backup Module](modules/configuration-backup-module.md)

Logs — будущий модуль обычных логов оборудования. Он отделён от PMON, потому что PMON — бинарные performance-файлы со своей логикой.

Подробно: [Logs Module](modules/logs-module.md)

## PostgreSQL как центр состояния

PostgreSQL хранит:

- inventory устройств;
- credentials;
- очередь задач;
- audit events;
- metadata artifacts.

Сами большие файлы хранятся на диске в artifact directory, а PostgreSQL хранит путь, размер и checksum.

Подробно: [Database](modules/database.md)

## Правило расширения

Добавление нового оборудования не должно требовать изменения Queue Manager, Scheduler или Worker.

Обычно нужно добавить:

1. Новый scenario.
2. Новый transport, если протокол ещё не поддержан.
3. Новый processor, если результат требует новой обработки.
4. Inventory records.
5. Schedule.

Так сохраняется простота ядра и возможность роста системы.

