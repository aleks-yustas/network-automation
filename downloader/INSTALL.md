# Установка PMON Downloader

## Требования

- Debian 13 Trixie
- Python 3.13 (устанавливается офлайн, см. раздел 4)
- Сетевой доступ к РРС по UDP/69 (TFTP)

---

## 1. Установка скрипта

### Скопировать файлы

```bash
sudo mkdir -p /srv/pmon
sudo cp downloader.py device_profiles.yml /srv/pmon/
sudo chown -R $USER:$USER /srv/pmon
```

### Создать виртуальное окружение и установить зависимости

```bash
cd /srv/pmon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Зависимости Python:

| Пакет | Версия | Назначение |
|-------|--------|------------|
| PyYAML | >=6.0 | Парсинг targets.yml и device_profiles.yml |

Все остальные модули (`sqlite3`, `subprocess`, `pathlib`, `argparse`) входят в стандартную библиотеку Python.

---

## 2. Структура директорий

После установки структура будет выглядеть так:

```
/srv/pmon/
├── downloader.py          # основной скрипт
├── device_profiles.yml    # профили устройств
├── venv/                  # виртуальное окружение Python
├── state.db               # SQLite база (создаётся автоматически)
└── data/
    └── raw/
        ├── 172.18.0.70/
        │   ├── daily-dmr-20260629.pm
        │   └── daily-dmr-20260630.pm
        ├── 172.18.0.107/
        │   └── ...
        └── ...
```

---

## 3. Офлайн-установка (Debian 13 Trixie)

Все шаги выполняются на **отдельной машине с Debian 13 и интернетом**, затем файлы переносятся на сервер.

> Важно: скачивать пакеты нужно именно на Debian 13, иначе версии пакетов не совпадут.

### Шаг A. Скачать .deb пакеты с зависимостями

Самый надёжный способ получить полное дерево зависимостей — `apt-get install --download-only`. Он сам разрешает все транзитивные зависимости и складывает .deb в кэш.

```bash
sudo apt update

# Скачать все пакеты в /var/cache/apt/archives/ без установки
sudo apt-get install --download-only -y \
  python3 \
  python3.13 \
  python3.13-venv \
  python3-pip \
  python3-pip-whl \
  tftp-hpa

