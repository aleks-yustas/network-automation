# Модуль Logs

## Назначение

Logs module планируется для сбора обычных логов оборудования: event log, alarm log, syslog snapshots, диагностические файлы. Он должен быть отдельным от PMON, потому что PMON — это бинарные performance-файлы со своей структурой и 7-дневным окном хранения.

## Текущий статус

Модуль пока не реализован.

Важно: файл `PMON/dowload_pasolink_log.bat`, который обсуждался ранее, на самом деле скачивает PMON, а не обычные логи. Поэтому его логика перенесена в PMON module.

## Чем Logs отличается от PMON

PMON:

- бинарный `.pm` файл;
- path зависит от типа РРС;
- проверяется по header/record size;
- хранится на РРС 7 дней;
- дальше может декодироваться в интервальные показатели.

Logs:

- обычно текстовые или vendor-specific файлы;
- могут храниться в других каталогах;
- могут иметь другое окно хранения;
- требуют нормализации времени, уровней severity и источника;
- могут импортироваться в Loki или PostgreSQL.

## Планируемая архитектура

Logs module должен состоять из:

- profiles с путями логов для разных устройств;
- scenarios для скачивания или сбора logs;
- processors для нормализации, архивации и импорта.

Пример будущего flow:

```text
Scheduler -> download_device_log -> TFTP/FTP/SFTP -> archive -> log_normalize -> loki_import
```

## Планируемые scenarios

- `download_device_log`;
- `download_alarm_log`;
- `download_event_log`;
- `collect_syslog_snapshot`;
- `show_log_tail`.

## Планируемые processors

- `log_archive`;
- `log_normalize`;
- `log_metadata`;
- `loki_import`;
- `log_retention_cleanup`.

## Вопросы перед реализацией

Перед кодом нужно собрать по каждому типу оборудования:

- где лежит log;
- какой transport нужен;
- какой формат файла;
- как определить дату/время события;
- сколько хранится log на устройстве;
- нужно ли удалять файл после скачивания.

