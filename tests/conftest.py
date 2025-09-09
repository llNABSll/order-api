import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from app.core.db import Base, engine, get_db, SessionLocal
from fastapi.testclient import TestClient
from app.main import app

os.environ["TESTING"] = "1"

@pytest.fixture(autouse=True)
def setup_db():
	Base.metadata.create_all(bind=engine)
	yield
	Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
	def override_get_db():
		db = SessionLocal()
		try:
			yield db
		finally:
			db.close()
	app.dependency_overrides[get_db] = override_get_db
	yield TestClient(app)
	app.dependency_overrides.clear()
