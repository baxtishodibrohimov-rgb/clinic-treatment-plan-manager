import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analysis, auth, cases, clinics, image_types, images, reminder_rules, settings_router, users, webhook
from app.config import get_settings
from app.jobs.periodic_sync import periodic_sync_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_task = asyncio.create_task(periodic_sync_loop())
    try:
        yield
    finally:
        sync_task.cancel()


app = FastAPI(title="Clinic Treatment Plan Manager API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clinics.router)
app.include_router(users.router)
app.include_router(cases.router)
app.include_router(analysis.router)
app.include_router(images.router)
app.include_router(image_types.router)
app.include_router(reminder_rules.router)
app.include_router(settings_router.router)
app.include_router(webhook.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
