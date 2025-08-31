from dev.src.core.rabbitmq import rabbitmq
import logging
import json

logger = logging.getLogger("order-api")

async def handle_product_updated(message_bytes: bytes):
    try:
        data = json.loads(message_bytes)
        product_id = data.get("product_id")
        status = data.get("status")
        logger.info(f"[RabbitMQ] Produit mis à jour: id={product_id}, status={status}")
        # Ici, ajoute la logique pour marquer les commandes concernées comme invalides, etc.
    except Exception:
        logger.exception("Erreur lors du traitement de product.updated")

async def handle_client_updated(message_bytes: bytes):
    try:
        data = json.loads(message_bytes)
        client_id = data.get("client_id")
        status = data.get("status")
        logger.info(f"[RabbitMQ] Client mis à jour: id={client_id}, status={status}")
        # Ici, ajoute la logique pour annuler/refuser les commandes du client, etc.
    except Exception:
        logger.exception("Erreur lors du traitement de client.updated")

async def start_rabbitmq_consumers():
    await rabbitmq.connect()
    await rabbitmq.consume("product.updated", handle_product_updated)
    await rabbitmq.consume("client.updated", handle_client_updated)

# Pour lancer les consumers au démarrage FastAPI, ajoute dans lifespan/main.py :
#   from dev.src.services.rabbitmq_consumers import start_rabbitmq_consumers
#   await start_rabbitmq_consumers()
