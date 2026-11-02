import os,subprocess,sys

def test_mysql_config_single_source():
 code="from app.db_settings import build_database_url; print(build_database_url().render_as_string(hide_password=False))"
 env={**os.environ,'MYSQL_PASSWORD':'123@abc#teste','MYSQL_USER':'condoroute','MYSQL_DATABASE':'condoroute','MYSQL_HOST':'db'}
 env.pop('DATABASE_URL',None)
 p=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
 assert p.returncode==0,p.stderr
 assert '123%40abc%23teste' in p.stdout
