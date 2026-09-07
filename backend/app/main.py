from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, cases, clinics, image_types, reminder_rules, settings_router, users, webhook
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Clinic Treatment Plan Manager API", version="0.1.0")

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
app.include_router(image_types.router)
app.include_router(reminder_rules.router)
app.include_router(settings_router.router)
app.include_router(webhook.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
