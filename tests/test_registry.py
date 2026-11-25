"""Cadastro de residências, portarias e rota interna: validações e edição."""

import json

import pytest

from app.core import Audit, Gate, House

ROUTE_TEXT = "-10.7001000, -37.4101000\n-10.7012942, -37.4131006"
ROUTE_POINTS = [[-10.7001, -37.4101], [-10.7012942, -37.4131006]]

INVALID_COORDINATES = [
    ("91", "0"), ("-91", "0"), ("0", "181"), ("0", "-181"),
    ("nan", "0"), ("inf", "0"), ("abc", "0"), ("", "0"),
]


def create_house(world, **overrides):
    data = dict(
        condo_id=world.a.condo_id, block="B", number="02",
        lat="-10.7", lng="-37.4", reference="",
    )
    data.update(overrides)
    return world.a.admin.post("/houses", **data)


def update_house(world, house_id=None, **overrides):
    data = dict(
        block="A", number="01", lat="-10.7012942", lng="-37.4131006",
        reference="Referencia alfa",
    )
    data.update(overrides)
    return world.a.admin.post(f"/houses/{house_id or world.a.house_id}/update", **data)


def save_route(world, **data):
    return world.a.admin.post(f"/houses/{world.a.house_id}/route", **data)


# --- residências: cadastro -------------------------------------------------


def test_house_block_and_number_are_trimmed_and_uppercased(world, store):
    assert create_house(world, block=" b ", number=" 12a ").status_code == 303
    house = store.get(House, condo_id=world.a.condo_id, block="B", number="12A")
    assert house is not None


def test_duplicate_house_is_rejected_after_normalization(world, store):
    before = store.count(House)
    response = create_house(world, block="a", number="01")
    assert response.status_code == 409
    assert "já estão cadastradas" in response.json()["detail"]
    assert store.count(House) == before


def test_duplicate_of_an_inactive_house_points_to_reactivation(world, store):
    store.update(House, world.a.house_id, active=False)
    response = create_house(world, block="A", number="01")
    assert response.status_code == 409
    assert "inativa" in response.json()["detail"]


def test_same_block_and_number_is_allowed_in_another_condo(world, store):
    for condo in (world.a, world.b):
        response = world.root.post(
            "/houses", condo_id=condo.condo_id, block="Z", number="1",
            lat="1", lng="1",
        )
        assert response.status_code == 303


@pytest.mark.parametrize("lat, lng", INVALID_COORDINATES)
def test_house_rejects_invalid_coordinates(world, store, lat, lng):
    before = store.count(House)
    assert create_house(world, lat=lat, lng=lng).status_code == 422
    assert store.count(House) == before


@pytest.mark.parametrize("lat, lng", [("90", "180"), ("-90", "-180"), ("0", "0")])
def test_house_accepts_boundary_coordinates(world, lat, lng):
    assert create_house(world, lat=lat, lng=lng).status_code == 303


@pytest.mark.parametrize("block, number", [("  ", "1"), ("A", "  ")])
def test_house_requires_block_and_number(world, store, block, number):
    before = store.count(House)
    assert create_house(world, block=block, number=number).status_code == 422
    assert store.count(House) == before


def test_house_creation_is_audited(world, store):
    create_house(world, block="C", number="03")
    events = [e for e in store.rows(Audit) if e.action == "house.create"]
    assert [e.detail for e in events] == ["C/03"]
    assert events[0].condo_id == world.a.condo_id


# --- residências: edição ---------------------------------------------------


def test_house_update_persists(world, store):
    response = update_house(world, block="b", number="7", lat="-10.5", lng="-37.5", reference="Novo")
    assert response.status_code == 303
    house = store.get(House, id=world.a.house_id)
    assert (house.block, house.number, house.lat, house.lng, house.reference) == (
        "B", "7", -10.5, -37.5, "Novo",
    )


def test_moving_a_house_removes_route_verification_but_keeps_the_points(world, store):
    store.update(House, world.a.house_id, route_geometry=json.dumps(ROUTE_POINTS), route_verified=True)
    assert update_house(world, lat="-10.8").status_code == 303
    house = store.get(House, id=world.a.house_id)
    assert house.route_verified is False
    assert json.loads(house.route_geometry) == ROUTE_POINTS


def test_saving_a_house_without_moving_it_keeps_route_verification(world, store):
    store.update(House, world.a.house_id, route_geometry=json.dumps(ROUTE_POINTS), route_verified=True)
    assert update_house(world, reference="So a referencia").status_code == 303
    assert store.get(House, id=world.a.house_id).route_verified is True


def test_house_update_cannot_take_another_houses_identity(world, store):
    other = store.add_house(world.a.condo_id, "B", "02")
    response = update_house(world, house_id=other, block="A", number="01")
    assert response.status_code == 409
    assert store.get(House, id=other).number == "02"


def test_house_update_requires_block_and_number(world):
    assert update_house(world, block=" ").status_code == 422


# --- portarias -------------------------------------------------------------


def create_gate(world, **data):
    return world.a.admin.post("/gates", condo_id=world.a.condo_id, **data)


