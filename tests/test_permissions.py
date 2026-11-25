"""O que cada perfil (superadmin, admin, porteiro) pode e não pode fazer."""

import re

import pytest

from app.core import Access, Audit, Condo, Gate, House, User
from support import STRUCTURE_WRITES, TEST_PASSWORD

# {gate}, {house} e {admin} são trocados pelos ids do condomínio Alfa.
MANAGEMENT_POSTS = [
    ("/gates/{gate}/update", {"name": "x"}),
    ("/gates/{gate}/active", {"active": "0"}),
    ("/houses/{house}/update", {"block": "A", "number": "1", "lat": "1", "lng": "1"}),
    ("/houses/{house}/active", {"active": "0"}),
    ("/houses/{house}/route", {"geometry": "1, 1\n2, 2"}),
    ("/users/{admin}/active", {"active": "0"}),
    ("/users/{admin}/password", {"password": "uma-senha-longa-123"}),
]


def snapshot(store, world):
    house = store.get(House, id=world.a.house_id)
    gate = store.get(Gate, id=world.a.gate_id)
    admin = store.get(User, id=world.a.admin.user_id)
    return (
        (house.active, house.block, house.number, house.lat, house.lng, house.route_geometry),
        (gate.active, gate.name, gate.lat, gate.lng),
        (admin.active, admin.password_hash),
    )


def actions(store):
    return [event.action for event in store.rows(Audit)]


# --- porteiro --------------------------------------------------------------


@pytest.mark.parametrize("path, data", STRUCTURE_WRITES)
def test_porter_cannot_register_structure(world, store, path, data):
    before = store.counts()
    response = world.a.porter.post(path, condo_id=world.a.condo_id, **data)
    assert response.status_code == 403
    assert store.counts() == before


def test_porter_cannot_create_condo(world, store):
    assert world.a.porter.post("/condos", name="Condominio Novo").status_code == 403


@pytest.mark.parametrize("path, data", MANAGEMENT_POSTS)
def test_porter_cannot_use_management_endpoints(world, store, path, data):
    before = snapshot(store, world)
    path = path.format(
        gate=world.a.gate_id, house=world.a.house_id, admin=world.a.admin.user_id
    )
    response = world.a.porter.post(path, **data)
    assert response.status_code in (403, 404)
    assert snapshot(store, world) == before


def test_porter_cannot_open_users_page(world):
    assert world.a.porter.get("/usuarios").status_code == 403


def test_porter_sees_structure_pages_without_edit_forms(world):
    assert world.a.porter.get("/manage").status_code == 200
    assert world.a.porter.get("/portaria").status_code == 200
    detail = world.a.porter.get(f"/condominios/{world.a.condo_id}")
    assert detail.status_code == 200
    assert 'action="/houses"' not in detail.text
    assert 'action="/gates"' not in detail.text


def test_porter_can_issue_and_revoke_links(world, store):
    response = world.a.porter.post(
        "/links", house_id=world.a.house_id, gate_id=world.a.gate_id
    )
    assert response.status_code == 303
    link_id = int(response.headers["location"].split("link=")[1])
    assert store.get(Access, id=link_id).active is True

    assert world.a.porter.post(f"/links/{link_id}/revoke").status_code == 303
    assert store.get(Access, id=link_id).active is False


# --- administrador do condomínio ------------------------------------------


def test_admin_sees_edit_forms(world):
    detail = world.a.admin.get(f"/condominios/{world.a.condo_id}").text
    assert 'action="/houses"' in detail
    assert 'action="/gates"' in detail


def test_admin_cannot_create_or_toggle_condos(world, store):
    assert world.a.admin.post("/condos", name="Condominio Novo").status_code == 403
    assert (
        world.a.admin.post(f"/condos/{world.a.condo_id}/active", active="0").status_code
        == 403
    )
    assert store.get(Condo, id=world.a.condo_id).active is True


