from fastapi import FastAPI

from app.api.routes import router
from app.database import engine, Base

from app.models.player_db import PlayerDB

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transfer Index API")

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Transfer Index API running"}