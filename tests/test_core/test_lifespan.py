import logging
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock
from app.main import lifespan

def test_lifespan_database_ok(monkeypatch):
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    monkeypatch.setattr("app.main.engine", mock_engine)
    monkeypatch.setattr("app.main.init_db", lambda: None)
    mock_rabbit = MagicMock()
    mock_rabbit.connect = AsyncMock()
    mock_rabbit.disconnect = AsyncMock()
    mock_rabbit.exchange_name = "test"
    monkeypatch.setattr("app.main.rabbitmq", mock_rabbit)
    monkeypatch.setattr("app.main.start_consumer", AsyncMock())
    app = FastAPI()
    async def run_lifespan():
        async with lifespan(app):
            pass
    import asyncio
    asyncio.run(run_lifespan())
    mock_engine.connect.assert_called()
    mock_rabbit.connect.assert_awaited()
    mock_rabbit.disconnect.assert_awaited()

def test_lifespan_database_fail(monkeypatch, caplog):
    def fail_connect():
        raise Exception("fail")
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = fail_connect
    monkeypatch.setattr("app.main.engine", mock_engine)
    monkeypatch.setattr("app.main.init_db", lambda: None)
    mock_rabbit = MagicMock()
    mock_rabbit.connect = AsyncMock()
    mock_rabbit.disconnect = AsyncMock()
    mock_rabbit.exchange_name = "test"
    monkeypatch.setattr("app.main.rabbitmq", mock_rabbit)
    monkeypatch.setattr("app.main.start_consumer", AsyncMock())
    app = FastAPI()
    import asyncio
    async def run_lifespan():
        with caplog.at_level(logging.ERROR):
            async with lifespan(app):
                pass
    asyncio.run(run_lifespan())
    assert "database connectivity check failed" in caplog.text

def test_lifespan_rabbitmq_fail(monkeypatch, caplog):
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = MagicMock()
    monkeypatch.setattr("app.main.engine", mock_engine)
    monkeypatch.setattr("app.main.init_db", lambda: None)
    mock_rabbit = MagicMock()
    mock_rabbit.connect = AsyncMock(side_effect=Exception("rabbit fail"))
    mock_rabbit.disconnect = AsyncMock()
    mock_rabbit.exchange_name = "test"
    import asyncio
    app = FastAPI()
    async def run_lifespan():
        with caplog.at_level(logging.ERROR):
            async with lifespan(app):
                pass
    asyncio.run(run_lifespan())
    assert "Échec initialisation RabbitMQ" in caplog.text
