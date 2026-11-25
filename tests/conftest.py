import pytest

# Importar "support" primeiro garante que o ambiente de teste (banco temporário
# etc.) esteja configurado antes de qualquer módulo ``app`` ser importado.
import support
from app import core


@pytest.fixture(autouse=True)
def clean_database():
    """Cada teste começa com tabelas vazias (sem sequer o superadmin)."""
    core.Base.metadata.drop_all(bind=core.engine)
    core.Base.metadata.create_all(bind=core.engine)


@pytest.fixture
def store():
    return support.store


@pytest.fixture
def new_browser():
    """Fábrica de navegadores sem sessão: ``new_browser()``."""
    return support.Browser


@pytest.fixture
def world():
    """Superadmin + condomínios Alfa (``world.a``) e Beta (``world.b``)."""
    return support.build_world()
