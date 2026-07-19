# Модуль Scenario Layer

## Назначение

Scenario Layer описывает, что именно нужно сделать с устройством. Это слой смысла. Transport умеет только передавать данные, а scenario знает последовательность действий: какие команды отправить, какого prompt ждать, какой remote path собрать, какие признаки успеха или ошибки искать.

Пакет:

```text
netops_automation/scenarios/
```

## Контракт

Каждый scenario реализует метод:

```python
def run(self, job: Job, transport: object) -> ScenarioResult:
    ...
```

На вход приходит задача и уже созданный transport. На выход возвращается `ScenarioResult`.

## Почему scenario отделён от transport

Один и тот же transport может использоваться десятками сценариев. Например, TFTP может скачать PMON, обычный LOG, конфиг или firmware. Telnet может сохранить конфиг, собрать версию, выключить paging, посмотреть alarms.

Если в transport положить знания о PMON или NEC-командах, этот transport станет частным скриптом. Поэтому protocol mechanics остаются в transport, а workflow — в scenario.

## Текущие сценарии

`download_pmon` скачивает PMON-файл с РРС по TFTP.

`nec_cx2200_backup_config` подключается к NEC CX2200 по Telnet и отправляет команду сохранения конфигурации на FTP-сервер, который уже настроен на коммутаторе.

## Что scenario должен делать

Scenario должен:

- проверить обязательные поля payload;
- убедиться, что передан правильный transport;
- выполнить последовательность действий;
- интерпретировать ответ устройства;
- вернуть структурированный результат.

## Что scenario не должен делать

Scenario не должен:

- сам менять статус задачи в очереди;
- писать directly в `netops_jobs`;
- заниматься глобальным retry/backoff;
- хранить список IP-адресов;
- смешивать работу с устройством и долговременное хранение результата.

За хранение отвечают processors. За retry отвечает Queue Manager. За список устройств отвечает inventory.

## Будущие сценарии

Планируются:

- `download_device_log`;
- `download_pmon_range`;
- `show_version`;
- `collect_mac_table`;
- `backup_config_cisco`;
- `backup_config_mikrotik`;
- `ups_status`;
- `collect_alarm_table`.

## Как добавить scenario

Нужно:

1. Создать файл в `scenarios/`.
2. Описать payload contract.
3. Использовать существующий transport или добавить новый.
4. Возвращать `ScenarioResult` с metadata.
5. Зарегистрировать scenario key в `SCENARIOS`.
6. Добавить schedule.

