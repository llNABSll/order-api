from dev.src.api.routes import router as api_router
from contextlib         import asynccontextmanager
from fastapi            import FastAPI
from dev.src.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await rabbitmq.connect()
    try:
        yield
    finally:
        await rabbitmq.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(api_router)

@app.get("/")
def read_root():
    return "Order API is running"

from dev.src.rabbitmq import rabbitmq
