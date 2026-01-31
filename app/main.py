from fastapi import FastAPI
from app.database import engine
from . import models
from .routers import auth, users, trains, bookings, payment
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
models.Base.metadata.create_all(bind=engine)


app = FastAPI(title="RailBay")


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trains.router)
app.include_router(bookings.router)
app.include_router(payment.router)


@app.get("/")
def root():
    return {"message" : "Welcome to RailBay"}
