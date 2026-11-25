"""Inicialização: superadmin inicial, migração leve do banco e guardas de produção."""

import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text

from app import core
from support import ROOT, SUPERADMIN_EMAIL, TEST_PASSWORD


def test_bootstrap_creates_the_superadmin_once_and_no_sample_data(store):
    core.bootstrap()
    core.bootstrap()  # idempotente

    users = store.rows(core.User)
    assert len(users) == 1
    admin = users[0]
    assert (admin.email, admin.role, admin.condo_id) == (SUPERADMIN_EMAIL, "superadmin", None)
    assert core.verify_password(TEST_PASSWORD, admin.password_hash)
    for model in (core.Condo, core.Gate, core.House, core.Access):
        assert store.count(model) == 0  # nenhum dado fictício


def test_bootstrap_rejects_a_short_admin_password(store, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "curta")
    with pytest.raises(RuntimeError):
        core.bootstrap()
    assert store.count(core.User) == 0


def test_bootstrap_without_credentials_creates_no_user(store, monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL")
    monkeypatch.delenv("ADMIN_PASSWORD")
    core.bootstrap()
    assert store.count(core.User) == 0


def test_ensure_schema_adds_the_gate_flag_to_a_legacy_database(store):
    # Banco criado por uma versão anterior: a tabela gates ainda não tinha "active".
    with core.engine.begin() as conn:
        conn.execute(text("DROP TABLE gates"))
        conn.execute(text(
            "CREATE TABLE gates (id INTEGER PRIMARY KEY, condo_id INTEGER, "
            "name VARCHAR(100), lat FLOAT, lng FLOAT)"
        ))
        conn.execute(text("INSERT INTO gates (condo_id, name) VALUES (1, 'Antiga')"))

    core.bootstrap()

    columns = {c["name"] for c in inspect(core.engine).get_columns("gates")}
    assert "active" in columns
    assert store.get(core.Gate, name="Antiga").active is True  # portarias antigas seguem ativas
    core.bootstrap()  # rodar de novo não quebra


def test_health_endpoints(new_browser):
    browser = new_browser()
    assert browser.get("/health").json() == {"status": "ok"}
    assert browser.get("/api/health").json() == {"ok": True}


def import_app(**env):
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        env={**os.environ, **env}, cwd=ROOT, capture_output=True, text=True,
    )


def test_production_refuses_a_weak_session_secret():
    weak = import_app(APP_ENV="production", SESSION_SECRET="curto")
    assert weak.returncode != 0
    assert "SESSION_SECRET inseguro" in weak.stderr

    strong = import_app(APP_ENV="production", SESSION_SECRET="s" * 40)
    assert strong.returncode == 0, strong.stderr
