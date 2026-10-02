from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app import models  # Register every ORM model before queries resolve foreign keys.
from app.core.config import get_settings
from app.core.exceptions import ResourceNotFound
from app.route.api import api_router

def create_app() -> FastAPI:
    application = FastAPI(title=get_settings().app_name, version="0.1.0")

    @application.exception_handler(ResourceNotFound)
    async def not_found_handler(request: Request, exc: ResourceNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        """Process liveness only; does not query the database."""
        return {"status": "ok"}

    application.include_router(api_router)
    return application

app = create_app()
