# Модуль Deployment и systemd

## Назначение

Этот модуль описывает, как NetOps Automation должен жить в production: обычный Linux-сервис в LXC-контейнере Proxmox на Debian 13. Система должна работать полностью offline, без Docker registry, Kubernetes и внешних managed-сервисов.

Файлы:

```text
systemd/netops-worker.service
systemd/netops-scheduler@.service
systemd/netops-scheduler@.timer
```

## Почему systemd

Для такого сервиса systemd достаточно:

- умеет запускать long-running worker;
- умеет перезапускать при падении;
- умеет timers вместо cron;
- хранит logs через journald;
- понятен Linux-администратору;
- работает offline.

## Рекомендуемая структура

```text
/srv/netops/                 # код и venv
/srv/netops/venv/            # Python окружение
/etc/netops/netops.yml       # основной config
/etc/netops/netops.env       # environment/secrets
/etc/netops/schedules.yml    # расписания
/var/lib/netops/artifacts/   # артефакты
```

Пользователь:

```text
netops
```

Он должен иметь доступ к artifact directory и право запускать TFTP/сетевые подключения.

## Worker service

`netops-worker.service` — постоянный процесс.

Он:

- стартует после сети и PostgreSQL;
- читает `/etc/netops/netops.env`;
- запускает `netops-worker`;
- перезапускается при падении.

## Scheduler timer

Scheduler сделан parameterized:

```text
netops-scheduler@<schedule-name>.service
```

Timer запускает конкретное расписание:

```bash
systemctl enable --now netops-scheduler@pasolink-pmon-daily.timer
```

`Persistent=true` нужен, чтобы systemd выполнил пропущенный запуск после простоя контейнера.

## Offline installation

Нужно заранее подготовить:

- Python 3.13+;
- PostgreSQL client libraries;
- `tftp-hpa`;
- wheelhouse для `psycopg[binary]` и `PyYAML`.

В production нельзя рассчитывать на доступ к PyPI.

## План развития

Нужно добавить:

- install script;
- offline build инструкции;
- `logrotate` или journald policy;
- `tmpfiles.d` для рабочих каталогов;
- healthcheck command;
- unit hardening через `ProtectSystem`, `PrivateTmp`, `NoNewPrivileges`.

