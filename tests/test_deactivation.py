"""Desativação lógica (nada é apagado) de condomínios, usuários, portarias e residências."""

import pytest

from app.core import Audit, Condo, Gate, House, User
from support import STRUCTURE_WRITES, has_origin, select_options

UNAVAILABLE = "Este acesso não está disponível"
BAD_LOGIN = "E-mail ou senha inválidos."


def actions(store):
    return [event.action for event in store.rows(Audit)]


def public_page(new_browser, link):
    return new_browser().get(f"/r/{link.token}").text


# --- condomínio ------------------------------------------------------------


def test_deactivating_a_condo_suspends_users_and_links(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    assert world.a.porter.get("/dashboard").status_code == 200  # sessão já aberta
    assert world.a.admin.get("/dashboard").status_code == 200
    assert UNAVAILABLE not in public_page(new_browser, link)

    response = world.root.post(f"/condos/{world.a.condo_id}/active", active="0")

    assert response.status_code == 303
    assert store.get(Condo, id=world.a.condo_id).active is False
    assert world.a.porter.get("/dashboard").status_code == 401
    assert world.a.admin.get("/dashboard").status_code == 401
    assert BAD_LOGIN in new_browser().login(world.a.admin.email).text
    assert UNAVAILABLE in public_page(new_browser, link)
    assert "condominium.deactivate" in actions(store)


def test_reactivating_a_condo_restores_everything(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    world.root.post(f"/condos/{world.a.condo_id}/active", active="0")

    assert world.root.post(f"/condos/{world.a.condo_id}/active", active="1").status_code == 303

    assert store.get(Condo, id=world.a.condo_id).active is True
    assert new_browser().login(world.a.admin.email).status_code == 303
    assert UNAVAILABLE not in public_page(new_browser, link)
    assert "condominium.activate" in actions(store)


def test_deactivating_a_condo_does_not_affect_the_others(world, store, new_browser):
    link = store.add_link(world.b.condo_id, world.b.house_id)
    world.root.post(f"/condos/{world.a.condo_id}/active", active="0")
    assert world.b.admin.get("/dashboard").status_code == 200
    assert UNAVAILABLE not in public_page(new_browser, link)


@pytest.mark.parametrize("path, data", STRUCTURE_WRITES)
def test_nothing_can_be_registered_in_an_inactive_condo(world, store, path, data):
    store.update(Condo, world.a.condo_id, active=False)
    before = store.counts()
    response = world.root.post(path, condo_id=world.a.condo_id, **data)
    assert response.status_code == 409
    assert store.counts() == before


def test_links_cannot_be_issued_in_an_inactive_condo(world, store):
    store.update(Condo, world.a.condo_id, active=False)
    response = world.root.post("/links", house_id=world.a.house_id, gate_id="")
    assert response.status_code == 409


def test_inactive_condo_is_flagged_and_left_out_of_the_qr_form(world, store):
    store.update(Condo, world.a.condo_id, active=False)
    assert "Inativo" in world.root.get("/manage").text
    assert "Reativar condomínio" in world.root.get(f"/condominios/{world.a.condo_id}").text
    portaria = world.root.get("/portaria").text
    assert world.a.name not in portaria
    assert world.b.name in portaria


def test_condo_flag_must_be_zero_or_one(world, store):
    assert world.root.post(f"/condos/{world.a.condo_id}/active", active="talvez").status_code == 422
    assert store.get(Condo, id=world.a.condo_id).active is True


def test_unknown_condo_cannot_be_toggled(world):
    assert world.root.post("/condos/9999/active", active="0").status_code == 404


def test_users_of_an_inactive_condo_cannot_be_reactivated(world, store):
    store.update(User, world.a.porter.user_id, active=False)
    store.update(Condo, world.a.condo_id, active=False)
    response = world.root.post(f"/users/{world.a.porter.user_id}/active", active="1")
    assert response.status_code == 409
    assert store.get(User, id=world.a.porter.user_id).active is False


# --- residência ------------------------------------------------------------


def test_deactivating_a_house_blocks_its_links_and_new_ones(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id)

    response = world.a.admin.post(f"/houses/{world.a.house_id}/active", active="0")

    assert response.status_code == 303
    assert store.get(House, id=world.a.house_id).active is False
    assert UNAVAILABLE in public_page(new_browser, link)
    houses = select_options(world.a.admin.get("/portaria").text, "house-select")
    assert f'value="{world.a.house_id}"' not in houses
    assert world.a.admin.post("/links", house_id=world.a.house_id, gate_id="").status_code == 404
    assert "house.deactivate" in actions(store)


def test_reactivating_a_house_brings_its_links_back(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    world.a.admin.post(f"/houses/{world.a.house_id}/active", active="0")

    assert world.a.admin.post(f"/houses/{world.a.house_id}/active", active="1").status_code == 303

    assert UNAVAILABLE not in public_page(new_browser, link)
    houses = select_options(world.a.admin.get("/portaria").text, "house-select")
    assert f'value="{world.a.house_id}"' in houses


def test_house_of_an_inactive_condo_cannot_be_reactivated(world, store):
    store.update(House, world.a.house_id, active=False)
    store.update(Condo, world.a.condo_id, active=False)
    response = world.root.post(f"/houses/{world.a.house_id}/active", active="1")
    assert response.status_code == 409
    assert store.get(House, id=world.a.house_id).active is False


def test_condo_page_marks_inactive_houses_and_offers_reactivation(world, store):
    store.update(House, world.a.house_id, active=False)
    html = world.a.admin.get(f"/condominios/{world.a.condo_id}").text
    assert "Inativa" in html
    assert "Reativar" in html


# --- portaria --------------------------------------------------------------


def test_inactive_gate_is_not_offered_and_cannot_be_used(world, store):
    gates = select_options(world.a.admin.get("/portaria").text, "gate-select")
    assert f'value="{world.a.gate_id}"' in gates

    response = world.a.admin.post(f"/gates/{world.a.gate_id}/active", active="0")

    assert response.status_code == 303
    assert store.get(Gate, id=world.a.gate_id).active is False
    gates = select_options(world.a.admin.get("/portaria").text, "gate-select")
    assert f'value="{world.a.gate_id}"' not in gates
    blocked = world.a.admin.post("/links", house_id=world.a.house_id, gate_id=world.a.gate_id)
    assert blocked.status_code == 422
    assert "gate.deactivate" in actions(store)


def test_existing_links_ignore_an_inactive_gate(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id, gate_id=world.a.gate_id)
    assert has_origin(public_page(new_browser, link))

    world.a.admin.post(f"/gates/{world.a.gate_id}/active", active="0")

    html = public_page(new_browser, link)
    assert UNAVAILABLE not in html  # o destino continua válido
    assert not has_origin(html)
    assert "Entrada alfa" not in html
    assert "Portaria não especificada" in html


def test_reactivating_a_gate_makes_it_available_again(world, store):
    world.a.admin.post(f"/gates/{world.a.gate_id}/active", active="0")
    assert world.a.admin.post(f"/gates/{world.a.gate_id}/active", active="1").status_code == 303
    response = world.a.admin.post("/links", house_id=world.a.house_id, gate_id=world.a.gate_id)
    assert response.status_code == 303


# --- usuário ---------------------------------------------------------------


def test_admin_deactivates_and_reactivates_a_porter(world, store, new_browser):
    porter_id = world.a.porter.user_id
    assert world.a.porter.get("/dashboard").status_code == 200

    assert world.a.admin.post(f"/users/{porter_id}/active", active="0").status_code == 303

    assert store.get(User, id=porter_id).active is False
    assert world.a.porter.get("/dashboard").status_code == 401
    assert BAD_LOGIN in new_browser().login(world.a.porter.email).text
    assert "Inativo" in world.a.admin.get("/usuarios").text

    assert world.a.admin.post(f"/users/{porter_id}/active", active="1").status_code == 303
    assert new_browser().login(world.a.porter.email).status_code == 303
    assert {"user.deactivate", "user.activate"} <= set(actions(store))


def test_a_user_cannot_deactivate_their_own_account(world, store):
    response = world.a.admin.post(f"/users/{world.a.admin.user_id}/active", active="0")
    assert response.status_code == 409
    assert store.get(User, id=world.a.admin.user_id).active is True


def test_superadmin_deactivates_an_admin(world, store, new_browser):
    assert world.root.post(f"/users/{world.a.admin.user_id}/active", active="0").status_code == 303
    assert BAD_LOGIN in new_browser().login(world.a.admin.email).text
