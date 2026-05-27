from fastapi import FastAPI
from database import engine, Base
import models
from routers import firms

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Legal Outreach System API")

app.include_router(firms.router)

@app.get("/")
def root():
    return {"message": "Legal Outreach System API Running"}