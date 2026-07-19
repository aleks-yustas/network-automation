# Модуль Credentials

## Назначение

Credentials module хранит и выдаёт учётные данные для подключения к оборудованию. Он отделён от schedule, потому что расписание должно описывать работу, а не содержать пароли.

Таблица:

```text
netops_device_credentials
```

## Модель данных

Credential привязан к устройству и назначению:

- `device_id` — устройство;
- `purpose` — для чего нужны данные: `telnet`, `ssh`, `ftp`;
- `username` — имя пользователя;
- `secret` — JSONB с секретами.

Пример:

```sql
INSERT INTO netops_device_credentials (device_id, purpose, username, secret)
VALUES ('...', 'telnet', 'admin', '{"password": "..."}'::jsonb);
```

## Как credentials попадают в задачу

Schedule указывает:

```yaml
credential_purpose: "telnet"
```

Scheduler ищет credential для выбранного устройства и добавляет `username` и поля из `secret` в payload. Scenario получает уже готовый payload и не знает, где именно хранились секреты.

## Почему это не transport responsibility

Transport должен получить уже готовые параметры подключения. Если transport сам начнёт ходить в БД за паролем, он станет зависимым от storage и перестанет быть простым protocol adapter.

## Безопасность

На текущем этапе секреты хранятся в PostgreSQL. Это допустимо для первого offline-варианта, но требует:

- отдельного DB-пользователя;
- минимальных прав;
- строгого доступа к backup'ам PostgreSQL;
- запрета логировать payload целиком;
- ограниченных прав на `/etc/netops/netops.env`.

## План развития

Следующий шаг — шифрование `secret` локальным ключом. Ключ можно хранить в отдельном root-readable файле в `/etc/netops/secret.key`, а worker запускать так, чтобы только пользователь `netops` мог читать нужные файлы.

Позже можно добавить rotation, audit доступа к credential и redaction helper для логов.

