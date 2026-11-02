import pytest
from app.core import hash_password,verify_password,validate_coords,map_url

def test_password():
 p=hash_password('umaSenhaBemForte2026')
 assert verify_password('umaSenhaBemForte2026',p)
 assert not verify_password('errada',p)
def test_coords():
 assert validate_coords(-10.7012942,-37.4131006)==(-10.7012942,-37.4131006)
 with pytest.raises(ValueError):validate_coords(-91,0)
def test_maps():
 for p in ('google','apple','waze'):
  assert '37.4131006' in map_url(p,-10.7012942,-37.4131006)
 with pytest.raises(ValueError):map_url('other',0,0)
