"""FastAPI app — точка входа."""
from fastapi import FastAPI

from portal_api.routers import health

app = FastAPI(title="MIREA Agent Portal API", version="0.1.0")
app.include_router(health.router, prefix="/api")
