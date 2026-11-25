"""Ciclo de vida dos links/QR Codes e a tela da portaria."""

import re

import pytest
import qrcode

from app.core import Access, Audit, Condo, House

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BASE_URL = "http://localhost:8000"


def issue_link(world, **overrides):
    data = dict(house_id=world.a.house_id, gate_id=world.a.gate_id)
    data.update(overrides)
    return world.a.admin.post("/links", **data)


def link_id(response):
    return int(re.search(r"link=(\d+)$", response.headers["location"]).group(1))


# --- criação ---------------------------------------------------------------


def test_new_link_redirects_by_id_and_keeps_the_token_out_of_the_url(world, store):
    response = issue_link(world)
    assert response.status_code == 303
    assert re.fullmatch(r"/portaria\?link=\d+", response.headers["location"])
    token = store.get(Access, id=link_id(response)).token
    assert token not in response.headers["location"]


def test_tokens_are_long_and_unique(world, store):
    for _ in range(5):
        issue_link(world)
    tokens = [link.token for link in store.rows(Access)]
    assert len(set(tokens)) == 5
    assert all(len(token) >= 43 for token in tokens)


def test_cannot_issue_link_for_an_inactive_house(world, store):
    store.update(House, world.a.house_id, active=False)
    assert issue_link(world).status_code == 404
    assert store.count(Access) == 0


@pytest.mark.parametrize("gate_id", ["abc", "9999"], ids=["not-a-number", "unknown"])
def test_invalid_gate_is_rejected_with_a_clear_error(world, store, gate_id):
    response = issue_link(world, gate_id=gate_id)
    assert response.status_code == 422
    assert store.count(Access) == 0


def test_gate_is_optional(world, store):
    assert issue_link(world, gate_id="").status_code == 303
    assert store.get(Access, house_id=world.a.house_id).gate_id is None


# --- tela da portaria ------------------------------------------------------


def test_new_link_is_shown_with_qr_copy_button_and_download(world, store):
    response = issue_link(world)
    ident = link_id(response)
    token = store.get(Access, id=ident).token

    html = world.a.admin.get(response.headers["location"]).text

    assert f'src="/links/{ident}/qr.png"' in html
    assert f'href="/links/{ident}/qr.png" download=' in html
    assert 'id="copy-link"' in html
    assert f'value="{BASE_URL}/r/{token}"' in html  # campo com o link para copiar


