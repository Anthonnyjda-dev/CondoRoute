import os,io,secrets,json
from contextlib import asynccontextmanager
from urllib.parse import quote
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import qrcode
from .core import *

@asynccontextmanager
async def lifespan(app):
 bootstrap();yield
app=FastAPI(title='CondoRoute',lifespan=lifespan,docs_url=None,redoc_url=None)
secret=os.getenv('SESSION_SECRET','local-development-only-change-me')
if os.getenv('APP_ENV')=='production' and (len(secret)<32 or secret=='local-development-only-change-me'):raise RuntimeError('SESSION_SECRET inseguro para produção')
app.add_middleware(SessionMiddleware,secret_key=secret,https_only=os.getenv('SESSION_HTTPS','false').lower()=='true',same_site='lax')
app.mount('/static',StaticFiles(directory='app/static'),name='static')
templates=Jinja2Templates(directory='app/templates')

def db_dep():
 with SessionLocal() as db:yield db

def current_user(request:Request,db:Session):
 uid=request.session.get('uid')
 if uid:
  u=db.get(User,uid)
  if u and u.active:return u
 return None

def require(request,db):
 u=current_user(request,db)
 if not u:raise HTTPException(401,'Faça login')
 return u

def visible(db,u,model):
 q=db.query(model)
 if u.role!='superadmin':q=q.filter(model.condo_id==u.condo_id)
 return q

def allowed(u,condo_id):return u.role=='superadmin' or u.condo_id==condo_id

def csrf(request):
 if 'csrf' not in request.session:request.session['csrf']=secrets.token_urlsafe(24)
 return request.session['csrf']
def check_csrf(request,token):
 if not token or not secrets.compare_digest(request.session.get('csrf',''),token):raise HTTPException(403,'Formulário inválido. Atualize a página e tente novamente.')
def redirect(url):return RedirectResponse(url,status_code=303)
def page(request,template,**ctx):return templates.TemplateResponse(request,template,{'csrf':csrf(request),**ctx})
def audit(db,u,action,detail,condo=None):db.add(Audit(condo_id=condo or u.condo_id,user_id=u.id,action=action,detail=detail[:255]))

@app.get('/health')
def health():return {'status':'ok'}
@app.get('/login')
def login_page(request:Request):return page(request,'login.html',error='')
@app.post('/login')
def login_post(request:Request,email:str=Form(...),password:str=Form(...),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 check_csrf(request,csrf_token)
 u=db.query(User).filter_by(email=email.strip().lower(),active=True).first()
 if not u or not verify_password(password,u.password_hash):return page(request,'login.html',error='E-mail ou senha inválidos.')
 request.session.clear();request.session['uid']=u.id;csrf(request)
 return redirect('/dashboard')
@app.post('/logout')
def logout(request:Request,csrf_token:str=Form(...)):
 check_csrf(request,csrf_token);request.session.clear();return redirect('/login')
@app.get('/')
def root(request:Request):return redirect('/dashboard' if request.session.get('uid') else '/login')
@app.get('/dashboard')
def dashboard(request:Request,db:Session=Depends(db_dep)):
 u=require(request,db)
 condos=db.query(Condo).all() if u.role=='superadmin' else db.query(Condo).filter_by(id=u.condo_id).all()
 houses=visible(db,u,House).all();gates=visible(db,u,Gate).all();links=visible(db,u,Access).order_by(Access.id.desc()).limit(6).all()
 return page(request,'dashboard.html',user=u,condos=condos,houses=houses,gates=gates,links=links,section='dashboard',title='Visão geral')
@app.get('/manage')
def manage(request:Request,db:Session=Depends(db_dep)):
 u=require(request,db)
 condos=db.query(Condo).order_by(Condo.name).all() if u.role=='superadmin' else db.query(Condo).filter_by(id=u.condo_id).all()
 return page(request,'manage.html',user=u,condos=condos,houses=visible(db,u,House).order_by(House.id.desc()).all(),gates=visible(db,u,Gate).all(),section='manage',title='Condomínios')
@app.post('/condos')
def add_condo(request:Request,name:str=Form(...),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token)
 if u.role!='superadmin':raise HTTPException(403)
 name=name.strip()
 if len(name)<3 or len(name)>150:raise HTTPException(422,'Nome deve conter entre 3 e 150 caracteres')
 c=Condo(name=name);db.add(c);db.flush();audit(db,u,'condominium.create',name,c.id);db.commit();return redirect(f'/condominios/{c.id}?success=condo')
@app.post('/gates')
def add_gate(request:Request,condo_id:int=Form(...),name:str=Form(...),lat:str=Form(''),lng:str=Form(''),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token)
 if u.role not in ('superadmin','admin') or not allowed(u,condo_id) or not db.get(Condo,condo_id):raise HTTPException(403)
 name=name.strip()
 if not name:raise HTTPException(422,'Informe o nome da portaria')
 if bool(lat.strip()) != bool(lng.strip()):raise HTTPException(422,'Preencha latitude e longitude da portaria juntas')
 try:coords=validate_coords(lat,lng) if lat.strip() else (None,None)
 except ValueError as e:raise HTTPException(422,str(e))
 g=Gate(condo_id=condo_id,name=name[:100],lat=coords[0],lng=coords[1]);db.add(g);audit(db,u,'gate.create',name,condo_id);db.commit();return redirect(f'/condominios/{condo_id}?success=gate')
@app.post('/houses')
def add_house(request:Request,condo_id:int=Form(...),block:str=Form(...),number:str=Form(...),lat:str=Form(...),lng:str=Form(...),reference:str=Form(''),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token)
 if u.role not in ('superadmin','admin') or not allowed(u,condo_id) or not db.get(Condo,condo_id):raise HTTPException(403)
 try:a,b=validate_coords(lat,lng)
 except ValueError as e:raise HTTPException(422,str(e))
 block=block.strip().upper();number=number.strip().upper()
 if not block or not number:raise HTTPException(422,'Informe quadra e número')
 h=House(condo_id=condo_id,block=block[:30],number=number[:30],lat=a,lng=b,reference=reference.strip()[:255]);db.add(h);audit(db,u,'house.create',f'{block}/{number}',condo_id)
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'Esta quadra e residência já estão cadastradas')
 return redirect(f'/condominios/{condo_id}?success=house')
