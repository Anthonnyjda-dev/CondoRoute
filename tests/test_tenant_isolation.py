"""Isolamento multi-tenant: um condomínio nunca enxerga nem altera outro."""

import pytest

from app.core import Access, Gate, House, User
from support import STRUCTURE_WRITES

MODEL_BY_PATH = {"/houses": House, "/gates": Gate, "/users": User}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# --- leitura ---------------------------------------------------------------


def test_admin_can_open_own_condo(world):
    response = world.a.admin.get(f"/condominios/{world.a.condo_id}")
    assert response.status_code == 200
    assert world.a.name in response.text


def test_admin_cannot_open_other_condo(world):
    assert world.a.admin.get(f"/condominios/{world.b.condo_id}").status_code == 404


@pytest.mark.parametrize("page", ["/dashboard", "/manage", "/usuarios", "/portaria"])
def test_admin_pages_list_only_own_condo(world, page):
    response = world.a.admin.get(page)
    assert response.status_code == 200
    assert world.a.name in response.text
    assert world.b.name not in response.text
    assert "admin-beta@teste.local" not in response.text
    assert "porter-beta@teste.local" not in response.text


def test_portaria_form_lists_only_own_houses_and_gates(world):
    html = world.a.admin.get("/portaria").text
    assert f'data-condo="{world.a.condo_id}"' in html
    assert f'data-condo="{world.b.condo_id}"' not in html


@pytest.mark.parametrize("page", ["/dashboard", "/manage", "/portaria"])
def test_superadmin_sees_every_condo(world, page):
    html = world.root.get(page).text
    assert world.a.name in html
    assert world.b.name in html


def test_superadmin_user_list_includes_every_condo(world):
    html = world.root.get("/usuarios").text
    assert "admin-alfa@teste.local" in html
    assert "admin-beta@teste.local" in html


# --- escrita em estrutura --------------------------------------------------


@pytest.mark.parametrize("path, data", STRUCTURE_WRITES)
def test_admin_cannot_write_into_other_condo(world, store, path, data):
    before = store.counts()
    response = world.a.admin.post(path, condo_id=world.b.condo_id, **data)
    assert response.status_code == 403
    assert store.counts() == before


@pytest.mark.parametrize("path, data", STRUCTURE_WRITES)
def test_admin_can_write_into_own_condo(world, store, path, data):
    # Controle positivo: garante que o 403 acima vem do isolamento e não de um erro geral.
    model = MODEL_BY_PATH[path]
    before = store.count(model)
    response = world.a.admin.post(path, condo_id=world.a.condo_id, **data)
    assert response.status_code == 303
    assert store.count(model) == before + 1


@pytest.mark.parametrize("path, data", STRUCTURE_WRITES)
def test_superadmin_can_write_into_any_condo(world, store, path, data):
    model = MODEL_BY_PATH[path]
    before = store.count(model)
    response = world.root.post(path, condo_id=world.b.condo_id, **data)
    assert response.status_code == 303
    assert store.count(model) == before + 1


def test_admin_cannot_edit_house_of_other_condo(world, store):
    before = store.get(House, id=world.b.house_id)
    response = world.a.admin.post(
        f"/houses/{world.b.house_id}/update",
        block="A", number="01", lat="1", lng="1", reference="invadida",
    )
    assert response.status_code == 404
    after = store.get(House, id=world.b.house_id)
    assert (after.lat, after.lng, after.reference) == (
        before.lat, before.lng, before.reference,
    )


def test_admin_cannot_edit_gate_of_other_condo(world, store):
    response = world.a.admin.post(
        f"/gates/{world.b.gate_id}/update", name="invadida", lat="1", lng="1"
    )
    assert response.status_code == 404
    assert store.get(Gate, id=world.b.gate_id).name == "Entrada beta"


def test_admin_cannot_set_route_of_other_condo_house(world, store):
    response = world.a.admin.post(
        f"/houses/{world.b.house_id}/route", geometry="1, 1\n2, 2", verified="1"
    )
    assert response.status_code == 404
    house = store.get(House, id=world.b.house_id)
    assert house.route_geometry is None
    assert house.route_verified is False


@pytest.mark.parametrize("resource", ["gates", "houses"])
def test_admin_cannot_toggle_items_of_other_condo(world, store, resource):
    model = Gate if resource == "gates" else House
    ident = world.b.gate_id if resource == "gates" else world.b.house_id
    response = world.a.admin.post(f"/{resource}/{ident}/active", active="0")
    assert response.status_code == 404
    assert store.get(model, id=ident).active is True


def test_admin_cannot_deactivate_a_condo(world, store):
    for condo_id in (world.a.condo_id, world.b.condo_id):
        response = world.a.admin.post(f"/condos/{condo_id}/active", active="0")
        assert response.status_code == 403


def test_admin_cannot_manage_users_of_other_condo(world, store):
    target = world.b.porter.user_id
    before = store.get(User, id=target)
    assert world.a.admin.post(f"/users/{target}/active", active="0").status_code == 404
    assert (
        world.a.admin.post(
            f"/users/{target}/password", password="outra-senha-longa-1"
        ).status_code
        == 404
    )
    after = store.get(User, id=target)
    assert after.active is True
    assert after.password_hash == before.password_hash


# --- links e QR ------------------------------------------------------------


def test_admin_cannot_create_link_for_house_of_other_condo(world, store):
    response = world.a.admin.post("/links", house_id=world.b.house_id, gate_id="")
    assert response.status_code == 404
    assert store.count(Access) == 0


def test_admin_cannot_use_gate_of_other_condo(world, store):
    response = world.a.admin.post(
        "/links", house_id=world.a.house_id, gate_id=world.b.gate_id
    )
    assert response.status_code == 422
    assert store.count(Access) == 0


@pytest.mark.parametrize("action", ["revoke", "reactivate", "delete"])
def test_admin_cannot_change_link_of_other_condo(world, store, action):
    initially_active = action != "reactivate"
    link = store.add_link(world.b.condo_id, world.b.house_id, active=initially_active)
    response = world.a.admin.post(f"/links/{link.id}/{action}")
    assert response.status_code == 404
    row = store.get(Access, id=link.id)
    assert row is not None
    assert row.active is initially_active


def test_porter_cannot_touch_links_of_other_condo(world, store):
    link = store.add_link(world.b.condo_id, world.b.house_id)
    assert world.a.porter.post(f"/links/{link.id}/revoke").status_code == 404
    assert store.get(Access, id=link.id).active is True
    assert (
        world.a.porter.post(
            "/links", house_id=world.b.house_id, gate_id=""
        ).status_code
        == 404
    )


def test_qr_png_is_only_served_to_the_owning_condo(world, store):
    own = store.add_link(world.a.condo_id, world.a.house_id)
    other = store.add_link(world.b.condo_id, world.b.house_id)

    response = world.a.admin.get(f"/links/{own.id}/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(PNG_SIGNATURE)

    assert world.a.admin.get(f"/links/{other.id}/qr.png").status_code == 404
    assert world.root.get(f"/links/{other.id}/qr.png").status_code == 200


def test_portaria_link_param_does_not_reveal_other_condo_link(world, store):
    link = store.add_link(world.b.condo_id, world.b.house_id)

    intruder = world.a.admin.get(f"/portaria?link={link.id}").text
    assert link.token not in intruder
    assert f"/links/{link.id}/qr.png" not in intruder

    owner = world.b.admin.get(f"/portaria?link={link.id}").text
    assert link.token in owner
    assert f"/links/{link.id}/qr.png" in owner
