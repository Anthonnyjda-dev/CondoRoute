import os, re, json, hashlib, hmac, secrets
from urllib.parse import urlencode
from .db_settings import build_database_url
from sqlalchemy import create_engine, inspect, text, String, Integer, Float, ForeignKey, Boolean, DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL=build_database_url()
engine=create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'check_same_thread':False} if str(DATABASE_URL).startswith('sqlite') else {})
SessionLocal=sessionmaker(bind=engine)
class Base(DeclarativeBase): pass
class Condo(Base):
 __tablename__='condominiums'
 id:Mapped[int]=mapped_column(primary_key=True)
 name:Mapped[str]=mapped_column(String(150))
 active:Mapped[bool]=mapped_column(Boolean,default=True)
class User(Base):
 __tablename__='users'
 id:Mapped[int]=mapped_column(primary_key=True)
 condo_id:Mapped[int|None]=mapped_column(ForeignKey('condominiums.id'),nullable=True)
 name:Mapped[str]=mapped_column(String(120))
 email:Mapped[str]=mapped_column(String(180),unique=True)
 password_hash:Mapped[str]=mapped_column(String(255))
 role:Mapped[str]=mapped_column(String(20))
 active:Mapped[bool]=mapped_column(Boolean,default=True)
class Gate(Base):
 __tablename__='gates'
 id:Mapped[int]=mapped_column(primary_key=True)
 condo_id:Mapped[int]=mapped_column(ForeignKey('condominiums.id'))
 name:Mapped[str]=mapped_column(String(100))
 lat:Mapped[float|None]=mapped_column(Float,nullable=True)
 lng:Mapped[float|None]=mapped_column(Float,nullable=True)
 active:Mapped[bool]=mapped_column(Boolean,default=True)
class House(Base):
 __tablename__='houses'
 __table_args__=(UniqueConstraint('condo_id','block','number',name='uq_home_identity'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 condo_id:Mapped[int]=mapped_column(ForeignKey('condominiums.id'))
 block:Mapped[str]=mapped_column(String(30))
 number:Mapped[str]=mapped_column(String(30))
 lat:Mapped[float]=mapped_column(Float)
 lng:Mapped[float]=mapped_column(Float)
 reference:Mapped[str]=mapped_column(String(255),default='')
 route_geometry:Mapped[str|None]=mapped_column(Text,nullable=True)
 route_verified:Mapped[bool]=mapped_column(Boolean,default=False)
 active:Mapped[bool]=mapped_column(Boolean,default=True)
class Access(Base):
 __tablename__='access_links'
 id:Mapped[int]=mapped_column(primary_key=True)
 condo_id:Mapped[int]=mapped_column(ForeignKey('condominiums.id'))
 house_id:Mapped[int]=mapped_column(ForeignKey('houses.id'))
 gate_id:Mapped[int|None]=mapped_column(ForeignKey('gates.id'),nullable=True)
 token:Mapped[str]=mapped_column(String(70),unique=True)
 active:Mapped[bool]=mapped_column(Boolean,default=True)
 created_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
class Audit(Base):
 __tablename__='audit_events'
 id:Mapped[int]=mapped_column(primary_key=True)
 condo_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
 user_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
 action:Mapped[str]=mapped_column(String(100))
 detail:Mapped[str]=mapped_column(String(255),default='')
 created_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())

def hash_password(password):
 salt=secrets.token_hex(16)
 iters=310000
 encoded=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),iters).hex()
 return f'pbkdf2_sha256${iters}${salt}${encoded}'
def verify_password(password,stored):
 try:
  _,i,s,d=stored.split('$')
  result=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(s),int(i)).hex()
  return hmac.compare_digest(result,d)
 except (ValueError,AttributeError):return False

def validate_coords(lat,lng):
 lat=float(lat);lng=float(lng)
 if not -90<=lat<=90 or not -180<=lng<=180:raise ValueError('Coordenadas fora da faixa válida')
 return lat,lng

def map_url(provider,lat,lng,origin=None):
 lat,lng=validate_coords(lat,lng)
 dest=f'{lat:.7f},{lng:.7f}'
 if provider=='google':
  params={'api':'1','destination':dest,'travelmode':'driving','dir_action':'navigate'}
  if origin:params['origin']=f'{origin[0]:.7f},{origin[1]:.7f}'
  return 'https://www.google.com/maps/dir/?'+urlencode(params)
 if provider=='waze':return 'https://waze.com/ul?'+urlencode({'ll':dest,'navigate':'yes'})
 if provider=='apple':return 'https://maps.apple.com/?'+urlencode({'daddr':dest,'dirflg':'d'})
 raise ValueError('Provedor não suportado')

MAX_ROUTE_POINTS=500

def parse_route(raw):
 """Converte o texto digitado em [[lat,lng],...] validado.

 Aceita uma linha "latitude, longitude" por ponto ou um array JSON.
 Texto vazio significa "sem rota" e devolve lista vazia.
 """
 raw=(raw or '').strip()
 if not raw:return []
 if raw.startswith('['):
  try:items=json.loads(raw)
  except ValueError:raise ValueError('Geometria inválida: o JSON está malformado')
 else:
  items=[]
  for number,line in enumerate(raw.splitlines(),1):
   if not line.strip():continue
   parts=[p for p in re.split(r'[,;\s]+',line.strip()) if p]
   if len(parts)!=2:raise ValueError(f'Linha {number}: use o formato "latitude, longitude"')
   items.append(parts)
 if not isinstance(items,list) or len(items)<2:raise ValueError('Informe pelo menos 2 pontos para formar um percurso')
 if len(items)>MAX_ROUTE_POINTS:raise ValueError(f'Use no máximo {MAX_ROUTE_POINTS} pontos')
 points=[]
 for number,item in enumerate(items,1):
  if not isinstance(item,(list,tuple)) or len(item)!=2:raise ValueError(f'Ponto {number}: use [latitude, longitude]')
  try:points.append(list(validate_coords(item[0],item[1])))
  except (ValueError,TypeError):raise ValueError(f'Ponto {number}: coordenadas inválidas')
 return points

def format_route(stored):
 """Inverso de parse_route: JSON salvo -> uma linha "lat, lng" por ponto."""
 try:points=json.loads(stored) if stored else []
 except ValueError:return ''
 if not isinstance(points,list):return ''
 return '\n'.join(f'{p[0]}, {p[1]}' for p in points if isinstance(p,list) and len(p)==2)

# create_all não altera tabelas que já existem. Cada item abaixo acrescenta uma
# coluna nova a bancos criados por versões anteriores. Trocar por Alembic quando
# as migrações versionadas forem adotadas.
SCHEMA_PATCHES=(('gates','active','BOOLEAN NOT NULL DEFAULT 1'),)

def ensure_schema():
 inspector=inspect(engine)
 for table,column,ddl in SCHEMA_PATCHES:
  if table not in inspector.get_table_names():continue
  if column in {c['name'] for c in inspector.get_columns(table)}:continue
  with engine.begin() as conn:conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))

def bootstrap():
 Base.metadata.create_all(bind=engine)
 ensure_schema()
 email=os.getenv('ADMIN_EMAIL','').strip().lower(); password=os.getenv('ADMIN_PASSWORD','')
 if email and password:
  if len(password)<12:raise RuntimeError('ADMIN_PASSWORD precisa ter pelo menos 12 caracteres')
  with SessionLocal() as db:
   if not db.query(User).filter_by(email=email).first():
    db.add(User(name='Administrador',email=email,password_hash=hash_password(password),role='superadmin',condo_id=None));db.commit()