@app.post('/houses/{hid}/update')
def update_house(hid:int,request:Request,block:str=Form(...),number:str=Form(...),lat:str=Form(...),lng:str=Form(...),reference:str=Form(''),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token);h=db.get(House,hid)
 if not h or not allowed(u,h.condo_id) or u.role not in ('superadmin','admin'):raise HTTPException(404)
 try:a,b=validate_coords(lat,lng)
 except ValueError as e:raise HTTPException(422,str(e))
 if not block.strip() or not number.strip():raise HTTPException(422,'Quadra e casa obrigatórias')
 # Reset route validation because the destination may have moved.
 if h.lat!=a or h.lng!=b:h.route_verified=False
 h.block=block.strip().upper()[:30];h.number=number.strip().upper()[:30];h.lat=a;h.lng=b;h.reference=reference.strip()[:255]
 audit(db,u,'house.update',f'{hid}',h.condo_id)
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'Quadra e número duplicados')
 return redirect(f'/condominios/{h.condo_id}?success=updated')
@app.post('/users')
def add_user(request:Request,condo_id:int=Form(...),name:str=Form(...),email:str=Form(...),password:str=Form(...),role:str=Form(...),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token)
 if not allowed(u,condo_id) or u.role not in ('superadmin','admin'):raise HTTPException(403)
 if role not in ('admin','porter') or (u.role=='admin' and role!='porter'):raise HTTPException(403)
 if len(password)<12:raise HTTPException(422,'Senha deve ter 12 caracteres ou mais')
 if not db.get(Condo,condo_id):raise HTTPException(422,'Condomínio inválido')
 db.add(User(condo_id=condo_id,name=name.strip()[:120],email=email.strip().lower()[:180],password_hash=hash_password(password),role=role));audit(db,u,'user.create',email,condo_id)
 try:db.commit()
 except IntegrityError:db.rollback();raise HTTPException(409,'E-mail já cadastrado')
 return redirect('/usuarios?success=user')
