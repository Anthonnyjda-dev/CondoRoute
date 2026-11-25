"""Lacunas conhecidas: cada teste descreve o comportamento DESEJADO e hoje falha.

Estão marcados com xfail(strict=True): enquanto o problema existir a suíte fica
verde; quando alguém corrigir, o teste "passa inesperadamente", a suíte
falha e basta remover o marcador xfail para transformá-lo em teste normal.
"""

import pytest

from app.core import Access

PORTER_ONLY_ISSUES_AND_REVOKES = (
    "docs/04 (seção 3): o porteiro gera e revoga QR; reativar e excluir "
    "deveriam ser do administrador. Hoje qualquer perfil faz as duas coisas "
    "(app/main.py, rotas /links/{id}/reactivate e /links/{id}/delete)."
)


@pytest.mark.xfail(strict=True, reason=PORTER_ONLY_ISSUES_AND_REVOKES)
def test_porter_cannot_reactivate_a_link(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id, active=False)
    response = world.a.porter.post(f"/links/{link.id}/reactivate")
    assert response.status_code in (403, 404)
    assert store.get(Access, id=link.id).active is False


@pytest.mark.xfail(strict=True, reason=PORTER_ONLY_ISSUES_AND_REVOKES)
def test_porter_cannot_delete_a_link(world, store):
    link = store.add_link(world.a.condo_id, world.a.house_id)
    response = world.a.porter.post(f"/links/{link.id}/delete")
    assert response.status_code in (403, 404)
    assert store.get(Access, id=link.id) is not None
