from fastapi import HTTPException,Depends,APIRouter,status,Response
from datetime import datetime
from sqlalchemy.orm import Session, aliased
import uuid
from typing import List
from .. import schemas,models
from ..database import get_db
from ..oauth2 import get_current_user
from ..mockGateway import MockRazorpayClient
import os


router = APIRouter(prefix="/bookings",tags=["Bookings"])


def generate_pnr():
    return str(uuid.uuid4()).split("-")[0].upper()

# Initialize Payment Client
KEY_ID = os.getenv("KEY_ID", "1234")
KEY_SECRET = os.getenv("KEY_SECRET", "5678")
payment_client = MockRazorpayClient(auth=(KEY_ID, KEY_SECRET))


#------------------------------------------------------BOOK TICKET ROUTE-----------------------------------------------------#

@router.post("/",status_code=status.HTTP_201_CREATED,response_model=schemas.TicketResponse)
def book_ticket(request : schemas.BookingCreate, db:Session = Depends(get_db), current_user = Depends(get_current_user)):
    
    try:
        trip_date_obj = datetime.strptime(request.trip_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    print("checkpoint 1")
    
    #1 find the route
    route_id = db.query(models.TrainDailyRoute.route_id).filter(
        models.TrainDailyRoute.train_id == request.train_id
        ,models.TrainDailyRoute.date == trip_date_obj).scalar()
    
    if not route_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Train {request.train_id} is not schduled for {request.trip_date}")
    
    print("checkpoint 2")
    
    source_seq = db.query(models.RouteStation.sequence_number).join(
        models.Station, models.Station.id == models.RouteStation.station_id
    ).filter(
        models.RouteStation.route_id == route_id,
        models.Station.code == request.source_station_code
    ).scalar()
    
    
    dest_seq = db.query(models.RouteStation.sequence_number).join(
        models.Station, models.Station.id == models.RouteStation.station_id
    ).filter(
        models.RouteStation.route_id == route_id,
        models.Station.code == request.dest_station_code
    ).scalar()
    
    print("checkpoint 3")
    
    if source_seq is None or dest_seq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Station not on route")
    
    if source_seq >= dest_seq:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid direction")
    
    
    
    print("checkpoint 4")
    
    # 3. FIND AVAILABLE SEAT (The "Normal" Booking Logic)
    # Logic: Get ALL seats, subtract seats that are BOOKED for this segment.
    
    # A. Find seats that clash
    clashing_seat_ids = db.query(models.Booking.seat_id).join(
        models.Ticket,models.Booking.pnr == models.Ticket.pnr).filter(
        models.Ticket.trip_date == trip_date_obj,
        models.Ticket.status.in_(["CONFIRMED","BOOKED"]),  # Ignore Cancelled, Cancelled seats can be assigned to user
        models.Booking.from_seq < dest_seq,
        models.Booking.to_seq > source_seq
    )
      
    print("checkpoint 5")  
    
    # B. Find an available seat
    available_seat = db.query(models.Seat).filter(
        models.Seat.train_id == request.train_id,
        ~models.Seat.id.in_(clashing_seat_ids)     #<-----here # type: ignore
    ).with_for_update(skip_locked=True).first()    #<--- Lock the row to prevent race conditions
    
    
    print("checkpoint 6")
    
    #4. assigning seat or WL
    final_status = "CONFIRMED" if available_seat else "WL"
    initial_status = "PAYMENT_PENDING" # <--- The new default
    
    pnr = generate_pnr()
    booking_status = "WL"    #by default waitlist
    assigned_seat_id = None

    assigned_seat_id = available_seat.id if available_seat else None
    seat_number_str = available_seat.number if available_seat else None
        
    src_station_id = db.query(models.Station.id).filter(models.Station.code == request.source_station_code).scalar()
    dest_station_id = db.query(models.Station.id).filter(models.Station.code == request.dest_station_code).scalar()
        
    print("checkpoint 7")
    
    # A. Create Ticket Entry (The Header)
    new_ticket = models.Ticket(
        pnr = pnr,
        user_id = current_user.id,
        train_id = request.train_id,
        source_station_id = src_station_id,
        destination_station_id = dest_station_id,
        trip_date = trip_date_obj,
        total_fare = 500.00,  # Hardcoded for simplicity
        status = initial_status  # PAYMENT_PENDING
    )
    
    db.add(new_ticket)
    db.commit() # Commit ticket to generate PNR relationship
    db.refresh(new_ticket)
    
    #B. Create Booking Entry
    new_booking = models.Booking(
        pnr = pnr,
        seat_id = assigned_seat_id,
        from_seq = source_seq,
        to_seq = dest_seq,
        status = booking_status
    )
    
    db.add(new_booking)
    db.flush() 
    db.refresh(new_booking)
    
    
    
    # --- 4. Create Payment Order ---
    amount_paise = 500 * 100
    order_data = {"amount": amount_paise, "currency": "INR", "payment_capture": 1}
    
    try:
        gateway_order = payment_client.order.create(data=order_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment Gateway Failed")

    # --- 5. Create Transaction Record ---
    new_transaction = models.Transactions(
        user_id=current_user.id,
        booking_id=new_booking.id,
        ticket_pnr=pnr, # Link to the ticket
        gateway_order_id=gateway_order['id'],
        amount=amount_paise,
        status="CREATED"
    )
    db.add(new_transaction)
    
    db.commit()
    db.refresh(new_ticket)
    
    return {
        "pnr": pnr,
        "status": initial_status,    # PAYMENT_PENDING
        "seat_number": None, # Don't show seat until paid!
        "total_fare": 500.0,
        "message": "Payment Pending",
        "created_at": new_ticket.created_at,
        "payment_order_id": gateway_order['id'] # <--- Frontend needs this --> then payment will be made --> frontend will get payment id and signature and call verify-payment
    }                                                  #verify-payment endpoint will validate the signature and then make the ticket CONFIRMED/WL
    
    
    
    
    

#------------------------------------------------------CHECK AVAILABILITY ROUTE-----------------------------------------------------#
    
@router.get("/check-availability",status_code=status.HTTP_200_OK,response_model=schemas.AvailabilityResponse)
def check_availability(request : schemas.AvailabilityCheck, db:Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    
    try:
        trip_date_obj = datetime.strptime(request.trip_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")
    
    
    #1 find the route
    route_id = db.query(models.TrainDailyRoute.route_id).filter(
        models.TrainDailyRoute.train_id == request.train_id
        ,models.TrainDailyRoute.date == trip_date_obj).scalar()
    
    if not route_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Train {request.train_id} is not schduled for {request.trip_date}")
    
    
    
    source_seq = db.query(models.RouteStation.sequence_number).join(
        models.Station, models.Station.id == models.RouteStation.station_id
    ).filter(
        models.RouteStation.route_id == route_id,
        models.Station.code == request.source_station_code
    ).scalar()
    
    
    dest_seq = db.query(models.RouteStation.sequence_number).join(
        models.Station, models.Station.id == models.RouteStation.station_id
    ).filter(
        models.RouteStation.route_id == route_id,
        models.Station.code == request.dest_station_code
    ).scalar()
    
    
    
    if source_seq is None or dest_seq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Station not on route")
    
    if source_seq >= dest_seq:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid direction")
    
    
    
    
    
    # 2. FIND AVAILABLE SEAT (The "Normal" Booking Logic)
    # Logic: Get ALL seats, subtract seats that are BOOKED for this segment.
    
    # A. Find seats that clash
    occupied_count = db.query(models.Booking.seat_id).join(
        models.Ticket,models.Booking.pnr == models.Ticket.pnr).filter(
        models.Ticket.trip_date == trip_date_obj,
        models.Ticket.status.in_(["CONFIRMED","BOOKED"]),  # Ignore Cancelled, Cancelled seats can be assigned to user
        models.Booking.from_seq < dest_seq,
        models.Booking.to_seq > source_seq
    ).count()


    total_seats = db.query(models.Train.total_seats).filter(
        models.Train.id == request.train_id
    ).scalar()
    
    if not total_seats:
        total_seats = 0

    available_seat_count = total_seats - occupied_count
    if available_seat_count < 0:
        available_seat_count = 0
    
    return {
        "train_id" : request.train_id,
        "trip_date" : request.trip_date,
        "available_seats" : available_seat_count,
        "total_seats" : total_seats,
        "status" : f"AVAILABLE {available_seat_count}" if available_seat_count > 0 else "WAITLIST"
    }
    
    
    
    
    
    
#Gemini - Copied
#------------------------------------------------------GET MY BOOKINGS ROUTE-----------------------------------------------------#
@router.get("/me", status_code=status.HTTP_200_OK, response_model=List[schemas.TicketDetails])
def get_my_bookings(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    today = datetime.now().date()
    
    # Create aliases so we can join 'stations' table twice
    SourceStation = aliased(models.Station)
    DestStation = aliased(models.Station)
    
    results = db.query(
        models.Ticket,
        models.Seat.number,
        SourceStation.name.label("src_name"),
        DestStation.name.label("dest_name")
    ).join(
        models.Booking, models.Ticket.pnr == models.Booking.pnr
    ).outerjoin(  # <--- OUTER JOIN (Critical for showing Waitlist tickets)
        models.Seat, models.Booking.seat_id == models.Seat.id
    ).join(
        SourceStation, models.Ticket.source_station_id == SourceStation.id
    ).join(
        DestStation, models.Ticket.destination_station_id == DestStation.id
    ).filter(
        models.Ticket.user_id == current_user.id,
        models.Ticket.trip_date >= today
    ).order_by(
        models.Ticket.trip_date.asc()
    ).all()
    
    # Manually map the results to the Schema
    response = []
    for ticket, seat_num, src_name, dest_name in results:
        response.append({
            "pnr": ticket.pnr,
            "status": ticket.status,
            "seat_number": seat_num, # Will be None if WL
            "source_station": src_name, # Now we have the actual name
            "dest_station": dest_name,
            "total_fare": ticket.total_fare,
            "trip_date": ticket.trip_date
        })
        
    return response





#------------------------------------------------------CANCEL Ticket-----------------------------------------------------#

@router.delete("/{pnr}",status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(pnr: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    
    ticket_to_cancel = db.query(models.Ticket).filter(
        models.Ticket.pnr == pnr,
        models.Ticket.user_id == current_user.id
    ).first()
    
    if not ticket_to_cancel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Ticket not found")
    
    if ticket_to_cancel.status == "CANCELLED": # type: ignore
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Ticket already cancelled")
    
    
    booking_to_cancel = db.query(models.Booking).filter(
        models.Booking.pnr == pnr
    ).first()
    
    freed_seat_id = booking_to_cancel.seat_id # type: ignore
    vacated_from_seq = booking_to_cancel.from_seq # type: ignore
    vacated_to_seq = booking_to_cancel.to_seq # type: ignore
    trip_date = ticket_to_cancel.trip_date
    train_id = ticket_to_cancel.train_id
    
    
    #Perform Cancellation
    ticket_to_cancel.status = "CANCELLED" # type: ignore
    booking_to_cancel.status = "CANCELLED" # type: ignore
    booking_to_cancel.seat_id = None # type: ignore
    
    db.commit()
    
    #------------------------------------------------
    # AUTO PROMOTION
    #-----------------------------------------------
    
    wl_candidates = db.query(models.Booking).join(models.Ticket,models.Booking.pnr == models.Ticket.pnr).filter(
        models.Ticket.train_id == train_id,      #same train
        models.Ticket.trip_date == trip_date,    #same date
        models.Ticket.status == "WL"             #waitlist
    ).order_by(models.Ticket.created_at.asc()).all()
    
    #we did join booking with tickets (why not onlt ticket because we need from_seq and to_seq which are present in Bookings)
    
    
    if freed_seat_id: # type: ignore
        for candidate in wl_candidates:
            # CHECK FOR COLLISIONS on the specific Freed Seat
            # We look for any CONFIRMED booking on 'freed_seat_id' that overlaps with 'candidate'
            collision = db.query(models.Booking).join(
                models.Ticket, models.Booking.pnr == models.Ticket.pnr
            ).filter(
                models.Booking.seat_id == freed_seat_id, # Check ONLY this seat
                models.Ticket.status == "CONFIRMED",     # Only active bookings
                models.Ticket.trip_date == trip_date,    # Same day
                # Overlap Formula: (StartA < EndB) and (EndA > StartB)
                models.Booking.from_seq < candidate.to_seq,
                models.Booking.to_seq > candidate.from_seq
            ).first()      #if one collision is there then move on, so no need to fetch all of them, one is sufficient
            
            
            if not collision:
                # NO COLLISION! The seat is free for this candidate's entire journey.
                print(f"🎉 Promoting PNR {candidate.pnr} to Seat {freed_seat_id}")

                #assign the seat
                candidate.seat_id = freed_seat_id
                candidate.status = "CONFIRMED" # type: ignore
                
                #also update ticket status
                candidate.ticket.status = "CONFIRMED"
                
                db.commit()
                
                break  #only promote one passenger at a time
            
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)