@app.get('/portaria')
def portaria(request:Request,db:Session=Depends(db_dep)):
 u=require(request,db)
 condos=db.query(Condo).all() if u.role=='superadmin' else db.query(Condo).filter_by(id=u.condo_id).all()
 houses=visible(db,u,House).filter(House.active==True).order_by(House.block,House.number).all()
 gates=visible(db,u,Gate).all()
 try: p=max(1,int(request.query_params.get('page','1')))
 except ValueError:p=1
 q=visible(db,u,Access)
 total=q.count();pages=max(1,(total+9)//10);p=min(p,pages)
 links=q.order_by(Access.id.desc()).offset((p-1)*10).limit(10).all()
 created=request.query_params.get('created','')
 created_link=q.filter(Access.token==created).first() if created else None
 return page(request,'portaria.html',user=u,section='portaria',title='Portaria e QR Code',condos=condos,houses=houses,gates=gates,links=links,created_link=created_link,p=p,pages=pages,total=total,public_url=os.getenv('PUBLIC_BASE_URL','http://localhost:8000').rstrip('/'))

@app.get('/condominios/{cid}')
def condo_detail(cid:int,request:Request,db:Session=Depends(db_dep)):
 u=require(request,db);c=db.get(Condo,cid)
 if not c or not allowed(u,cid):raise HTTPException(404,'Condomínio não encontrado')
 houses=visible(db,u,House).filter(House.condo_id==cid).order_by(House.block,House.number).all()
 gates=visible(db,u,Gate).filter(Gate.condo_id==cid).order_by(Gate.name).all()
 return page(request,'condo_detail.html',user=u,condo=c,houses=houses,gates=gates,section='manage',title=c.name)
@app.get('/usuarios')
def users_page(request:Request,db:Session=Depends(db_dep)):
 u=require(request,db)
 if u.role not in ('superadmin','admin'):raise HTTPException(403)
 condos=db.query(Condo).order_by(Condo.name).all() if u.role=='superadmin' else db.query(Condo).filter_by(id=u.condo_id).all()
 users=db.query(User).order_by(User.name).all() if u.role=='superadmin' else db.query(User).filter_by(condo_id=u.condo_id).all()
 return page(request,'users.html',user=u,condos=condos,users=users,section='users',title='Usuários e permissões')
@app.post('/links/{aid}/reactivate')
def reactivate(aid:int,request:Request,csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token);access=db.get(Access,aid)
 if not access or not allowed(u,access.condo_id):raise HTTPException(404)
 house=db.get(House,access.house_id)
 if not house or not house.active:raise HTTPException(409,'A residência precisa estar ativa')
 access.active=True;audit(db,u,'link.reactivate',str(aid),access.condo_id);db.commit();return redirect('/portaria?success=reactivated')
@app.post('/links/{aid}/delete')
def delete_link(aid:int,request:Request,csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token);access=db.get(Access,aid)
 if not access or not allowed(u,access.condo_id):raise HTTPException(404)
 # Keep audit records but remove the token permanently.
 audit(db,u,'link.delete',f'id={aid} house={access.house_id}',access.condo_id)
 db.delete(access);db.commit();return redirect('/portaria?success=deleted')

@app.post('/links')
def create_link(request:Request,house_id:int=Form(...),gate_id:str=Form(''),csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token);h=db.get(House,house_id)
 if not h or not h.active or not allowed(u,h.condo_id):raise HTTPException(404,'Residência indisponível')
 gid=int(gate_id) if gate_id else None
 if gid:
  g=db.get(Gate,gid)
  if not g or g.condo_id!=h.condo_id:raise HTTPException(422,'Portaria não pertence ao mesmo condomínio')
 a=Access(condo_id=h.condo_id,house_id=h.id,gate_id=gid,token=secrets.token_urlsafe(32));db.add(a);audit(db,u,'link.create',f'house={h.id}',h.condo_id);db.commit();return redirect('/portaria?created='+a.token)
@app.post('/links/{aid}/revoke')
def revoke(aid:int,request:Request,csrf_token:str=Form(...),db:Session=Depends(db_dep)):
 u=require(request,db);check_csrf(request,csrf_token);a=db.get(Access,aid)
 if not a or not allowed(u,a.condo_id):raise HTTPException(404)
 a.active=False;audit(db,u,'link.revoke',str(a.id),a.condo_id);db.commit();return redirect('/portaria?success=revoked')
@app.get('/qr/{token}.png')
def qr_png(token:str,request:Request,db:Session=Depends(db_dep)):
 u=require(request,db);a=db.query(Access).filter_by(token=token).first()
 if not a or not allowed(u,a.condo_id) or not a.active:raise HTTPException(404)
 url=os.getenv('PUBLIC_BASE_URL','http://localhost:8000').rstrip('/')+'/r/'+token
 img=qrcode.make(url);buf=io.BytesIO();img.save(buf,format='PNG');buf.seek(0)
 return StreamingResponse(buf,media_type='image/png',headers={'Content-Disposition':'inline; filename="condoroute-qr.png"','Cache-Control':'no-store'})
@app.get('/r/{token}',response_class=HTMLResponse)
def public_route(token:str,request:Request,db:Session=Depends(db_dep)):
 a=db.query(Access).filter_by(token=token,active=True).first()
 if not a:return page(request,'unavailable.html')
 h=db.get(House,a.house_id);c=db.get(Condo,a.condo_id);g=db.get(Gate,a.gate_id) if a.gate_id else None
 if not h or not h.active or not c or not c.active:return page(request,'unavailable.html')
 origin=(g.lat,g.lng) if g and g.lat is not None and g.lng is not None else None
 urls={p:map_url(p,h.lat,h.lng,origin) for p in ('google','waze','apple')}
 geometry=None
 if h.route_verified and h.route_geometry:
  try:
   candidate=json.loads(h.route_geometry)
   if isinstance(candidate,list) and len(candidate)>=2 and all(isinstance(x,list) and len(x)==2 for x in candidate):geometry=candidate
  except (ValueError,TypeError):pass
 return page(request,'public.html',condo=c,house=h,gate=g,urls=urls,geometry=geometry)
@app.get('/api/health')
def api_health():return {'ok':True}
