import os
os.environ['DATABASE_URL']='sqlite:////tmp/scriptstudio-tests.sqlite'
os.environ['MEDIA_ROOT']='/tmp/scriptstudio-tests-media'
os.environ['LIVE_GENERATION_ENABLED']='false'
import pytest
from studio.db import Base, engine, transaction, Project
from studio.schemas import Settings, uid

@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

@pytest.fixture
def project_id():
    with transaction() as session:
        p=Project(id=uid(),name='Test',original_script='Hello world.',script='Hello world.',settings=Settings().model_dump())
        session.add(p)
        return p.id