@pytest.mark.parametrize("role", ["admin", "superadmin", "inexistente"])
def test_admin_can_only_create_porters(world, store, role):
    before = store.count(User)
    response = world.a.admin.post(
        "/users", condo_id=world.a.condo_id, name="Novo", role=role,
        email="novo@teste.local", password="uma-senha-longa-123",
    )
    assert response.status_code == 403
    assert store.count(User) == before


def test_admin_creates_porter_and_the_porter_can_log_in(world, store, new_browser):
    response = world.a.admin.post(
        "/users", condo_id=world.a.condo_id, name="Novo Porteiro", role="porter",
        email="  Novo.Porteiro@Teste.Local ", password="uma-senha-longa-123",
    )
    assert response.status_code == 303
    user = store.get(User, email="novo.porteiro@teste.local")
    assert (user.role, user.condo_id, user.active) == ("porter", world.a.condo_id, True)
    assert user.password_hash.startswith("pbkdf2_sha256$")

    browser = new_browser()
    assert browser.login("novo.porteiro@teste.local", "uma-senha-longa-123").status_code == 303


def test_user_password_policy(world, store):
    def create(email, password):
        return world.a.admin.post(
            "/users", condo_id=world.a.condo_id, name="Novo", role="porter",
            email=email, password=password,
        )

    assert create("curta@teste.local", "x" * 11).status_code == 422
    assert store.get(User, email="curta@teste.local") is None
    assert create("limite@teste.local", "x" * 12).status_code == 303


def test_duplicate_user_email_is_rejected(world, store):
    response = world.a.admin.post(
        "/users", condo_id=world.a.condo_id, name="Outro", role="porter",
        email="ADMIN-ALFA@teste.local", password="uma-senha-longa-123",
    )
    assert response.status_code == 409


def test_admin_cannot_manage_another_admin_of_the_same_condo(world, store):
    other = store.add_user(world.a.condo_id, "admin", "admin2-alfa@teste.local")
    before = store.get(User, id=other.user_id)
    assert world.a.admin.post(f"/users/{other.user_id}/active", active="0").status_code == 404
    assert (
        world.a.admin.post(
            f"/users/{other.user_id}/password", password="uma-senha-longa-123"
        ).status_code
        == 404
    )
    after = store.get(User, id=other.user_id)
    assert (after.active, after.password_hash) == (True, before.password_hash)


# --- superadmin ------------------------------------------------------------


def test_superadmin_creates_condo_with_audit(world, store):
    response = world.root.post("/condos", name="  Condominio Gama  ")
    assert response.status_code == 303
    condo_id = int(re.search(r"/condominios/(\d+)", response.headers["location"]).group(1))
    assert store.get(Condo, id=condo_id).name == "Condominio Gama"
    assert "condominium.create" in actions(store)


@pytest.mark.parametrize("name", ["ab", "  ab  ", "x" * 151])
def test_condo_name_length_is_validated(world, store, name):
    before = store.count(Condo)
    assert world.root.post("/condos", name=name).status_code == 422
    assert store.count(Condo) == before


@pytest.mark.parametrize("role", ["admin", "porter"])
def test_superadmin_creates_admins_and_porters_for_any_condo(world, store, role):
    response = world.root.post(
        "/users", condo_id=world.b.condo_id, name="Novo", role=role,
        email="novo@teste.local", password="uma-senha-longa-123",
    )
    assert response.status_code == 303
    user = store.get(User, email="novo@teste.local")
    assert (user.role, user.condo_id) == (role, world.b.condo_id)


def test_superadmin_cannot_create_a_user_for_a_missing_condo(world, store):
    response = world.root.post(
        "/users", condo_id=9999, name="Novo", role="porter",
        email="novo@teste.local", password="uma-senha-longa-123",
    )
    assert response.status_code == 422


def test_superadmin_cannot_deactivate_self_or_reset_own_password_here(world, store):
    root_id = world.root.user_id
    assert world.root.post(f"/users/{root_id}/active", active="0").status_code == 409
    assert (
        world.root.post(f"/users/{root_id}/password", password=TEST_PASSWORD + "x").status_code
        == 404
    )
    assert store.get(User, id=root_id).active is True
