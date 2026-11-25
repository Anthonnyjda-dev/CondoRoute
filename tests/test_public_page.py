"""Página pública que o entregador abre ao ler o QR Code (/r/<token>)."""

import pytest

from app.core import Condo, Gate, House
from support import has_origin

UNAVAILABLE = "Este acesso não está disponível"
GEOMETRY = "[[-10.7001, -37.4101], [-10.7012, -37.4131]]"
VERIFIED = "Percurso verificado"
NOT_VERIFIED = "Sem rota interna verificada"


def open_link(new_browser, link):
    return new_browser().get(f"/r/{link.token}")


def test_active_link_shows_the_destination_without_login(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id, gate_id=world.a.gate_id)
    response = open_link(new_browser, link)
    assert response.status_code == 200
    for expected in ("Quadra A · Casa 01", world.a.name, "Entrada alfa", "Referencia alfa"):
        assert expected in response.text


def test_external_navigation_links_are_encoded(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id, gate_id=world.a.gate_id)
    html = open_link(new_browser, link).text
    assert "https://www.google.com/maps/dir/?" in html
    assert "destination=-10.7012942%2C-37.4131006" in html
    assert has_origin(html)
    assert "origin=-10.7000000%2C-37.4100000" in html  # coordenada da portaria
    assert "https://waze.com/ul?ll=-10.7012942%2C-37.4131006" in html
    assert "https://maps.apple.com/?daddr=-10.7012942%2C-37.4131006" in html


def test_without_a_gate_there_is_no_origin(world, store, new_browser):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    html = open_link(new_browser, link).text
    assert not has_origin(html)
    assert "Portaria não especificada" in html


def test_gate_without_coordinates_gives_no_origin(world, store, new_browser):
    gate_id = store.add_gate(world.a.condo_id, "Sem GPS")
    link = store.add_link(world.a.condo_id, world.a.house_id, gate_id=gate_id)
    html = open_link(new_browser, link).text
    assert "Sem GPS" in html
    assert not has_origin(html)


@pytest.mark.parametrize("reason", ["revoked", "house-inactive", "condo-inactive"])
def test_unavailable_links_show_a_friendly_notice(world, store, new_browser, reason):
    link = store.add_link(
        world.a.condo_id, world.a.house_id, active=reason != "revoked"
    )
    if reason == "house-inactive":
        store.update(House, world.a.house_id, active=False)
    if reason == "condo-inactive":
        store.update(Condo, world.a.condo_id, active=False)

    response = open_link(new_browser, link)

    assert response.status_code == 200
    assert UNAVAILABLE in response.text
    assert "google.com/maps" not in response.text
    assert "Quadra A" not in response.text  # nada do destino vaza


def test_unknown_token_shows_the_same_notice(new_browser):
    response = new_browser().get("/r/token-que-nao-existe")
    assert response.status_code == 200
    assert UNAVAILABLE in response.text


@pytest.mark.parametrize(
    "verified, geometry, expected",
    [
        (True, GEOMETRY, VERIFIED),
        (False, GEOMETRY, NOT_VERIFIED),
        (True, None, NOT_VERIFIED),
        (True, "isto nao e json", NOT_VERIFIED),
        (True, "[[1, 2]]", NOT_VERIFIED),
        (True, "[[1, 2, 3], [4, 5, 6]]", NOT_VERIFIED),
        (True, '{"a": 1}', NOT_VERIFIED),
    ],
    ids=[
        "verified-valid", "unverified-valid", "no-geometry", "bad-json",
        "one-point", "bad-shape", "json-object",
    ],
)
def test_internal_route_is_shown_only_when_verified_and_valid(
    world, store, new_browser, verified, geometry, expected
):
    store.update(House, world.a.house_id, route_verified=verified, route_geometry=geometry)
    link = store.add_link(world.a.condo_id, world.a.house_id)
    html = open_link(new_browser, link).text
    assert expected in html
    other = VERIFIED if expected == NOT_VERIFIED else NOT_VERIFIED
    assert other not in html


def test_user_supplied_text_is_escaped(world, store, new_browser):
    store.update(House, world.a.house_id, reference="<script>alert(1)</script>")
    store.update(Gate, world.a.gate_id, name="'); alert(2);//")
    link = store.add_link(world.a.condo_id, world.a.house_id, gate_id=world.a.gate_id)

    html = open_link(new_browser, link).text

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "'); alert(2);//" not in html


def test_admin_pages_escape_user_text_too(world, store):
    store.update(House, world.a.house_id, reference="<script>alert(1)</script>")
    html = world.a.admin.get(f"/condominios/{world.a.condo_id}").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
