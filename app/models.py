from sqlalchemy import Column, Integer, String, ForeignKey,Date, Numeric, Time, UniqueConstraint, CheckConstraint, TIMESTAMP
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
from sqlalchemy.sql import func # <--- Import this for server-side time

# --- LAYER 1: INFRASTRUCTURE ---
class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key = True, index = True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    city = Column(String)


class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String)
    distance = Column(Integer)
    
    stations = relationship("RouteStation", back_populates="route")
    

class RouteStation(Base):
    __tablename__ = "route_stations"
    id = Column(Integer,primary_key=True,index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    station_id = Column(Integer, ForeignKey("stations.id"))
    sequence_number = Column(Integer)
    distance_from_start = Column(Integer)
    
    route = relationship("Route", back_populates="stations")
    station = relationship("Station")
 
 
 
 
# --- LAYER 2: ASSETS ---   
class Train(Base):
    __tablename__ = "trains"
    id = Column(Integer,primary_key=True,index=True)
    number = Column(String,unique=True,index=True)
    name = Column(String)
    total_seats = Column(Integer,default=50)
    average_speed = Column(Integer, default=60)   #in km/h
    
    schedules = relationship("TrainDailyRoute", back_populates="train")
    seats = relationship("Seat", back_populates="train")
    

class TrainDailyRoute(Base):
    __tablename__ = "train_daily_routes"
    id = Column(Integer,primary_key=True,index=True)
    train_id =  Column(Integer,ForeignKey("trains.id"))
    date = Column(Date)
    route_id = Column(Integer,ForeignKey("routes.id"))
    start_time = Column(Time)
    
    train = relationship("Train", back_populates="schedules")
    route = relationship("Route")
    
class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"))
    number = Column(String)
    
    train = relationship("Train", back_populates="seats")
    __table_args__ = (UniqueConstraint('train_id', 'number', name='seats_train_id_number_key'),)
    
    

 
# --- LAYER 3: TRANSACTIONS ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index= True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)


class Ticket(Base):
    __tablename__ = "tickets"
    pnr = Column(String, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id"))
    train_id = Column(Integer, ForeignKey("trains.id"))
    source_station_id = Column(Integer,ForeignKey("stations.id"))
    destination_station_id = Column(Integer,ForeignKey("stations.id"))
    trip_date = Column(Date)
    total_fare = Column(Numeric(10,2))
    status = Column(String, default="CONFIRMED")
    created_at = Column(TIMESTAMP(timezone=True),server_default=func.now())
    
    bookings = relationship("Booking", back_populates="ticket")
    train = relationship("Train")
    
    
class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index= True)
    pnr = Column(String, ForeignKey("tickets.pnr"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    from_seq = Column(Integer)
    to_seq = Column(Integer)
    status = Column(String, default='BOOKED')
    
    
    ticket = relationship("Ticket", back_populates="bookings")
    seat = relationship("Seat")
    
    __table_args__ = (CheckConstraint('from_seq < to_seq', name='bookings_check'),)


class Transactions(Base):
    __tablename__ = "transactions";
    id = Column(Integer,primary_key=True,index = True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    gateway_order_id = Column(String, unique=True, index=True)
    gateway_payment_id = Column(String, unique=True, nullable=True) #nullable until payment is completed
    gateway_signature = Column(String, nullable=True)       #nullable until payment is completed
    amount = Column(Integer) #in paise
    
    # Status: CREATED -> SUCCESS / FAILED
    status = Column(String, default="CREATED")
    created_at = Column(TIMESTAMP(timezone=True),server_default=func.now())
    
    ticket_pnr = Column(String, ForeignKey("tickets.pnr"), nullable=True) #so can do payment for single pnr/ticket at a time
    
    user = relationship("User")
    ticket = relationship("Ticket")