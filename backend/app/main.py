from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Transfer Index API")

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Transfer Index API running"}