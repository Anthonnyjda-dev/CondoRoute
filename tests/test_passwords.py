"""Troca da própria senha (/conta) e redefinição feita por um administrador."""

import pytest

from app.core import Audit, User
from support import TEST_PASSWORD

NEW_PASSWORD = "outra-senha-bem-longa-9"


def change(account, **overrides):
    data = dict(
        current_password=TEST_PASSWORD,
        new_password=NEW_PASSWORD,
        confirm_password=NEW_PASSWORD,
    )
    data.update(overrides)
    return account.post("/conta/senha", **data)


def can_log_in(new_browser, email, password):
    return new_browser().login(email, password).status_code == 303


# --- própria senha ---------------------------------------------------------


@pytest.mark.parametrize("role", ["admin", "porter"])
def test_account_page_is_available_to_every_role(world, role):
    account = getattr(world.a, role)
    response = account.get("/conta")
    assert response.status_code == 200
    assert account.email in response.text


def test_changing_the_password_works_and_keeps_the_session(world, store, new_browser):
    admin = world.a.admin
    assert change(admin).status_code == 303

    assert not can_log_in(new_browser, admin.email, TEST_PASSWORD)
    assert can_log_in(new_browser, admin.email, NEW_PASSWORD)
    assert admin.get("/dashboard").status_code == 200  # sessão atual continua válida
    assert admin.get("/conta").status_code == 200
    assert "user.password_change" in [e.action for e in store.rows(Audit)]


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"current_password": "errada-errada-123"}, "senha atual está incorreta"),
        ({"confirm_password": "diferente-diferente-1"}, "confirmação não confere"),
        ({"new_password": "curta", "confirm_password": "curta"}, "12 caracteres"),
        (
            {"new_password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
            "diferente da atual",
        ),
    ],
    ids=["wrong-current", "mismatch", "too-short", "same-as-current"],
)
def test_invalid_password_changes_are_explained_and_ignored(
    world, store, new_browser, overrides, message
):
    admin = world.a.admin
    before = store.get(User, id=admin.user_id).password_hash

    response = change(admin, **overrides)

    assert response.status_code == 422
    assert message in response.text  # a própria página mostra o erro, não um JSON
    assert store.get(User, id=admin.user_id).password_hash == before
    assert can_log_in(new_browser, admin.email, TEST_PASSWORD)


def test_password_change_never_logs_the_passwords(world, store):
    change(world.a.admin)
    details = " ".join(e.detail for e in store.rows(Audit))
    assert NEW_PASSWORD not in details
    assert TEST_PASSWORD not in details


# --- redefinição por administrador ----------------------------------------


def test_admin_resets_a_porters_password(world, store, new_browser):
    porter = world.a.porter
    response = world.a.admin.post(
        f"/users/{porter.user_id}/password", password=NEW_PASSWORD
    )

    assert response.status_code == 303
    assert can_log_in(new_browser, porter.email, NEW_PASSWORD)
    assert not can_log_in(new_browser, porter.email, TEST_PASSWORD)
    events = [e for e in store.rows(Audit) if e.action == "user.password_reset"]
    assert [e.detail for e in events] == [porter.email]
    assert NEW_PASSWORD not in events[0].detail


def test_password_reset_enforces_the_policy(world, store, new_browser):
    porter = world.a.porter
    response = world.a.admin.post(f"/users/{porter.user_id}/password", password="curta")
    assert response.status_code == 422
    assert can_log_in(new_browser, porter.email, TEST_PASSWORD)


def test_superadmin_resets_an_admins_password(world, store, new_browser):
    admin = world.b.admin
    response = world.root.post(f"/users/{admin.user_id}/password", password=NEW_PASSWORD)
    assert response.status_code == 303
    assert can_log_in(new_browser, admin.email, NEW_PASSWORD)


def test_users_page_offers_reset_only_for_manageable_users(world):
    html = world.a.admin.get("/usuarios").text
    assert f'action="/users/{world.a.porter.user_id}/password"' in html
    assert f'action="/users/{world.a.admin.user_id}/password"' not in html  # a si mesmo
