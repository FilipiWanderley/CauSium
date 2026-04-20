from __future__ import annotations
from typing import Any, Dict, List

import clickhouse_connect

from app.core.config import get_settings

_client = None


def get_clickhouse_client():
    global _client
    if _client is None:
        settings = get_settings()
        kwargs: dict = {
            "host": settings.clickhouse_host,
            "port": settings.clickhouse_port,
            "username": settings.clickhouse_user,
            "password": settings.clickhouse_password,
            "database": settings.clickhouse_db,
            "secure": settings.clickhouse_secure,
            "verify": settings.clickhouse_verify,
        }
        # ca_cert pins the server certificate chain. When omitted, the
        # system trust store is used. Minimum TLS version for ClickHouse is
        # enforced server-side via config.xml <disableProtocols>.
        if settings.clickhouse_ca_cert:
            kwargs["ca_cert"] = settings.clickhouse_ca_cert
        _client = clickhouse_connect.get_client(**kwargs)
    return _client


def execute_query(query: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    client = get_clickhouse_client()
    result = client.query(query, parameters=parameters or {})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def insert_rows(table: str, data: List[Dict[str, Any]]) -> None:
    if not data:
        return
    client = get_clickhouse_client()
    columns = list(data[0].keys())
    rows = [[row[col] for col in columns] for row in data]
    client.insert(table, rows, column_names=columns)


def execute_command(statement: str, parameters: Dict[str, Any] | None = None) -> None:
    """Execute a DDL or DML statement (INSERT, DELETE, ALTER, CREATE, etc.)."""
    client = get_clickhouse_client()
    client.command(statement, parameters=parameters or {})
