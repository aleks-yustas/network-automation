#!/usr/bin/env python3
"""
PMON downloader — скачивает ежедневные логи с РРС по TFTP.

Использование:
  python downloader.py                # скачать за вчера (все таргеты)
  python downloader.py --retry        # повторить только failed/pending
  python downloader.py --date 20260629  # конкретная дата
  python downloader.py --import-dir /path/to/raw  # импортировать уже скачанные файлы в БД
"""

import argparse
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "state.db"
PROFILES_FILE = BASE_DIR / "device_profiles.yml"

TFTP_TIMEOUT = 10  # секунды
MAX_ATTEMPTS = 4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# БД
# ---------------------------------------------------------------------------

def open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            ip          TEXT NOT NULL,
            date        TEXT NOT NULL,   -- YYYYMMDD
            status      TEXT NOT NULL,   -- pending | ok | empty | error
            attempts    INTEGER NOT NULL DEFAULT 0,
            last_try    TEXT,
            file_size   INTEGER,
            remote_path TEXT,
            PRIMARY KEY (ip, date)
        )
    """)
    conn.commit()
    return conn


def upsert_pending(conn: sqlite3.Connection, ip: str, date_str: str, remote_path: str):
    conn.execute("""
        INSERT INTO downloads (ip, date, status, remote_path)
        VALUES (?, ?, 'pending', ?)
        ON CONFLICT (ip, date) DO NOTHING
    """, (ip, date_str, remote_path))
    conn.commit()


def update_status(conn: sqlite3.Connection, ip: str, date_str: str,
                  status: str, file_size: int | None = None):
    conn.execute("""
        UPDATE downloads
        SET status = ?, attempts = attempts + 1,
            last_try = datetime('now', 'localtime'),
            file_size = ?
        WHERE ip = ? AND date = ?
    """, (status, file_size, ip, date_str))
    conn.commit()


def get_pending(conn: sqlite3.Connection, date_str: str) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT * FROM downloads
        WHERE date = ? AND status IN ('pending', 'error') AND attempts < ?
    """, (date_str, MAX_ATTEMPTS)).fetchall()


# ---------------------------------------------------------------------------
# Конфиг
# ---------------------------------------------------------------------------

