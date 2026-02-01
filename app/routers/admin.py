from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from ..database import get_db
from ..oauth2 import get_current_admin
from .. import models,schemas
from datetime import date, time


router = APIRouter(prefix="/admin", tags=["admin"])



@router.get("/dashboard")
async def get_admin_dashboard():
    return {"message": "Admin dashboard placeholder"}



@router.post("/create-daily-route",status_code=status.HTTP_201_CREATED,response_model=schemas.DailyRouteResponse)
async def create_daily_route(request: schemas.DailyRouteCreate, db: Session = Depends(get_db), current_admin: models.User = Depends(get_current_admin)):
    if request.date < date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date cannot be in the past")
    
    
    train = db.query(models.Train).filter(models.Train.number == request.train_number).first()
    
    if not train:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Train not found")
    
    route = db.query(models.Route).filter(models.Route.id == request.route_id).first()
    
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    
    schduled_already = db.query(models.TrainDailyRoute).filter(
        models.TrainDailyRoute.train_id == train.id,
        models.TrainDailyRoute.date == request.date
    ).first()
    
    if schduled_already:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Train already scheduled for this date")
    
    new_daily_route = models.TrainDailyRoute(
        train_id = train.id,
        date = request.date,
        route_id = request.route_id,
        start_time = request.start_time
    )
    
    db.add(new_daily_route)
    db.commit()
    db.refresh(new_daily_route)
    
    return new_daily_route