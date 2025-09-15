from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine, SessionLocal
from app.core.log import setup_logging, access_log_middleware
from app.infra.events.rabbitmq import rabbitmq, start_consumer
from app.infra.events.handlers import (handle_customer_deleted,handle_customer_update_order,handle_customer_delete_order, handle_order_rejected)
from app.api import order_routes as order_router
from app.core.db import init_db

# --- Logging ---
setup_logging()
logger = logging.getLogger(__name__)

# --- Prometheus ---
REQUEST_COUNT = Counter(
    "http_requests_total", "Total des requêtes HTTP", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Latence des requêtes HTTP", ["method", "path"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("database connection OK")
        init_db()
    except Exception:
        logger.exception("database connectivity check failed")

    # The `Base.metadata.create_all` will be handled by Alembic in a real scenario
    # For now, we can leave it out as the models aren't defined yet.

    try:
        await rabbitmq.connect()
        logger.info("[order-api] RabbitMQ connecté, exchange=%s", rabbitmq.exchange_name)

        async def consumer_handler(payload: dict, rk: str):
            logger.info("[order-api] received %s: %s", rk, payload)
            db = SessionLocal()
            try:
                if rk == "customer.deleted":
                    await handle_customer_deleted(payload, db, rabbitmq)
                elif rk == "customer.update_order":
                    await handle_customer_update_order(payload, db, rabbitmq)
                elif rk == "customer.delete_order":
                    await handle_customer_delete_order(payload, db, rabbitmq)
                elif rk == "order.rejected":
                    await handle_order_rejected(payload, db, rabbitmq)
                else:
                    logger.warning(f"[order-api] event ignoré: {rk}")
            finally:
                db.close()

        # Démarre un consumer RabbitMQ
        asyncio.create_task(
            start_consumer(
                rabbitmq.connection,
                rabbitmq.exchange_name,
                rabbitmq.exchange_type,
                queue_name="order-events",
                patterns=["customer.#", "order.#"],
                handler=consumer_handler,
            )
        )

        logger.info("[order-api] Consumer lancé (q-order, patterns=product.#)")
    except Exception as e:
        logger.exception("[order-api] Échec initialisation RabbitMQ: %s", e)

    yield  # Application runs here

    # --- Shutdown ---
    try:
        await rabbitmq.disconnect()
        logger.info("RabbitMQ disconnected")
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    root_path=os.getenv("ROOT_PATH", ""),
    docs_url="/docs" if settings.ENV != "prod" else None,
    redoc_url="/redoc" if settings.ENV != "prod" else None,
    openapi_url="/openapi.json" if settings.ENV != "prod" else None,
)

# --- Middlewares ---
app.middleware("http")(access_log_middleware)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    duration = time.time() - start

    # Basic path templating for metrics
    path = request.url.path

    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(duration)
    return response


# --- CORS ---
allow_methods = (
    ["*"]
    if settings.CORS_ALLOW_METHODS == "*"
    else [m.strip() for m in settings.CORS_ALLOW_METHODS.split(",") if m.strip()]
)
allow_headers = (
    ["*"]
    if settings.CORS_ALLOW_HEADERS == "*"
    else [h.strip() for h in settings.CORS_ALLOW_HEADERS.split(",") if h.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)

# --- Tech endpoints ---
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# --- Routes ---
app.include_router(order_router.router)