def load_profiles() -> dict:
    with open(PROFILES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_targets(targets_file: Path, profiles: dict) -> list[dict]:
    """
    Парсит Prometheus SD файл:
      - targets: [ip, ...]
        labels:
          site: ...
          device: ...
    Возвращает список dict{ip, site, location, region, device, remote_path}.
    """
    with open(targets_file, encoding="utf-8") as f:
        groups = yaml.safe_load(f)

    targets = []
    for group in groups:
        labels = group.get("labels", {})
        device = labels.get("device", "")
        profile = profiles.get(device)
        if profile is None:
            log.warning("Нет профиля для device=%r, пропускаем", device)
            continue
        for ip in group.get("targets", []):
            ip = ip.strip()
            targets.append({
                "ip": ip,
                "device": device,
                "profile": profile,
                "site": labels.get("site", ""),
                "location": labels.get("location", ""),
                "region": labels.get("region", ""),
            })
    return targets


# ---------------------------------------------------------------------------
# TFTP
# ---------------------------------------------------------------------------

def tftp_get(ip: str, remote_path: str, local_path: Path) -> bool:
    """
    Скачивает файл через tftp-hpa.
    tftp -g -r {remote} -l {local} {host}
    Возвращает True при успехе.
    """
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Скачиваем во временный файл — не затираем старый при ошибке
    tmp = local_path.with_suffix(".tmp")
    try:
        result = subprocess.run(
            ["tftp", "-g", "-r", remote_path, "-l", str(tmp), ip],
            timeout=TFTP_TIMEOUT,
            capture_output=True,
        )
        if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(local_path)
            return True
        tmp.unlink(missing_ok=True)
        return False
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        log.debug("Таймаут: %s %s", ip, remote_path)
        return False
    except FileNotFoundError:
        log.error("tftp не найден. Установите: apt install tftp-hpa")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Валидация
# ---------------------------------------------------------------------------

def validate(data: bytes, profile: dict) -> str:
    """Возвращает 'ok' | 'empty' | 'error'."""
    h = profile["header_size"]
    r = profile["record_size"]
    if len(data) <= h:
        return "empty"
    payload = len(data) - h
    if payload % r != 0:
        return "error"
    return "ok"


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def download_one(conn: sqlite3.Connection, ip: str, date_str: str,
                 remote_path: str, profile: dict) -> str:
    """Скачивает один файл. Возвращает итоговый статус."""
    filename = remote_path.split("/")[-1]
    local_path = DATA_DIR / ip / filename

    log.info("↓ %s  %s", ip, remote_path)

    ok = tftp_get(ip, remote_path, local_path)
    if not ok:
        update_status(conn, ip, date_str, "error")
        log.warning("✗ %s  %s", ip, remote_path)
        return "error"

    data = local_path.read_bytes()
    status = validate(data, profile)
    update_status(conn, ip, date_str, status, file_size=len(data))

    if status == "ok":
        records = (len(data) - profile["header_size"]) // profile["record_size"]
        log.info("✓ %s  %d байт  %d записей", ip, len(data), records)
    elif status == "empty":
        log.info("○ %s  пустой файл (%d байт)", ip, len(data))
    else:
        log.warning("⚠ %s  размер не кратен record_size (%d байт)", ip, len(data))

    return status


def get_done(conn: sqlite3.Connection, date_str: str) -> set[str]:
    """IP-адреса с финальным статусом (ok/empty) — повторять не нужно."""
    rows = conn.execute("""
        SELECT ip FROM downloads WHERE date = ? AND status IN ('ok', 'empty')
    """, (date_str,)).fetchall()
    return {r["ip"] for r in rows}


def run_download(date_str: str, targets: list[dict], conn: sqlite3.Connection,
                 retry_only: bool = False):
    if retry_only:
        pending = {(r["ip"], r["date"]): r for r in get_pending(conn, date_str)}
        targets = [t for t in targets if (t["ip"], date_str) in pending]
        log.info("Retry: %d таргетов", len(targets))
    else:
        done = get_done(conn, date_str)
        skipped = [t for t in targets if t["ip"] in done]
        targets = [t for t in targets if t["ip"] not in done]
        if skipped:
            log.info("Пропущено (уже скачаны): %d таргетов", len(skipped))
        log.info("Загрузка за %s: %d таргетов", date_str, len(targets))

    for t in targets:
        profile = t["profile"]
        remote_path = profile["path_template"].format(date=date_str)
        upsert_pending(conn, t["ip"], date_str, remote_path)
        download_one(conn, t["ip"], date_str, remote_path, profile)


# ---------------------------------------------------------------------------
# Импорт уже скачанных файлов
# ---------------------------------------------------------------------------

def import_existing(import_dir: Path, conn: sqlite3.Connection,
                    targets: list[dict], profiles: dict):
    """
    Импортирует уже скачанные raw-файлы в state.db и перекладывает их
    в data/raw/{ip}/ если они ещё не там.
    Структура source: {import_dir}/{ip}/{filename}
    """
    target_map = {t["ip"]: t for t in targets}
    imported = skipped = 0

    for ip_dir in sorted(import_dir.iterdir()):
        if not ip_dir.is_dir():
            continue
        ip = ip_dir.name
        t = target_map.get(ip)
        if t is None:
            log.warning("IP %s не найден в targets.yml, пропускаем", ip)
            continue
        profile = t["profile"]

        for src in sorted(ip_dir.glob("*.pm")):
            # Извлекаем дату из имени файла (daily-dmr-YYYYMMDD.pm или daily-YYYYMMDD.pm)
            stem = src.stem  # daily-dmr-20200804 или daily-20200804
            parts = stem.rsplit("-", 1)
            if len(parts) != 2 or not parts[1].isdigit() or len(parts[1]) != 8:
                log.warning("Не удалось извлечь дату из %s", src.name)
                continue
            date_str = parts[1]

            dst = DATA_DIR / ip / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)

            if not dst.exists():
                import shutil
                shutil.copy2(src, dst)

            data = dst.read_bytes()
            status = validate(data, profile)
            conn.execute("""
                INSERT INTO downloads (ip, date, status, attempts, last_try, file_size, remote_path)
                VALUES (?, ?, ?, 1, datetime('now','localtime'), ?, ?)
                ON CONFLICT (ip, date) DO UPDATE SET
                    status = excluded.status,
                    file_size = excluded.file_size
            """, (ip, date_str, status,
                  len(data),
                  profile["path_template"].format(date=date_str)))
            imported += 1

    conn.commit()
    log.info("Импорт завершён: %d файлов", imported)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PMON downloader")
    parser.add_argument("--targets", required=True, metavar="FILE",
                        help="Путь к Prometheus SD targets.yml")
    parser.add_argument("--date", help="Дата YYYYMMDD (по умолчанию — вчера)")
    parser.add_argument("--retry", action="store_true",
                        help="Повторить только failed/pending")
    parser.add_argument("--import-dir", metavar="DIR",
                        help="Импортировать существующие raw-файлы из директории")
    args = parser.parse_args()

    if args.date:
        date_str = args.date
    else:
        date_str = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    profiles = load_profiles()
    targets = load_targets(Path(args.targets), profiles)
    conn = open_db()

    if args.import_dir:
        import_existing(Path(args.import_dir), conn, targets, profiles)
    else:
        run_download(date_str, targets, conn, retry_only=args.retry)


if __name__ == "__main__":
    main()
