# Модуль Inventory

## Назначение

Inventory описывает оборудование, с которым работает система. Это замена hardcoded IP-списков из старых batch-скриптов. Устройство должно быть описано один раз в PostgreSQL, а разные schedules будут выбирать его по vendor, model, site, region или metadata.

Основная таблица:

```text
netops_devices
```

## Почему inventory важен

В старом подходе список IP был частью конкретного `.bat` файла. Это мешает сопровождению: один и тот же IP может оказаться в нескольких местах, тип устройства спрятан в комментариях или порядке циклов, а изменение списка требует редактировать код.

В новой архитектуре список устройств — данные, а не код.

## Основные поля устройства

`name` — стабильное человекочитаемое имя. Его удобно показывать в отчётах.

`vendor` — производитель или крупная группа. Например, `NEC`.

`model` — модель или семейство. Например, `CX2200` или `Pasolink`.

`mgmt_ip` — IP-адрес управления.

`site` и `region` — эксплуатационные признаки для отбора.

`enabled` — участвует ли устройство в автоматизации.

`metadata` — JSONB для полей, которые нужны конкретным модулям.

## PMON и поле `device`

Для PMON важно знать тип РРС. Пользователь уточнил: это поле будет называться `device` в описании всех targets.

Пример:

```json
{"device": "Pasolink NEO/c"}
```

Сценарий `download_pmon` использует это поле, чтобы выбрать path template:

- `Pasolink NEO/c` -> `/pmon/daily-dmr-{date}.pm`
- `Pasolink NEO` -> `/pmon/daily-{date}.pm`

## Как scheduler использует inventory

Scheduler выбирает только `enabled = true` устройства. Затем применяет фильтр из schedule:

```yaml
device_selector:
  vendor: "NEC"
  model: "Pasolink"
```

После выбора scheduler создаёт payload, куда попадают host, target info и metadata.

## План развития

Нужно добавить импорт из Prometheus file_sd YAML, потому что текущая инфраструктура уже использует targets с labels. Импорт должен маппить:

- `targets` -> `mgmt_ip`;
- `labels.site` -> `site`;
- `labels.region` -> `region`;
- `labels.device` -> `metadata.device`;
- другие labels -> `metadata`.

Также нужен validator inventory: неизвестный PMON device, пустой mgmt_ip, дубли IP, disabled без причины.

