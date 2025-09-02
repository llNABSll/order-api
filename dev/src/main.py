from dev.src.rabbitmq.consumer import start_consumer
from dev.src.api.routes        import router as api_router
from contextlib                import asynccontextmanager
from dev.src.rabbitmq.config   import rabbitmq
from fastapi                   import FastAPI
from dev.src.db.init_db        import init_db
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await rabbitmq.connect()
    asyncio.create_task(start_consumer())
    try:
        yield
    finally:
        await rabbitmq.disconnect()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)

@app.get("/")
def read_root():
    return "Order API is running"
