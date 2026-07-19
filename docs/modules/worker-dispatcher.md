# Модуль Worker Dispatcher

## Назначение

Worker Dispatcher — исполнительная часть системы. Он не знает деталей PMON, NEC, Cisco или UPS. Его работа — взять задачу из очереди, найти нужный scenario, создать нужный transport, выполнить workflow и передать результат processors.

Файл реализации:

```text
netops_automation/app/worker.py
```

Запуск:

```bash
netops-worker --config /etc/netops/netops.yml
```

Для отладки:

```bash
netops-worker --config config/netops.example.yml --once
```

## Место в архитектуре

Worker находится между очередью и бизнес-логикой:

```text
PostgreSQL Queue -> Worker -> Transport + Scenario -> Processors -> PostgreSQL/Artifacts
```

Worker не должен превращаться в большой файл с условиями вида `if vendor == NEC`. Для этого есть registry сценариев и transport'ов.

## Как выполняется задача

Последовательность:

1. Worker стартует и читает config.
2. Подключается к PostgreSQL.
3. Вызывает восстановление зависших `RUNNING`.
4. Берёт следующую задачу через Queue Manager.
5. По строковому ключу находит scenario.
6. По строковому ключу находит transport.
7. Собирает transport из payload.
8. Запускает `scenario.run(job, transport)`.
9. Прогоняет результат через processors.
10. Отмечает задачу успешной или ошибочной.

## Как создаётся transport

Worker ищет host в:

```text
payload.transport.host
payload.host
```

Остальные поля из `payload.transport` передаются в constructor транспорта. Если timeout не задан, используется `job.timeout_sec`.

Это позволяет одному сценарию гибко менять параметры подключения без изменения кода worker.

## Ошибки

`NonRetryableError` означает, что повтор не поможет. Например, не указан `payload.device`, неизвестный PMON-профиль или нет обязательного пароля.

Обычные исключения считаются retryable. Например, TFTP timeout, временно недоступная РРС, сетевой сбой.

Финальное решение о `RETRY`, `FAILED` или `SKIPPED` принимает Queue Manager, потому что именно он знает attempts и `expires_at`.

## Завершение процесса

Worker обрабатывает `SIGTERM` и `SIGINT`. После сигнала он не берёт новые задачи, но текущую пытается завершить. Это важно для systemd restart и обновлений.

## План развития

Нужно добавить:

- структурированные JSON-логи;
- job id/device id во все log records;
- per-device concurrency lock;
- wrapper timeout вокруг всего scenario;
- режим нескольких worker-процессов или systemd instances.

