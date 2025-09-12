import pytest
import json
from unittest.mock import AsyncMock, MagicMock
import aio_pika

from app.infra.events.rabbitmq import RabbitMQ, start_consumer

pytestmark = pytest.mark.asyncio

async def test_rabbitmq_connect_sets_exchange_and_channel(monkeypatch):
    conn = AsyncMock()
    channel = AsyncMock()
    exchange = MagicMock()

    conn.channel = AsyncMock(return_value=channel)
    channel.declare_exchange = AsyncMock(return_value=exchange)

    connect_robust = AsyncMock(return_value=conn)
    monkeypatch.setattr('app.infra.events.rabbitmq.aio_pika.connect_robust', connect_robust)

    r = RabbitMQ()
    await r.connect()

    assert r.connection is conn
    assert r.channel is channel
    assert r.exchange is exchange
    channel.declare_exchange.assert_awaited()

async def test_publish_message_topic_and_fanout(monkeypatch):
    r = RabbitMQ()
    # prepare a mock exchange with publish
    mock_exchange = AsyncMock()
    r.exchange = mock_exchange

    # TOPIC behaviour: routing key kept
    r.exchange_type = aio_pika.ExchangeType.TOPIC
    await r.publish_message('order.created', {'foo': 'bar'})
    assert mock_exchange.publish.await_count == 1
    call = mock_exchange.publish.await_args_list[-1]
    assert call.kwargs['routing_key'] == 'order.created'
    # payload body is JSON
    msg = call.args[0]
    assert msg.content_type == 'application/json'
    assert json.loads(msg.body.decode('utf-8')) == {'foo': 'bar'}

    # FANOUT behaviour: routing key ignored -> empty string
    r.exchange_type = aio_pika.ExchangeType.FANOUT
    await r.publish_message('should.be.ignored', {'x': 1})
    call2 = mock_exchange.publish.await_args_list[-1]
    assert call2.kwargs['routing_key'] == ''

async def test_publish_message_no_exchange_logs_error(monkeypatch):
    r = RabbitMQ()
    r.exchange = None
    # should not raise
    await r.publish_message('rk', {'a': 1})

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

async def test_start_consumer_bindings_topic_and_fanout(monkeypatch):
    # mock connection -> channel -> queue
    conn = AsyncMock()
    channel = AsyncMock()
    queue = MagicMock()

    channel.set_qos = AsyncMock()
    channel.declare_queue = AsyncMock(return_value=queue)
    conn.channel = AsyncMock(return_value=channel)

    # Topic case: expect bind called for each pattern
    queue.bind = AsyncMock()
    queue.iterator = lambda: _AsyncIteratorContext([])

    await start_consumer(conn, MagicMock(), aio_pika.ExchangeType.TOPIC, 'qname', ['p1', 'p2'], AsyncMock())
    assert queue.bind.await_count == 2

    # Fanout case: expect single bind with empty routing_key
    queue.bind.reset_mock()
    queue.iterator = lambda: _AsyncIteratorContext([])
    exchange = MagicMock()
    await start_consumer(conn, exchange, aio_pika.ExchangeType.FANOUT, 'qname', ['ignored'], AsyncMock())
    # ensure bind was awaited once and routing_key was empty, and exchange passed is same
    assert queue.bind.await_count == 1
    last = queue.bind.await_args_list[-1]
    assert last.kwargs.get('routing_key') == ''
    assert last.args[0] is exchange

async def test_start_consumer_message_processing_and_raw_payload(monkeypatch):
    # simulate one message with invalid json body
    class ProcessCtx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Msg:
        def __init__(self, body, rk):
            self.body = body
            self.routing_key = rk
            # return an async context manager when called
            self.process = lambda: ProcessCtx()
    msg = Msg(b'invalid json', 'rk1')

    # iterator yields our message then stops
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

    await start_consumer(conn, MagicMock(), aio_pika.ExchangeType.TOPIC, 'q', ['p'], handler)

    # handler must have been called with payload containing raw body
    handler.assert_awaited()
    called_with = handler.await_args_list[0][0]
    assert called_with[0] == {'raw': msg.body}
    assert called_with[1] == 'rk1'