def test_existing_links_can_be_viewed_again(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    html = world.a.admin.get(f"/portaria?link={link.id}").text
    assert f'src="/links/{link.id}/qr.png"' in html
    assert f"/portaria?link={link.id}" in html  # o botão "Ver QR" da lista

    nothing_selected = world.a.admin.get("/portaria").text
    assert "Pronto para gerar" in nothing_selected
    assert "/qr.png" not in nothing_selected


@pytest.mark.parametrize("value", ["abc", "9999", "-1", ""])
def test_unusable_link_param_just_shows_the_empty_panel(world, store, value):
    store.add_link(world.a.condo_id, world.a.house_id)
    response = world.a.admin.get(f"/portaria?link={value}")
    assert response.status_code == 200
    assert "Pronto para gerar" in response.text


def test_revoked_link_explains_itself_instead_of_showing_a_qr(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id, active=False)
    html = world.a.admin.get(f"/portaria?link={link.id}").text
    assert "revogado" in html
    assert f'src="/links/{link.id}/qr.png"' not in html
    assert f'action="/links/{link.id}/reactivate"' in html


def test_copy_warning_appears_only_while_the_public_url_is_local(world, store, monkeypatch):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    page = f"/portaria?link={link.id}"
    assert "PUBLIC_BASE_URL" in world.a.admin.get(page).text

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://entregas.exemplo.com.br/")
    html = world.a.admin.get(page).text
    assert "PUBLIC_BASE_URL" not in html
    assert f'value="https://entregas.exemplo.com.br/r/{link.token}"' in html


def test_list_shows_block_number_and_gate_instead_of_the_house_id(world, store):
    store.add_link(world.a.condo_id, world.a.house_id, gate_id=world.a.gate_id)
    html = world.a.admin.get("/portaria").text
    assert "Quadra A · Casa 01" in html
    assert "Entrada alfa" in html
    assert f"Casa #{world.a.house_id}" not in html


def test_condo_name_is_listed_only_for_the_superadmin(world, store):
    store.add_link(world.a.condo_id, world.a.house_id)
    assert f'class="row-sub">{world.a.name}' in world.root.get("/portaria").text
    assert 'class="row-sub"' not in world.a.admin.get("/portaria").text


def test_list_flags_links_of_inactive_houses(world, store):
    store.add_link(world.a.condo_id, world.a.house_id)
    store.update(House, world.a.house_id, active=False)
    assert "Residência inativa" in world.a.admin.get("/portaria").text


def test_pagination_is_tolerant(world, store):
    for _ in range(12):
        store.add_link(world.a.condo_id, world.a.house_id)
    get = world.a.admin.get
    assert "Página 1 de 2" in get("/portaria").text
    assert "Página 2 de 2" in get("/portaria?page=2").text
    assert "Página 2 de 2" in get("/portaria?page=999").text
    assert "Página 1 de 2" in get("/portaria?page=abc").text
    assert "Página 1 de 2" in get("/portaria?page=-4").text


# --- imagem do QR ----------------------------------------------------------


def test_qr_png_headers(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    response = world.a.admin.get(f"/links/{link.id}/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(PNG_SIGNATURE)


def test_qr_encodes_the_public_url(world, store, monkeypatch):
    seen = []
    original = qrcode.make

    def spy(data, *args, **kwargs):
        seen.append(data)
        return original(data, *args, **kwargs)

    monkeypatch.setattr(qrcode, "make", spy)
    link = store.add_link(world.a.condo_id, world.a.house_id)
    assert world.a.admin.get(f"/links/{link.id}/qr.png").status_code == 200
    assert seen == [f"{BASE_URL}/r/{link.token}"]


def test_qr_png_is_not_served_for_revoked_or_unknown_links(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id, active=False)
    assert world.a.admin.get(f"/links/{link.id}/qr.png").status_code == 404
    assert world.a.admin.get("/links/9999/qr.png").status_code == 404


def test_old_token_based_urls_no_longer_exist(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    assert world.a.admin.get(f"/qr/{link.token}.png").status_code == 404
    legacy = world.a.admin.get(f"/portaria?created={link.token}").text
    assert link.token not in legacy


# --- revogar, reativar, excluir -------------------------------------------


def test_link_lifecycle_is_audited_in_order(world, store, new_browser):
    admin = world.a.admin
    ident = link_id(issue_link(world))
    token = store.get(Access, id=ident).token
    unavailable = "Este acesso não está disponível"
    opens = lambda: unavailable not in new_browser().get(f"/r/{token}").text  # noqa: E731

    assert opens()
    assert admin.post(f"/links/{ident}/revoke").status_code == 303
    assert store.get(Access, id=ident).active is False
    assert not opens()

    assert admin.post(f"/links/{ident}/reactivate").status_code == 303
    assert store.get(Access, id=ident).active is True
    assert opens()

    assert admin.post(f"/links/{ident}/delete").status_code == 303
    assert store.get(Access, id=ident) is None
    assert not opens()

    assert [e.action for e in store.rows(Audit)] == [
        "link.create", "link.revoke", "link.reactivate", "link.delete",
    ]


def test_cannot_reactivate_a_link_of_an_inactive_house(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id, active=False)
    store.update(House, world.a.house_id, active=False)
    assert world.a.admin.post(f"/links/{link.id}/reactivate").status_code == 409
    assert store.get(Access, id=link.id).active is False


def test_links_of_an_inactive_condo_cannot_be_issued(world, store):
    store.update(Condo, world.a.condo_id, active=False)
    assert world.root.post("/links", house_id=world.a.house_id, gate_id="").status_code == 409
