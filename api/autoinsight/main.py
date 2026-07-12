from fastapi import FastAPI

from autoinsight import health
from autoinsight.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="Auto Insight API")
    app.include_router(health.router)
    app.include_router(auth_router.router)
    return app


app = create_app()
