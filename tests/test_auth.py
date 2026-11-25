"""Login, logout, sessão e proteção CSRF."""

import pytest

from app.core import User
from support import SUPERADMIN_EMAIL, TEST_PASSWORD

PROTECTED_PAGES = [
    "/dashboard",
    "/manage",
    "/portaria",
    "/usuarios",
    "/conta",
    "/condominios/1",
    "/links/1/qr.png",
]

# Todo POST que muda dados, com os campos obrigatórios (senão o FastAPI responde
# 422 antes de chegar na verificação de login/CSRF).
STATE_CHANGING_POSTS = [
    ("/condos", {"name": "Nova"}),
    ("/condos/1/active", {"active": "0"}),
    ("/gates", {"condo_id": 1, "name": "x"}),
    ("/gates/1/update", {"name": "x"}),
    ("/gates/1/active", {"active": "0"}),
    ("/houses", {"condo_id": 1, "block": "A", "number": "1", "lat": "1", "lng": "1"}),
    ("/houses/1/update", {"block": "A", "number": "1", "lat": "1", "lng": "1"}),
    ("/houses/1/active", {"active": "0"}),
    ("/houses/1/route", {"geometry": ""}),
    (
        "/users",
        {
            "condo_id": 1, "name": "x", "email": "x@x.x",
            "password": "uma-senha-longa-123", "role": "porter",
        },
    ),
    ("/users/1/active", {"active": "0"}),
    ("/users/1/password", {"password": "uma-senha-longa-123"}),
    (
        "/conta/senha",
        {
            "current_password": "a",
            "new_password": "uma-senha-longa-123",
            "confirm_password": "uma-senha-longa-123",
        },
    ),
    ("/links", {"house_id": 1}),
    ("/links/1/revoke", {}),
    ("/links/1/reactivate", {}),
    ("/links/1/delete", {}),
]


# --- visitante -------------------------------------------------------------


@pytest.mark.parametrize("path", PROTECTED_PAGES)
def test_anonymous_cannot_open_protected_pages(new_browser, path):
    assert new_browser().get(path).status_code == 401


@pytest.mark.parametrize("path, data", STATE_CHANGING_POSTS)
def test_anonymous_cannot_change_anything(new_browser, store, path, data):
    response = new_browser().post(path, **data)
    assert response.status_code == 401
    assert sum(store.counts().values()) == 0


def test_login_page_is_public(new_browser):
    assert new_browser().get("/login").status_code == 200


# --- CSRF ------------------------------------------------------------------


@pytest.mark.parametrize("path, data", STATE_CHANGING_POSTS)
def test_every_state_changing_post_rejects_a_bad_csrf_token(world, store, path, data):
    before = store.counts()
    response = world.root.post(path, token="token-errado", **data)
    assert response.status_code == 403
    assert store.counts() == before


def test_post_without_csrf_field_is_rejected(world, store):
    before = store.counts()
    response = world.a.admin.post(
        "/houses", token=None,
        condo_id=world.a.condo_id, block="Z", number="9", lat="1", lng="1",
    )
    assert response.status_code == 422
    assert store.counts() == before


def test_csrf_token_from_another_session_is_rejected(world, store, new_browser):
    stolen = new_browser().csrf()
    before = store.counts()
    response = world.a.admin.post(
        "/houses", token=stolen,
        condo_id=world.a.condo_id, block="Z", number="9", lat="1", lng="1",
    )
    assert response.status_code == 403
    assert store.counts() == before


def test_login_requires_csrf(world, new_browser):
    response = new_browser().post(
        "/login", token="errado", email=SUPERADMIN_EMAIL, password=TEST_PASSWORD
    )
    assert response.status_code == 403


def test_logout_requires_csrf(world):
    admin = world.a.admin
    assert admin.post("/logout", token="errado").status_code == 403
    assert admin.get("/dashboard").status_code == 200  # continua logado


# --- login e logout --------------------------------------------------------


def test_login_redirects_to_dashboard(world, new_browser):
    browser = new_browser()
    response = browser.login(world.a.admin.email)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert browser.get("/dashboard").status_code == 200


def test_login_normalizes_the_email(world, new_browser):
    browser = new_browser()
    response = browser.login("  ADMIN-ALFA@Teste.Local ")
    assert response.status_code == 303


@pytest.mark.parametrize(
    "email, password",
    [
        ("admin-alfa@teste.local", "senha-errada-123"),
        ("ninguem@teste.local", TEST_PASSWORD),
    ],
    ids=["wrong-password", "unknown-user"],
)
def test_bad_credentials_show_the_same_generic_error(world, new_browser, email, password):
    browser = new_browser()
    response = browser.login(email, password)
    assert response.status_code == 200
    assert "E-mail ou senha inválidos." in response.text
    assert browser.get("/dashboard").status_code == 401


def test_inactive_user_cannot_log_in(world, store, new_browser):
    store.update(User, world.a.porter.user_id, active=False)
    response = new_browser().login(world.a.porter.email)
    assert response.status_code == 200
    assert "E-mail ou senha inválidos." in response.text


def test_deactivating_a_user_ends_the_open_session(world, store):
    assert world.a.porter.get("/dashboard").status_code == 200
    store.update(User, world.a.porter.user_id, active=False)
    assert world.a.porter.get("/dashboard").status_code == 401


def test_logout_ends_the_session(world):
    admin = world.a.admin
    assert admin.get("/dashboard").status_code == 200
    response = admin.post("/logout")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert admin.get("/dashboard").status_code == 401


def test_root_redirects_by_login_state(world, new_browser):
    anonymous = new_browser()
    assert anonymous.get("/").headers["location"] == "/login"
    assert world.a.admin.get("/").headers["location"] == "/dashboard"


def test_password_is_stored_hashed(world, store):
    stored = store.get(User, id=world.a.admin.user_id).password_hash
    assert stored.startswith("pbkdf2_sha256$")
    assert TEST_PASSWORD not in stored
