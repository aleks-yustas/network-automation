# Модуль Processor Layer

## Назначение

Processor Layer отвечает за обработку результата после выполнения scenario. Scenario получает данные от устройства, но не должен решать, как их хранить, нормализовать, коммитить в Git или импортировать в Loki. Для этого нужны processors.

Пакет:

```text
netops_automation/processors/
```

## Контракт

Каждый processor реализует:

```python
def process(self, job: Job, result: ScenarioResult) -> ScenarioResult:
    ...
```

Processors выполняются цепочкой. Каждый получает результат предыдущего и может добавить metadata или artifacts.

## Почему processors отделены от scenarios

Один сценарий может использовать разные способы обработки результата. PMON можно просто сохранить как raw-файл, можно декодировать, можно импортировать в PostgreSQL, можно отправить в другую offline-систему. Сценарий скачивания при этом не должен меняться.

То же самое для конфигураций: сначала сохранить файл, потом нормализовать, потом положить в Git, потом построить diff. Это разные processors.

## Текущие processors

### `archive`

Сохраняет `ScenarioResult.data` на диск.

Путь:

```text
<artifact_dir>/<device_id>/<job_type>/<filename>
```

Имя файла берётся из `result.metadata.artifact_filename`. Если его нет, используется `<job_id>.txt`.

Processor считает SHA256 и добавляет artifact descriptor в `ScenarioResult.artifacts`.

### `postgres_metadata`

Берёт список artifacts из результата и пишет metadata в `netops_artifacts`.

Он не хранит сами байты. Файлы остаются на диске, PostgreSQL хранит путь, checksum, размер и JSON metadata.

## Будущие processors

Для PMON:

- `pmon_decode` — расшифровка records;
- `pmon_quality_check` — проверка 96 интервалов за сутки;
- `pmon_store_timeseries` — запись decoded data в PostgreSQL.

Для конфигураций:

- `config_normalize`;
- `git_commit`;
- `config_diff`.

Для логов:

- `log_normalize`;
- `loki_import`;
- `log_retention`.

## Правила разработки

Processor не должен подключаться к оборудованию. Он работает только с результатом scenario и локальными/серверными хранилищами.

Processor должен быть максимально детерминированным: одинаковый input должен давать одинаковый output. Это упростит повторную обработку artifacts.

## Известный риск

Текущий `archive` path может перезаписать файл с тем же именем для одного device/job_type. Для PMON это частично компенсируется idempotency по target_date, но перед production лучше сделать путь immutable, например добавить дату или job id в структуру.

