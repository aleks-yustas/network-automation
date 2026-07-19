# Модуль Configuration Backup

## Назначение

Configuration Backup module отвечает за автоматизированное сохранение конфигураций сетевого оборудования. Это не просто копирование файлов. Для разных устройств процесс может выглядеть по-разному: где-то нужно выполнить CLI-команду, где-то скачать файл по FTP/SFTP, где-то получить конфиг через API.

Первый реализуемый сценарий:

```text
netops_automation/scenarios/nec_cx2200_backup.py
```

## Первый целевой кейс: NEC CX2200

Для NEC CX2200 требуется:

1. Подключиться по Telnet.
2. Авторизоваться.
3. Выполнить команду сохранения конфигурации на FTP-сервер.

FTP-сервер уже прописан на коммутаторе. Поэтому на первом этапе scenario не должен сам загружать файл по FTP. Он только инициирует сохранение.

## Почему это scenario, а не transport

Telnet transport ничего не знает о NEC. Он умеет только ждать prompt и отправлять строки. А scenario знает:

- какие prompts ожидать;
- как отправлять username/password;
- какую команду выполнить;
- какие слова считать успехом;
- какие слова считать ошибкой.

Такой подход позволит позже использовать TelnetTransport для других сценариев: `show version`, `collect alarms`, `backup config` для другого оборудования.

## Payload

Обязательные поля:

- `host`;
- `username`;
- `password`.

Опциональные поля:

- `command`;
- `login_prompts`;
- `password_prompts`;
- `shell_prompts`;
- `success_markers`;
- `failure_markers`;
- `login_timeout_sec`;
- `command_timeout_sec`.

Эти параметры вынесены в payload, потому что реальные prompts и тексты success/failure могут отличаться на разных firmware.

## Текущий workflow

Сценарий:

1. Проверяет, что передан `TelnetTransport`.
2. Ждёт login prompt.
3. Отправляет username.
4. Ждёт password prompt.
5. Отправляет password.
6. Ждёт shell prompt.
7. Выполняет command.
8. Ждёт shell prompt.
9. Проверяет transcript.
10. Возвращает transcript как artifact data.

## Что считается ошибкой

Если нет username/password, ошибка non-retryable: повтор не поможет.

Если Telnet не подключился или оборвалось соединение, ошибка retryable.

Если CLI вернул failure marker, сейчас это `ScenarioError`, worker считает её retryable. Позже лучше разделить ошибки: неправильная команда или отказ авторизации должны быть non-retryable.

## План развития

Нужно проверить реальную команду NEC CX2200 и success markers на устройстве. После этого можно добавить второй этап:

```text
Telnet command -> проверка FTP-файла -> archive -> Git commit -> diff report
```

Также планируются сценарии:

- Cisco config backup через SSH;
- MikroTik export через SSH/API;
- UPS config/status backup;
- нормализация конфигураций;
- локальный Git archive.

