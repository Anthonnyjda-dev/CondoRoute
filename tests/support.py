"""Infraestrutura compartilhada pelos testes HTTP.

As variáveis de ambiente abaixo são definidas ANTES de qualquer ``import app``,
porque ``app.core`` cria o engine do banco no momento do import. O banco usado
é sempre um SQLite temporário: a suíte nunca toca o banco de desenvolvimento
nem o MySQL do Docker, e funciona mesmo que o seu shell tenha ``DATABASE_URL``,
``MYSQL_PASSWORD`` etc. definidos.
"""

import atexit
import hashlib
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # app.main monta "app/static" com caminho relativo

TEST_PASSWORD = "senha-de-teste-123"
SUPERADMIN_EMAIL = "superadmin@teste.local"

_TMPDIR = tempfile.mkdtemp(prefix="condoroute-tests-")
os.environ.update(
    DATABASE_URL="sqlite:///" + Path(_TMPDIR, "test.db").as_posix(),
    ADMIN_EMAIL=SUPERADMIN_EMAIL,
    ADMIN_PASSWORD=TEST_PASSWORD,
    SESSION_SECRET="segredo-de-teste-" + "x" * 32,
    SESSION_HTTPS="false",  # o TestClient usa http://testserver
    PUBLIC_BASE_URL="http://localhost:8000",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import core, main  # noqa: E402


def _cleanup():
    core.engine.dispose()
    shutil.rmtree(_TMPDIR, ignore_errors=True)


atexit.register(_cleanup)

# Escritas que só admin/superadmin podem fazer. Cada item: (caminho, campos).
# O campo condo_id é acrescentado pelo teste.
STRUCTURE_WRITES = [
    pytest.param(
        "/houses",
        {"block": "Z", "number": "9", "lat": "-10.7", "lng": "-37.4"},
        id="house",
    ),
    pytest.param("/gates", {"name": "Nova portaria"}, id="gate"),
    pytest.param(
        "/users",
        {
            "name": "Novo porteiro",
            "email": "novo@teste.local",
            "password": "uma-senha-longa-123",
            "role": "porter",
        },
        id="user",
    ),
]

_AUTO = object()
_password_hash = None


def password_hash():
    """Hash de TEST_PASSWORD no mesmo formato de core.hash_password, porém com
    1.000 iterações em vez de 310.000. verify_password lê o número de iterações
    do próprio hash, então o login passa pelo código real, mas cada login de
    teste leva milissegundos em vez de ~0,1 s. (hash_password em si é coberto
    por test_core.py e pelos testes que criam usuários pelo formulário.)"""
    global _password_hash
    if _password_hash is None:
        salt = "00" * 16
        digest = hashlib.pbkdf2_hmac(
            "sha256", TEST_PASSWORD.encode(), bytes.fromhex(salt), 1000
        ).hex()
        _password_hash = f"pbkdf2_sha256$1000${salt}${digest}"
    return _password_hash


def select_options(html, select_id):
    """Trecho HTML de um <select id=...>, para conferir que opções a tela oferece."""
    start = html.index(f'id="{select_id}"')
    return html[start : html.index("</select>", start)]


def has_origin(html):
    """A página pública tem o parâmetro origin= nos links do Google Maps?
    (Não basta procurar "origin=": o Leaflet traz o atributo "crossorigin=".)"""
    return bool(re.search(r"(?:\?|&amp;|&)origin=", html))


class Browser:
    """Navegador simulado: guarda os cookies de sessão e cuida do token CSRF."""

    def __init__(self):
        # raise_server_exceptions=False: um erro 500 vira resposta, não exceção.
        self.http = TestClient(main.app, raise_server_exceptions=False)

    def get(self, path):
        return self.http.get(path, follow_redirects=False)

    def csrf(self):
        """Token CSRF da sessão atual, lido do formulário da página de login."""
        html = self.http.get("/login").text
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def post(self, path, *, token=_AUTO, **data):
        """POST de formulário. ``token=None`` omite o campo; ``token="x"`` força um valor."""
        if token is _AUTO:
            token = self.csrf()
        if token is not None:
            data["csrf_token"] = token
        return self.http.post(path, data=data, follow_redirects=False)

    def login(self, email, password=TEST_PASSWORD):
        return self.post("/login", email=email, password=password)


class Account:
    """Usuário já gravado no banco; só faz login quando o teste precisa dele."""

    def __init__(self, user_id, email):
        self.user_id = user_id
        self.email = email
        self._browser = None

    @property
    def browser(self):
        if self._browser is None:
            browser = Browser()
            response = browser.login(self.email)
            assert response.status_code == 303, "login de teste falhou"
            self._browser = browser
        return self._browser

    def get(self, path):
        return self.browser.get(path)

    def post(self, path, **kwargs):
        return self.browser.post(path, **kwargs)


class Store:
    """Acesso direto ao banco para preparar e conferir dados nos testes."""

    TABLES = (core.Condo, core.User, core.Gate, core.House, core.Access, core.Audit)

    def get(self, model, **filters):
        with core.SessionLocal() as db:
            return db.query(model).filter_by(**filters).first()

    def rows(self, model, **filters):
        with core.SessionLocal() as db:
            return db.query(model).filter_by(**filters).order_by(model.id).all()

    def count(self, model, **filters):
        return len(self.rows(model, **filters))

    def counts(self):
        """Fotografia do número de linhas de cada tabela."""
        return {model.__name__: self.count(model) for model in self.TABLES}

    def update(self, model, ident, **values):
        with core.SessionLocal() as db:
            obj = db.get(model, ident)
            for key, value in values.items():
                setattr(obj, key, value)
            db.commit()

    def add_house(self, condo_id, block, number, lat=-10.7, lng=-37.4):
        with core.SessionLocal() as db:
            house = core.House(
                condo_id=condo_id, block=block, number=number, lat=lat, lng=lng
            )
            db.add(house)
            db.commit()
            return house.id

    def add_gate(self, condo_id, name, lat=None, lng=None):
        with core.SessionLocal() as db:
            gate = core.Gate(condo_id=condo_id, name=name, lat=lat, lng=lng)
            db.add(gate)
            db.commit()
            return gate.id

    def add_user(self, condo_id, role, email):
        """Cria um usuário (senha = TEST_PASSWORD) e devolve uma Account."""
        with core.SessionLocal() as db:
            user = core.User(
                condo_id=condo_id,
                name=email.split("@")[0],
                email=email,
                password_hash=password_hash(),
                role=role,
            )
            db.add(user)
            db.commit()
            return Account(user.id, email)

    def add_link(self, condo_id, house_id, *, gate_id=None, active=True):
        token = secrets.token_urlsafe(32)
        with core.SessionLocal() as db:
            link = core.Access(
                condo_id=condo_id,
                house_id=house_id,
                gate_id=gate_id,
                token=token,
                active=active,
            )
            db.add(link)
            db.commit()
            return SimpleNamespace(id=link.id, token=token)


store = Store()


def build_world():
    """Dois condomínios independentes, cada um com portaria, casa, admin e porteiro."""
    with core.SessionLocal() as db:
        root = core.User(
            name="Administrador",
            email=SUPERADMIN_EMAIL,
            password_hash=password_hash(),
            role="superadmin",
        )
        db.add(root)
        db.flush()
        world = SimpleNamespace(root=Account(root.id, root.email))

        for key, suffix in (("a", "alfa"), ("b", "beta")):
            condo = core.Condo(name=f"Condominio {suffix.capitalize()}")
            db.add(condo)
            db.flush()
            gate = core.Gate(
                condo_id=condo.id, name=f"Entrada {suffix}", lat=-10.70, lng=-37.41
            )
            house = core.House(
                condo_id=condo.id,
                block="A",
                number="01",
                lat=-10.7012942,
                lng=-37.4131006,
                reference=f"Referencia {suffix}",
            )
            people = {
                role: core.User(
                    condo_id=condo.id,
                    name=f"{role} {suffix}",
                    email=f"{role}-{suffix}@teste.local",
                    password_hash=password_hash(),
                    role=role,
                )
                for role in ("admin", "porter")
            }
            db.add_all([gate, house, *people.values()])
            db.flush()
            setattr(
                world,
                key,
                SimpleNamespace(
                    condo_id=condo.id,
                    name=condo.name,
                    gate_id=gate.id,
                    house_id=house.id,
                    admin=Account(people["admin"].id, people["admin"].email),
                    porter=Account(people["porter"].id, people["porter"].email),
                ),
            )
        db.commit()
    return world
