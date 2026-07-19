from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


@contextmanager
def connect(dsn: str) -> Iterator[Connection]:
    conn = psycopg.connect(dsn, row_factory=dict_row)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()
