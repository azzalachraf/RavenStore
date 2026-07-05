from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.database import AsyncSessionLocal
from app.models import ErrorLog

logger = structlog.get_logger("ravenstore.errors")


class AppError(Exception):
    def __init__(self, message_key: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message_key = message_key
        self.status_code = status_code
        super().__init__(message_key)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": {"message_key": exc.message_key}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> ORJSONResponse:
        details = [
            {"location": error.get("loc", ()), "type": error.get("type", "invalid")}
            for error in exc.errors()
        ]
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"message_key": "validation.invalid_request", "details": details}},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, __: IntegrityError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"message_key": "database.constraint_violation"}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.exception("request.unhandled_error", request_id=request_id, error_type=type(exc).__name__)
        try:
            async with AsyncSessionLocal() as session:
                session.add(
                    ErrorLog(
                        level="error",
                        message="system.unhandled_error",
                        trace_id=request_id,
                        error_metadata={"error_type": type(exc).__name__, "path": request.url.path},
                    )
                )
                await session.commit()
        except Exception:
            logger.exception("error_log.persistence_failed", request_id=request_id)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"message_key": "error.unexpected", "request_id": request_id}},
        )
