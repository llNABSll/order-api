import pytest
import json
from unittest.mock import AsyncMock, MagicMock
import aio_pika

from app.infra.events.rabbitmq import RabbitMQ, start_consumer

pytestmark = pytest.mark.asyncio


# ---------- RabbitMQ.connect ----------
async def test_rabbitmq_connect_sets_exchange_and_channel(monkeypatch):
    conn = AsyncMock()
    channel = AsyncMock()
    exchange = MagicMock()

    conn.channel = AsyncMock(return_value=channel)
    channel.declare_exchange = AsyncMock(return_value=exchange)

    connect_robust = AsyncMock(return_value=conn)
    monkeypatch.setattr("app.infra.events.rabbitmq.aio_pika.connect_robust", connect_robust)

    r = RabbitMQ()
    await r.connect()

    assert r.connection is conn
    assert r.channel is channel
    assert r.exchange is exchange
    channel.declare_exchange.assert_awaited()


# ---------- RabbitMQ.disconnect ----------
async def test_disconnect_success_and_fail(monkeypatch, caplog):
    r = RabbitMQ()
    r.channel = AsyncMock()
    r.channel.is_closed = False
    r.connection = AsyncMock()
    r.connection.is_closed = False

    await r.disconnect()
    assert "RabbitMQ channel closed" in caplog.text
    assert "RabbitMQ connection closed" in caplog.text

    # simulate errors during close
    r.channel = AsyncMock()
    r.channel.is_closed = False
    r.channel.close = AsyncMock(side_effect=Exception("close fail"))
    r.connection = AsyncMock()
    r.connection.is_closed = False
    r.connection.close = AsyncMock(side_effect=Exception("conn fail"))

    await r.disconnect()
    assert "Failed to close RabbitMQ channel" in caplog.text
    assert "Failed to close RabbitMQ connection" in caplog.text


# ---------- RabbitMQ.publish_message ----------
async def test_publish_message_topic_and_fanout(monkeypatch):
    r = RabbitMQ()
    mock_exchange = AsyncMock()
    r.exchange = mock_exchange

    # TOPIC → routing_key kept
    r.exchange_type = aio_pika.ExchangeType.TOPIC
    await r.publish_message("order.created", {"foo": "bar"})
    call = mock_exchange.publish.await_args_list[-1]
    assert call.kwargs["routing_key"] == "order.created"
    msg = call.args[0]
    assert json.loads(msg.body.decode()) == {"foo": "bar"}

    # FANOUT → routing_key ignored
    r.exchange_type = aio_pika.ExchangeType.FANOUT
    await r.publish_message("ignored", {"x": 1})
    call2 = mock_exchange.publish.await_args_list[-1]
    assert call2.kwargs["routing_key"] == ""


async def test_publish_message_no_exchange_logs_error(caplog):
    r = RabbitMQ()
    r.exchange = None
    await r.publish_message("rk", {"a": 1})
    assert "exchange is not available" in caplog.text


async def test_publish_message_exception(caplog):
    r = RabbitMQ()
    mock_exchange = AsyncMock()
    mock_exchange.publish = AsyncMock(side_effect=Exception("publish fail"))
    r.exchange = mock_exchange
    r.exchange_type = aio_pika.ExchangeType.TOPIC

    await r.publish_message("rk", {"y": 2})
    assert "Failed to publish" in caplog.text


# ---------- start_consumer helpers ----------
class _EmptyAsyncIterator:
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


class _AsyncIteratorContext:
    def __init__(self, items):
        self._it = _EmptyAsyncIterator(items)

    async def __aenter__(self):
        return self._it

    async def __aexit__(self, exc_type, exc, tb):
        return False


# ---------- start_consumer ----------
async def test_start_consumer_bindings_topic_and_fanout():
    conn = AsyncMock()
    channel = AsyncMock()
    queue = MagicMock()
    channel.set_qos = AsyncMock()
    channel.declare_queue = AsyncMock(return_value=queue)
    conn.channel = AsyncMock(return_value=channel)

    queue.bind = AsyncMock()
    queue.iterator = lambda: _AsyncIteratorContext([])

    # topic → binds each pattern
    await start_consumer(conn, MagicMock(), aio_pika.ExchangeType.TOPIC, "q", ["p1", "p2"], AsyncMock())
    assert queue.bind.await_count == 2

    # fanout → single bind empty rk
    queue.bind.reset_mock()
    queue.iterator = lambda: _AsyncIteratorContext([])
    exchange = MagicMock()
    await start_consumer(conn, exchange, aio_pika.ExchangeType.FANOUT, "q", ["ignored"], AsyncMock())
    call = queue.bind.await_args_list[-1]
    assert call.kwargs.get("routing_key") == ""
    assert call.args[0] is exchange


async def test_start_consumer_message_processing_and_raw_payload():
    class ProcessCtx:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False

    class Msg:
        def __init__(self, body, rk):
            self.body = body
            self.routing_key = rk
            self.process = lambda: ProcessCtx()

    msg = Msg(b"notjson", "rk1")
    iterator_ctx = _AsyncIteratorContext([msg])

    conn = AsyncMock()
    channel = AsyncMock()
    queue = MagicMock()
    channel.set_qos = AsyncMock()
    channel.declare_queue = AsyncMock(return_value=queue)
    conn.channel = AsyncMock(return_value=channel)
    queue.bind = AsyncMock()
    queue.iterator = lambda: iterator_ctx

    handler = AsyncMock()
    await start_consumer(conn, MagicMock(), aio_pika.ExchangeType.TOPIC, "q", ["p"], handler)

    handler.assert_awaited()
    called_with = handler.await_args_list[0][0]
    assert called_with[0] == {"raw": msg.body}
    assert called_with[1] == "rk1"


async def test_start_consumer_handler_exception(caplog):
    class ProcessCtx:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False

    class Msg:
        def __init__(self):
            self.body = b'{"ok": 1}'
            self.routing_key = "rk"
            self.process = lambda: ProcessCtx()

    msg = Msg()
    iterator_ctx = _AsyncIteratorContext([msg])

    conn = AsyncMock()
    channel = AsyncMock()
    queue = MagicMock()
    channel.set_qos = AsyncMock()
    channel.declare_queue = AsyncMock(return_value=queue)
    conn.channel = AsyncMock(return_value=channel)
    queue.bind = AsyncMock()
    queue.iterator = lambda: iterator_ctx

    bad_handler = AsyncMock(side_effect=Exception("boom"))
    await start_consumer(conn, MagicMock(), aio_pika.ExchangeType.TOPIC, "q", ["p"], bad_handler)

    assert "Handler error" in caplog.text
