"""FastAPI exception handlers for standardized error responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import GFMException


async def gfm_exception_handler(request: Request, exc: GFMException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": f"An unexpected error occurred: {str(exc)}",
            "status_code": 500,
            "path": request.url.path,
        },
    )
