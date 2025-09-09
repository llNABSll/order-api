from __future__ import annotations

import logging
import sys, json
from fastapi import Request, Response
from uvicorn.logging import ColourizedFormatter
from app.core.config import settings


class _RequestIdLogFilter(logging.Filter):
    """Injecte le request_id dans tous les logs d'une requête."""

    def filter(self, record: logging.LogRecord) -> bool:
        # request_id est ajouté par le middleware access
        record.request_id = getattr(record, "request_id", "-")  # type: ignore
        return True


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname.upper(),
            "logger": record.name,
            "msg": record.getMessage(),
            "service": getattr(settings, "APP_NAME", "order-api"),
            "request_id": getattr(record, "request_id", "-"),
        }

        # Merge extras (method, path, status, latency_ms, etc.)
        for k, v in record.__dict__.items():
            if k not in log_obj and k not in (
                "message", "args", "levelname", "name", "pathname", "lineno",
                "exc_info", "exc_text", "stack_info", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName", "process"
            ):
                log_obj[k] = v

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging():
    """Configure le logging pour l'application."""
    log_level = settings.LOG_LEVEL.upper()
    log_format = settings.LOG_FORMAT.lower()

    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        formatter = _JsonLogFormatter(
            '{"ts":"%(asctime)s","level":"%(levelno)s","logger":"%(logger)s",'
            '"msg":"%(message)s","service":"%(service)s","request_id":"%(request_id)s"}',
            "%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        formatter = ColourizedFormatter("%(levelprefix)s %(name)s - %(message)s", use_colors=True)

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    root_logger.addFilter(_RequestIdLogFilter())

    # Moins de bruit
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


async def access_log_middleware(request: Request, call_next) -> Response:
    """Middleware pour logguer les requêtes et réponses avec un request_id."""
    import time, uuid

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    logger = logging.getLogger("app.access")
    extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "-",
        "user_agent": request.headers.get("user-agent", "-"),
    }

    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)

    extra["status"] = response.status_code
    extra["latency_ms"] = duration_ms

    logger.info("request", extra=extra)

    return response
