"""Tests for the shared SQL Server connection-string builder.

These tests pin the contract that all three backend call sites
(``db_service``, ``core/schema``, ``repositories/base``) now rely on. They
exercise the LocalDB / remote-auth split that previously diverged between
modules.
"""

import pytest

from core.db import (
    DatabaseConfigurationError,
    build_master_connection_string,
    build_sqlserver_connection_string,
)


def test_remote_server_uses_sql_authentication():
    conn = build_sqlserver_connection_string(
        database="outvox",
        server="db.internal,1433",
        user="svc",
        password="hunter2",
    )

    assert "SERVER=db.internal,1433" in conn
    assert "DATABASE=outvox" in conn
    assert "UID=svc" in conn
    assert "PWD=hunter2" in conn
    assert "Trusted_Connection" not in conn
    assert "ODBC Driver 18 for SQL Server" in conn
    assert conn.endswith(";")


def test_localdb_uses_trusted_connection():
    conn = build_sqlserver_connection_string(
        database="outvox",
        server="(localdb)\\MSSQLLocalDB",
    )

    assert "Trusted_Connection=yes" in conn
    assert "UID=" not in conn
    assert "PWD=" not in conn


def test_master_connection_targets_master_db():
    conn = build_master_connection_string(
        server="db.internal,1433",
        user="svc",
        password="hunter2",
    )

    assert "DATABASE=master" in conn


def test_missing_server_raises():
    with pytest.raises(DatabaseConfigurationError):
        build_sqlserver_connection_string(database="outvox", server="")


def test_missing_database_raises(monkeypatch):
    monkeypatch.delenv("SQLDatabase", raising=False)
    with pytest.raises(DatabaseConfigurationError):
        build_sqlserver_connection_string(server="db.internal,1433", user="u", password="p")


def test_remote_without_credentials_raises():
    with pytest.raises(DatabaseConfigurationError):
        build_sqlserver_connection_string(
            database="outvox",
            server="db.internal,1433",
            user="",
            password="",
        )


def test_reads_environment_when_args_omitted(monkeypatch):
    monkeypatch.setenv("SQLServer", "envhost,1433")
    monkeypatch.setenv("SQLDatabase", "envdb")
    monkeypatch.setenv("SQLUser", "envuser")
    monkeypatch.setenv("SQLPassword", "envpw")

    conn = build_sqlserver_connection_string()

    assert "SERVER=envhost,1433" in conn
    assert "DATABASE=envdb" in conn
    assert "UID=envuser" in conn
    assert "PWD=envpw" in conn
