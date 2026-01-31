from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session, aliased
from typing import List
from .. import models,schemas,oauth2
from ..database import get_db
from datetime import datetime, date, timedelta

router = APIRouter(prefix="/trains",tags=["Trains"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[schemas.TrainResponse])
def search_trains(search_info: schemas.SearchInfo, db:Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    
    # 1. Get Station IDs for the codes (e.g., "NDLS", "HWH")
    source_station = db.query(models.Station).filter(models.Station.code == search_info.source).first()
    dest_station = db.query(models.Station).filter(models.Station.code == search_info.destination).first()
    
    if not source_station or not dest_station:
        raise HTTPException(status.HTTP_404_NOT_FOUND,detail="One or more stations not found")
    
    
    # 2. Advanced Query: Find Routes connecting A -> B with valid direction
    # We will join route with RS1(copy of route_stations) and RS2(copy of route_stations) 
    # --> by this we will be able to obtain a single row where route id, source_id , destinaion_id matches 
    # that row if exists means route_id is the route.
    
    RS1 = aliased(models.RouteStation)
    RS2 = aliased(models.RouteStation)
    
    valid_routes = db.query(models.Route).join(
        RS1, RS1.route_id == models.Route.id).join(
            RS2, RS2.route_id == models.Route.id).filter(
                RS1.station_id == source_station.id,
                RS2.station_id == dest_station.id,
                RS1.sequence_number < RS2.sequence_number
            ).all()
    
    if not valid_routes:
        return []      #if no valid_routes present---> no trains to show ---> return empty list
    
    valid_routes_ids = [r.id for r in valid_routes]
    
    
    
    # 3. Find Trains that run on these specific routes
    trains_and_times = db.query(models.Train, models.TrainDailyRoute.start_time, models.TrainDailyRoute.date).join(
        models.TrainDailyRoute, models.TrainDailyRoute.train_id ==models.Train.id).filter(
            models.TrainDailyRoute.route_id.in_(valid_routes_ids)
        ).all()     #list of tuples (TrainObj, start_time)
    
    
    #4 . Prepare Response
    response = []
    for train, start_time, train_date in trains_and_times:
        response.append({
            "id": train.id,
            "number": train.number,
            "name": train.name,
            "total_seats": train.total_seats,
            "start_time": start_time,           # <--- Injecting the time here
            "date" : train_date
        })
        
    #Note: Filter on the basis of day still not implemented!
    return response




@router.get("/running/{train_id}",status_code=status.HTTP_200_OK, response_model=List[schemas.TrainPath])
def getTrainRoute(train_id: int, trip_date: str, db : Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    
    try:
        trip_date_obj = datetime.strptime(trip_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    #1 Find the Route id
    train_details = db.query(models.TrainDailyRoute.route_id,models.TrainDailyRoute.start_time,models.Train.average_speed).join(
        models.Train, models.TrainDailyRoute.train_id == models.Train.id).filter(
        models.TrainDailyRoute.train_id == train_id,
        models.TrainDailyRoute.date ==  trip_date_obj
    ).first()
        
    if not train_details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Train {train_id} does not run on {trip_date}")
    
    # unpack the train details
    route_id, start_time, average_speed = train_details
    
    if not average_speed:
        average_speed = 60
    
    #2 Join Query
    stations = db.query(models.Station, models.RouteStation.distance_from_start).join(
        models.RouteStation, models.Station.id == models.RouteStation.station_id
    ).filter(
        models.RouteStation.route_id == route_id
    ).order_by(
        models.RouteStation.sequence_number     #<-----station are in order
    ).all()
    
    
    #3 we will return list of stations with rime of arrival/departure later
    response_stations = []
    
    # We need a dummy date (today) to add hours to a "Time" object
    dummy_date = date.today()
    train_start_datetime = datetime.combine(dummy_date, start_time)
    
    for station, distance_from_start in stations:
        travel_hours = distance_from_start / average_speed
        arrival_datetime = train_start_datetime + timedelta(hours=travel_hours)
        
        response_stations.append({
            "id": station.id,
            "station_name" : station.name,
            "code": station.code,
            "city": station.city,
            "distance_from_start": distance_from_start,
            "arrival_time": arrival_datetime.time()     # Extract just the time
        })
    
    return response_stations
    
    
    