# Собрать всё в одну папку
mkdir -p pmon-packages/debs
cp /var/cache/apt/archives/*.deb pmon-packages/debs/
```

Что войдёт в архив (основные пакеты, точный список зависит от состояния системы):

| Пакет | Назначение |
|-------|------------|
| `python3_*.deb` | мета-пакет Python 3 |
| `python3.13_*.deb` | интерпретатор Python 3.13 |
| `python3.13-minimal_*.deb` | минимальный рантайм |
| `libpython3.13_*.deb` | разделяемая библиотека Python |
| `libpython3.13-stdlib_*.deb` | стандартная библиотека |
| `libpython3.13-minimal_*.deb` | минимальная stdlib |
| `python3.13-venv_*.deb` | модуль venv |
| `python3-pip_*.deb` | pip |
| `python3-pip-whl_*.deb` | pip в формате wheel (нужен для офлайн-установки) |
| `tftp-hpa_*.deb` | TFTP-клиент |
| `libreadline8_*.deb` | зависимость tftp-hpa |

### Шаг B. Скачать Python wheel для PyYAML

```bash
pip3 download PyYAML \
  --dest pmon-packages/wheels \
  --platform manylinux2014_x86_64 \
  --python-version 313 \
  --only-binary=:all:
```

Файл который появится:

```
pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64...whl
```

> Если архитектура ARM — замените `manylinux2014_x86_64` на `manylinux2014_aarch64`.

### Шаг C. Перенести на сервер

```bash
tar -czf pmon-packages.tar.gz pmon-packages/
# Скопировать pmon-packages.tar.gz на сервер через scp, флешку и т.п.
```

На сервере:

```bash
tar -xzf pmon-packages.tar.gz
```

### Шаг D. Установить на сервере

```bash
# Установить все .deb (dpkg сам разберёт порядок)
sudo dpkg -i pmon-packages/debs/*.deb

# Если dpkg сообщит о неудовлетворённых зависимостях —
# значит какой-то пакет уже есть в системе, это нормально.
# Проверить что всё ок:
python3 --version   # должно быть 3.13.x
tftp --version
```

```bash
# Создать venv и установить PyYAML из wheel
sudo mkdir -p /srv/pmon
cd /srv/pmon
python3 -m venv venv
venv/bin/pip install --no-index --find-links ~/pmon-packages/wheels PyYAML
```

Проверить:

```bash
venv/bin/python -c "import yaml; print(yaml.__version__)"
```

---

## 4. Файл targets.yml

Скрипт читает файл таргетов напрямую из расположения Prometheus — дублировать не нужно. Формат файла — Prometheus SD:

```yaml
- targets:
    - 172.18.0.114
  labels:
    site: 6169
    location: Rassvet
    region: Rostov
    device: Pasolink NEO/c
```

Поле `device` должно совпадать с ключом в `device_profiles.yml`. Если устройство не найдено в профилях — оно пропускается с предупреждением в логе.

---

## 5. Настройка расписания (cron)

```bash
crontab -e
```

Добавить строки:

```cron
# PMON — основной запуск в 05:00
0 5  * * * /srv/pmon/venv/bin/python /srv/pmon/downloader.py --targets /etc/prometheus/targets.yml

# PMON — повторные попытки для недоступных РРС
0 10 * * * /srv/pmon/venv/bin/python /srv/pmon/downloader.py --targets /etc/prometheus/targets.yml --retry
0 15 * * * /srv/pmon/venv/bin/python /srv/pmon/downloader.py --targets /etc/prometheus/targets.yml --retry
0 20 * * * /srv/pmon/venv/bin/python /srv/pmon/downloader.py --targets /etc/prometheus/targets.yml --retry
```

---

## 6. Импорт существующих данных

Если есть архив файлов, скачанных старым bat/sh скриптом, их можно импортировать в базу одной командой. Скрипт скопирует файлы в `data/raw/` и зарегистрирует их в `state.db`.

Ожидаемая структура исходной директории:

```
/path/to/existing/raw/
├── 172.18.0.70/
│   ├── daily-dmr-20260101.pm
│   └── ...
├── 172.18.0.107/
│   └── ...
```

Команда импорта:

```bash
cd /srv/pmon
source venv/bin/activate
python downloader.py \
  --targets /etc/prometheus/targets.yml \
  --import-dir /path/to/existing/raw
```

---

## 7. Проверка работы

### Тестовый запуск (вчерашняя дата)

```bash
cd /srv/pmon
source venv/bin/activate
python downloader.py --targets /etc/prometheus/targets.yml
```

### Проверить состояние загрузок в БД

```bash
sqlite3 /srv/pmon/state.db \
  "SELECT ip, date, status, attempts, file_size FROM downloads ORDER BY date DESC, ip LIMIT 20;"
```

### Посмотреть только упавшие

```bash
sqlite3 /srv/pmon/state.db \
  "SELECT ip, date, attempts FROM downloads WHERE status='error' ORDER BY date DESC;"
```

---

## 8. Возможные проблемы

### `tftp не найден`

```bash
sudo apt install tftp-hpa -y
```

### Таймаут при скачивании

РРС недоступна в момент запуска. Скрипт запишет статус `error` и повторит при следующем запуске с `--retry`. Если устройство недоступно весь день — останется `error`, попытки на следующий день не предпринимаются автоматически (только для той же даты).

### Файл скачался, но статус `error` (размер не кратен record_size)

Возможно, профиль устройства в `device_profiles.yml` указан неверно (неправильный `record_size`). Уточните параметры после анализа расшифрованных файлов.

### Файл скачался, статус `empty` (≤16 байт)

Устройство доступно, но данных за этот день не накопило. Повторные попытки бессмысленны.
