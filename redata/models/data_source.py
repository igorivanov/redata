from redata.models.base import Base
from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String, JSON, ARRAY
from redata.db_operations import metrics_session
from redata.backends.postgrsql import Postgres
from redata.backends.mysql import MySQL
from redata.backends.bigquery import BigQuery
from redata.backends.exasol import Exasol, ExasolEngine
from sqlalchemy import create_engine
from redata import settings


class DataSource(Base):

    SUPPORTED_SOURCES = [
        ('bigquery', 'BigQuery',),
        ('postgres', 'PostgreSQL'),
        ('mysql', 'MySQL', ),
        ('exa+pyexasol', 'Exasol')
    ]

    __tablename__ = 'data_source'

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True)
    source_type = Column(String)
    host = Column(String)
    database = Column(String)
    user = Column(String)
    password = Column(String)

    schemas = Column(ARRAY(String))
    run_for_all = Column(Boolean, default=True)

    def __str__(self):
        return f"{self.name}"

    @property
    def db_url(self):
        if self.source_type == 'bigquery':
            return f'{self.source_type}://{self.host}'
        
        return f'{self.source_type}://{self.user}:{self.password}@{self.host}/{self.database}'
    
    def get_db_object(self):
        db_url = self.db_url
        
        if self.source_type == 'exa+pyexasol':
            return Exasol(self, ExasolEngine(db_url), schema=self.schemas)

        if self.source_type == 'bigquery':
            db = create_engine(db_url, credentials_path=settings.REDATA_BIGQUERY_DOCKER_CREDS_FILE_PATH)
            return BigQuery(self, db, schema=self.schemas)
        
        db = create_engine(db_url)

        if self.source_type == 'postgres':
            return Postgres(self, db, schema=self.schemas)

        if self.source_type == 'mysql':
            return MySQL(self, db, schema=self.schemas)

        raise Exception('Not supported DB')
    
    
    @classmethod
    def source_dbs(cls):
        if not getattr(cls, 'source_db_objects', None):
            sources = metrics_session.query(cls).all()
            source_dbs = [s.get_db_object() for s in sources]
            cls.source_db_objects = source_dbs

        return cls.source_db_objects


    def get_db_by_name(name):
        for source_db in settings.REDATA_SOURCE_DBS:
            if source_db['name'] == name:
                return get_db_object(source_db)