
from fastapi.testclient import TestClient
from dev.src.main import app
from dev.src.database import Base, engine

client = TestClient(app)

def before_all(context):
    """
    Crée les tables SQLite en mémoire avant tous les tests si on utilise SQLite.
    """
    url = str(engine.url)

def before_scenario(context, scenario):
    """
    Reset database state before each scenario.
    Utilise TestClient pour supprimer les commandes sans serveur externe.
    """
    Base.metadata.create_all(bind=engine)
    # Option 1 : dedicated testing endpoint (recommended)
    response = client.delete("/test/reset")
    if response.status_code != 200:
        # Option 2 : fallback if no reset endpoint available
        response = client.get("/orders/")
        if response.status_code == 200:
            for order in response.json():
                client.delete(f"/orders/{order['id']}")
