import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from app.core.db import Base, engine

os.environ["TESTING"] = "1"

@pytest.fixture(autouse=True)
def setup_db():
	Base.metadata.create_all(bind=engine)
	yield
	Base.metadata.drop_all(bind=engine)
