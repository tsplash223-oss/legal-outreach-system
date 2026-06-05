from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routers import firms, newsletters

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prospective Client Outreach System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://legal-outreach-system.vercel.app",
        "https://legal-outreach-system.onrender.com",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "file://",
        "null",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(firms.router)
app.include_router(newsletters.router)

@app.get("/")
def root():
    return {"message": "Prospective Client Outreach System API Running"}
