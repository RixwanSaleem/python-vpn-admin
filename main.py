import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import ensure_db_schema
from app.routes import router


def create_app() -> FastAPI:
    # Ensure SQLite schema exists before serving.
    ensure_db_schema(settings.db_path)

    app = FastAPI(title="VPN Admin (Python)")

    # Session auth: store session data in a signed cookie.
    # Set SESSION_SECRET in production.
    session_max_age_raw = os.getenv("SESSION_MAX_AGE", "28800").strip()
    try:
        session_max_age = int(session_max_age_raw) if session_max_age_raw else None
    except ValueError:
        session_max_age = 28800

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,  # set True behind HTTPS if desired
        max_age=session_max_age,
    )

    app.include_router(router)
    return app


app = create_app()

