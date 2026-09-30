"""FastAPI exception handlers ensuring unified JSON error envelopes without stack traces."""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.utils.exceptions import SentinelDocException

logger = logging.getLogger("sentineldoc")


async def sentineldoc_exception_handler(request: Request, exc: SentinelDocException):
    """Handle custom SentinelDocException and render unified error JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI / Pydantic validation errors (HTTP 422)."""
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_messages.append(f"{loc}: {msg}")
    combined_msg = "; ".join(error_messages) if error_messages else "Request parameter validation failed."

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_PARAMETERS",
                "message": combined_msg,
                "status_code": 422,
                "details": exc.errors(),
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle standard FastAPI HTTPExceptions."""
    code_map = {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "PAYLOAD_TOO_LARGE",
        422: "INVALID_PARAMETERS",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "status_code": exc.status_code,
                "details": None,
            }
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected server errors (HTTP 500), hiding tracebacks."""
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred while processing the request.",
                "status_code": 500,
                "details": None,
            }
        },
    )
