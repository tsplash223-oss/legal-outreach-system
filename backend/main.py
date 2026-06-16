import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import DATABASE_URL, IS_POSTGRESQL, engine, Base, repair_postgresql_id_sequences
import models
from routers import auth, firms, newsletters
from security import hash_password, normalize_email
from services.email_sender import check_smtp_config
from services.gmail_reply_tracker import ensure_gmail_api_files_from_env
from settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
settings = get_settings()
settings.validate()


def bootstrap_admin_from_env():
    if not settings.admin_email or not settings.admin_password:
        return

    with Session(engine) as db:
        if db.query(models.User.id).count() > 0:
            return

        admin = models.User(
            email=normalize_email(settings.admin_email),
            full_name="System Administrator",
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Bootstrapped initial admin user from ADMIN_EMAIL.")


bootstrap_admin_from_env()
gmail_file_errors = ensure_gmail_api_files_from_env()
for gmail_file_error in gmail_file_errors:
    logger.warning("Gmail reply tracking configuration: %s", gmail_file_error)

default_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://legal-outreach-system-tsplash223-oss-projects.vercel.app",
]

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_origins = sorted(set(default_origins + frontend_origins + settings.cors_origins))

app = FastAPI(title="Prospective Client Outreach System API")


@app.middleware("http")
async def log_unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(auth.router)
app.include_router(firms.router)
app.include_router(newsletters.router)


@app.on_event("startup")
async def startup_checks():
    cors_message = (
        "CORS allowed origins: "
        f"{allowed_origins}; allow_origin_regex=https://.*\\.vercel\\.app"
    )
    print(cors_message)
    logger.info(cors_message)

    repaired_tables = repair_postgresql_id_sequences()
    if IS_POSTGRESQL:
        logger.info(
            "PostgreSQL ID sequence repair completed. repaired_tables=%s",
            repaired_tables,
        )


@app.get("/")
def root():
    return {"message": "Prospective Client Outreach System API Running"}


@app.get("/health")
def health():
    with Session(engine) as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/health/config")
def health_config():
    smtp_config = check_smtp_config()

    return {
        "database_url_type": "postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite",
        "gmail_address_present": smtp_config["gmail_address_present"],
        "gmail_app_password_present": smtp_config["gmail_app_password_present"],
        "gmail_app_password_length": smtp_config["gmail_app_password_length"],
        "google_maps_api_key_present": bool(os.getenv("GOOGLE_MAPS_API_KEY", "").strip()),
        "jwt_secret_present": bool(settings.jwt_secret),
        "cors_origins_count": len(allowed_origins),
    }


@app.get("/cors-test")
def cors_test():
    return {"cors": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
