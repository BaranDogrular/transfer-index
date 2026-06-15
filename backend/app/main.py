from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database import engine, Base
from app.models.player_db import PlayerDB
from app.models.player_valuation_db import PlayerValuationDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.club_db import ClubDB

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transfer Index API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Transfer Index API running"}
