__author__ = 'Dimitris'
import sqlalchemy as sa

class dbObj(object):
    def __init__(self):
        pass

    def connect(self):
        connStr = "mssql+pyodbc://Dimitris:123456@192.168.1.10\SQLEXPRESS/Research?driver=/usr/local/lib/libtdsodbc.so"
        engine = sa.create_engine(connStr)
        return engine
