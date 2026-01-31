from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import time, datetime, date


class SearchInfo(BaseModel):
    source: str
    destination: str
    

#------------------------USER------------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    

class UserResponse(BaseModel):
    id: int
    username : str
    email : EmailStr
    
    class Config:                  # Hey, if input is a SQLAlchemy object not dict, read values using attributes.
        from_attributes = True
    
class UserUpdate(BaseModel):
    username : Optional[str] = None
    email : Optional[EmailStr] = None
    password : Optional[str] = None
    
     
#------------------------TRAIN------------------------ 
class TrainResponse(BaseModel):
    id: int
    number: str
    name: str
    total_seats: int
    start_time: time  # to include start_time from TrainDailyRoute when needed
    date : date    #added on 31/01
    
    class Config:
        from_attributes = True
        
        
class TrainPath(BaseModel):
    id: int
    station_name : str
    code: str
    city: str
    distance_from_start:int 
    arrival_time: time

    class Config:
        from_attributes = True
      
      
#------------------------INFRASTRUCTURE------------------------  
class Station(BaseModel):
    id: int
    name: str
    code: str
    city: str
    
    class Config:
        from_attributes = True

    
#------------------------BOOKING------------------------
class BookingCreate(BaseModel):
    train_id : int
    source_station_code : str
    dest_station_code : str
    trip_date : str          # Format "YYYY-MM-DD"

class TicketResponse(BaseModel):
    pnr : str
    status : str
    seat_number : Optional[int] = None    #for WL
    total_fare : float
    message : str
    # NEW FIELD
    created_at: datetime
    payment_order_id: str
    
    class Config:
        from_attributes = True
        
class TicketDetails(BaseModel):
    pnr : str
    status : str
    seat_number : Optional[str] = None    #for WL
    source_station : str
    dest_station : str
    total_fare : float
    trip_date : date
    payment_order_id: Optional[str] = None
    
    class Config:
        from_attributes = True
        
        
class AvailabilityCheck(BaseModel):
    train_id: int
    source_station_code: str
    dest_station_code: str
    trip_date: str # YYYY-MM-DD
    
class AvailabilityResponse(BaseModel):
    train_id: int
    trip_date: str
    available_seats: int
    total_seats: int
    status: str # "AVAILABLE" or "WAITLIST"


#------------------------TOKEN------------------------
    
class Token(BaseModel):
    access_token : str
    token_type : str
    
class TokenData(BaseModel):
    id : int
    
    
    
    
#------------------------TRANSACTION------------------------
class PaymentVerification(BaseModel):
    gateway_order_id: str
    gateway_payment_id :str
    gateway_signature : str
    
class PaymentVerificationResponse(BaseModel):
    status: str
    message: str
    
class OrderCreate(BaseModel):
    amount:int
    
class OrderResponse(BaseModel):
    id: str
    amount : int
    currency : str