def test_gate_can_be_created_with_or_without_coordinates(world, store):
    assert create_gate(world, name="Com coordenadas", lat="-10.7", lng="-37.4").status_code == 303
    assert create_gate(world, name="Sem coordenadas").status_code == 303
    with_coords = store.get(Gate, name="Com coordenadas")
    without = store.get(Gate, name="Sem coordenadas")
    assert (with_coords.lat, with_coords.lng, with_coords.active) == (-10.7, -37.4, True)
    assert (without.lat, without.lng) == (None, None)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "  "},
        {"name": "x", "lat": "-10.7"},
        {"name": "x", "lng": "-37.4"},
        {"name": "x", "lat": "95", "lng": "0"},
        {"name": "x", "lat": "abc", "lng": "0"},
    ],
    ids=["blank-name", "only-lat", "only-lng", "out-of-range", "not-a-number"],
)
def test_gate_validation(world, store, data):
    before = store.count(Gate)
    assert create_gate(world, **data).status_code == 422
    assert store.count(Gate) == before


def test_gate_update_persists_and_can_clear_coordinates(world, store):
    path = f"/gates/{world.a.gate_id}/update"
    assert world.a.admin.post(path, name="Entrada principal", lat="-10.71", lng="-37.42").status_code == 303
    gate = store.get(Gate, id=world.a.gate_id)
    assert (gate.name, gate.lat, gate.lng) == ("Entrada principal", -10.71, -37.42)

    assert world.a.admin.post(path, name="Entrada principal", lat="", lng="").status_code == 303
    gate = store.get(Gate, id=world.a.gate_id)
    assert (gate.lat, gate.lng) == (None, None)
    assert "gate.update" in [e.action for e in store.rows(Audit)]


@pytest.mark.parametrize(
    "data",
    [{"name": " "}, {"name": "x", "lat": "-10.7", "lng": ""}, {"name": "x", "lat": "91", "lng": "0"}],
    ids=["blank-name", "only-lat", "out-of-range"],
)
def test_gate_update_validation(world, store, data):
    before = store.get(Gate, id=world.a.gate_id)
    response = world.a.admin.post(f"/gates/{world.a.gate_id}/update", **data)
    assert response.status_code == 422
    after = store.get(Gate, id=world.a.gate_id)
    assert (after.name, after.lat, after.lng) == (before.name, before.lat, before.lng)


# --- rota interna ----------------------------------------------------------


def test_route_is_saved_as_normalized_json(world, store):
    assert save_route(world, geometry=ROUTE_TEXT).status_code == 303
    house = store.get(House, id=world.a.house_id)
    assert json.loads(house.route_geometry) == ROUTE_POINTS
    assert house.route_verified is False  # só vira verificada se alguém marcar


def test_route_accepts_a_json_array(world, store):
    assert save_route(world, geometry=json.dumps(ROUTE_POINTS), verified="1").status_code == 303
    house = store.get(House, id=world.a.house_id)
    assert json.loads(house.route_geometry) == ROUTE_POINTS
    assert house.route_verified is True


def test_route_verification_requires_points(world, store):
    assert save_route(world, geometry="", verified="1").status_code == 422
    assert store.get(House, id=world.a.house_id).route_verified is False


def test_empty_geometry_removes_the_route_and_its_verification(world, store):
    save_route(world, geometry=ROUTE_TEXT, verified="1")
    assert save_route(world, geometry="").status_code == 303
    house = store.get(House, id=world.a.house_id)
    assert house.route_geometry is None
    assert house.route_verified is False


@pytest.mark.parametrize(
    "geometry",
    [
        "isto nao e uma rota",
        "-10.7, -37.4",                      # um ponto só
        "-10.7, -37.4\n-10.8",               # linha incompleta
        "91, 0\n1, 1",                       # latitude fora da faixa
        "1, 1\n2, 181",                      # longitude fora da faixa
        "[[1, 2]]",
        "[1, 2]",
        '{"a": 1}',
        "[[1, 2], [3",                       # JSON quebrado
        "\n".join("1, 1" for _ in range(501)),
    ],
    ids=[
        "text", "one-point", "incomplete-line", "bad-lat", "bad-lng",
        "json-one-point", "json-flat", "json-object", "json-broken", "too-many",
    ],
)
def test_invalid_routes_are_rejected_without_changes(world, store, geometry):
    save_route(world, geometry=ROUTE_TEXT)
    response = save_route(world, geometry=geometry)
    assert response.status_code == 422
    assert json.loads(store.get(House, id=world.a.house_id).route_geometry) == ROUTE_POINTS


def test_route_changes_are_audited_without_the_coordinates(world, store):
    save_route(world, geometry=ROUTE_TEXT, verified="1")
    event = [e for e in store.rows(Audit) if e.action == "house.route"][0]
    assert "pontos=2" in event.detail and "verificado=True" in event.detail
    assert "-37.41" not in event.detail


def test_condo_page_shows_the_route_state(world, store):
    page = f"/condominios/{world.a.condo_id}"
    assert "Sem rota" in world.a.admin.get(page).text
    save_route(world, geometry=ROUTE_TEXT)
    assert "Não verificada" in world.a.admin.get(page).text
    save_route(world, geometry=ROUTE_TEXT, verified="1")
    html = world.a.admin.get(page).text
    assert "Verificada" in html
    assert "-10.7001, -37.4101" in html  # texto pré-preenchido no formulário
