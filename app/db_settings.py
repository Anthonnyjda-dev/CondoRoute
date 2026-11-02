import os
from sqlalchemy.engine import URL

def build_database_url():
    if os.getenv('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    if os.getenv('MYSQL_PASSWORD'):
        return URL.create('mysql+pymysql',username=os.getenv('MYSQL_USER','condoroute'),password=os.environ['MYSQL_PASSWORD'],host=os.getenv('MYSQL_HOST','db'),port=3306,database=os.getenv('MYSQL_DATABASE','condoroute'))
    return 'sqlite:///./condoroute.db'
