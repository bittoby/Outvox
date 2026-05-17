"""
Database connection helpers.

This module is the single source of truth for building SQL Server connection
strings. Previously three places (``db_service.py``, ``core/schema.py``,
``repositories/base.py``) each had their own subtly different implementation —
notably ``BaseRepository`` did not handle LocalDB at all, so repository code
would fail against a local developer database. Consolidating them removes that
class of drift.

Environment variables consumed:

* ``SQLServer``   — host or instance (``localhost,1433``, ``(localdb)\\MSSQLLocalDB``)
* ``SQLDatabase`` — database name (required for non-master connections)
* ``SQLUser``     — username (only required for remote servers)
* ``SQLPassword`` — password (only required for remote servers)

If ``SQLServer`` contains ``localdb`` (case-insensitive) we use Windows
Authentication; otherwise we use SQL Server authentication.
"""

from __future__ import annotations

import os
from typing import Optional

ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


class DatabaseConfigurationError(RuntimeError):
    """Raised when required SQL Server environment variables are missing."""


def _is_localdb(server: str) -> bool:
    return "localdb" in (server or "").lower()


def build_sqlserver_connection_string(
    database: Optional[str] = None,
    *,
    server: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Return a pyodbc connection string for the configured SQL Server.

    Parameters mirror the environment variables but can be supplied explicitly
    for tests or for connecting to ``master`` during schema bootstrap. When a
    parameter is ``None`` the environment variable is used.

    Raises ``DatabaseConfigurationError`` if a required value is missing.
    """
    resolved_server = (server if server is not None else os.getenv("SQLServer", "")).strip()
    resolved_database = (database if database is not None else os.getenv("SQLDatabase", "")).strip()

    if not resolved_server:
        raise DatabaseConfigurationError("SQLServer environment variable is not set")
    if not resolved_database:
        raise DatabaseConfigurationError("SQLDatabase (or explicit `database`) is required")

    parts = [
        f"DRIVER={{{ODBC_DRIVER}}}",
        "TrustServerCertificate=yes",
        f"SERVER={resolved_server}",
        f"DATABASE={resolved_database}",
    ]

    if _is_localdb(resolved_server):
        parts.append("Trusted_Connection=yes")
    else:
        resolved_user = (user if user is not None else os.getenv("SQLUser", "")).strip()
        resolved_password = password if password is not None else os.getenv("SQLPassword", "")
        if not resolved_user or not resolved_password:
            raise DatabaseConfigurationError(
                "SQLUser and SQLPassword are required for remote SQL Server connections"
            )
        parts.append(f"UID={resolved_user}")
        parts.append(f"PWD={resolved_password}")

    return ";".join(parts) + ";"


def build_master_connection_string(
    *,
    server: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Connection string against the ``master`` database (for ``CREATE DATABASE``)."""
    return build_sqlserver_connection_string(
        database="master",
        server=server,
        user=user,
        password=password,
    )
