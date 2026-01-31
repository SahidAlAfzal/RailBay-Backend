from app.database import SessionLocal, engine
from app import models
from datetime import date, timedelta, time
import random

# Initialize DB Session
db = SessionLocal()

def seed_data():
    try:
        # --- 1. CLEAN SLATE (Delete in correct order) ---
        # ⚠️ CRITICAL: Child tables must be deleted before Parent tables
        print("🧹 Clearing old data...")
        
        # 1. Level 3: Transactions (Depends on Users, Bookings, Tickets)
        db.query(models.Transactions).delete()
        
        # 2. Level 2: Bookings (Depends on Tickets, Seats)
        db.query(models.Booking).delete()
        
        # 3. Level 2: Tickets (Depends on Users, Trains, Stations)
        db.query(models.Ticket).delete()
        
        # 4. Level 2: Seats (Depends on Trains)
        db.query(models.Seat).delete()
        
        # 5. Level 2: Schedules (Depends on Trains, Routes)
        db.query(models.TrainDailyRoute).delete()
        
        # 6. Level 2: Route Stations (Depends on Routes, Stations)
        db.query(models.RouteStation).delete()
        
        # 7. Level 1: Routes
        db.query(models.Route).delete()
        
        # 8. Level 1: Trains
        db.query(models.Train).delete()
        
        # 9. Level 1: Stations
        db.query(models.Station).delete()
        
        # 10. Level 0: Users (Optional: Keep if you want to preserve logins)
        # db.query(models.User).delete() 
        
        db.commit()
        print("✨ Database clean.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during cleanup: {e}")
        return

    print("🌱 Planting new seeds...")

    # --- 2. CREATE STATIONS ---
    # We'll create a nice corridor: Delhi -> Kanpur -> Prayagraj -> Patna -> Kolkata
    stations_data = [
        {"code": "NDLS", "name": "New Delhi", "city": "Delhi"},
        {"code": "CNB", "name": "Kanpur Central", "city": "Kanpur"},
        {"code": "PRYJ", "name": "Prayagraj Junction", "city": "Prayagraj"},
        {"code": "PNBE", "name": "Patna Junction", "city": "Patna"},
        {"code": "HWH", "name": "Howrah Junction", "city": "Kolkata"},
        {"code": "BCT", "name": "Mumbai Central", "city": "Mumbai"},
        {"code": "JP", "name": "Jaipur", "city": "Jaipur"},
    ]
    
    stations = {}
    for s_data in stations_data:
        station = models.Station(**s_data)
        db.add(station)
        stations[s_data["code"]] = station
    
    db.commit()
    # Refresh to get IDs
    for code, station in stations.items():
        db.refresh(station)
    print(f"✅ Created {len(stations)} Stations.")

    # --- 3. CREATE ROUTES ---
    # Route A: The East Corridor (Delhi -> Kolkata)
    route_east = models.Route(name="Delhi-Kolkata Main Line", distance=1450)
    # Route B: The West Corridor (Delhi -> Mumbai)
    route_west = models.Route(name="Delhi-Mumbai Capital Line", distance=1380)

    db.add_all([route_east, route_west])
    db.commit()

    # --- 4. MAP STATIONS TO ROUTES ---
    # East Route Stops (0, 440, 630, 1000, 1450 km)
    east_stops = [
        models.RouteStation(route_id=route_east.id, station_id=stations["NDLS"].id, sequence_number=0, distance_from_start=0),
        models.RouteStation(route_id=route_east.id, station_id=stations["CNB"].id, sequence_number=10, distance_from_start=440),
        models.RouteStation(route_id=route_east.id, station_id=stations["PRYJ"].id, sequence_number=20, distance_from_start=630),
        models.RouteStation(route_id=route_east.id, station_id=stations["PNBE"].id, sequence_number=30, distance_from_start=1000),
        models.RouteStation(route_id=route_east.id, station_id=stations["HWH"].id, sequence_number=40, distance_from_start=1450),
    ]

    # West Route Stops (0, 300, 1380 km)
    west_stops = [
        models.RouteStation(route_id=route_west.id, station_id=stations["NDLS"].id, sequence_number=0, distance_from_start=0),
        models.RouteStation(route_id=route_west.id, station_id=stations["JP"].id, sequence_number=10, distance_from_start=300),
        models.RouteStation(route_id=route_west.id, station_id=stations["BCT"].id, sequence_number=20, distance_from_start=1380),
    ]

    db.add_all(east_stops + west_stops)
    db.commit()
    print("✅ Routes Mapped.")

    # --- 5. CREATE TRAINS ---
    trains = [
        models.Train(number="12301", name="Rajdhani Express", total_seats=100, average_speed=80),
        models.Train(number="12951", name="Tejas Express", total_seats=50, average_speed=90),
        models.Train(number="12201", name="Garib Rath", total_seats=120, average_speed=60),
    ]
    db.add_all(trains)
    db.commit()
    for t in trains: db.refresh(t)

    # --- 6. GENERATE SCHEDULES (NEXT 60 DAYS) ---
    today = date.today()
    schedules = []

    print("📅 Generating Schedules...")
    for day_offset in range(60): # Generate for next 2 months
        current_date = today + timedelta(days=day_offset)
        day_name = current_date.strftime("%A")

        # Train 1: Rajdhani (Delhi-Kolkata) runs Mon, Wed, Fri
        if day_name in ["Monday", "Wednesday", "Friday"]:
            schedules.append(models.TrainDailyRoute(
                train_id=trains[0].id, # Rajdhani
                date=current_date,
                route_id=route_east.id,
                start_time=time(16, 30) # 4:30 PM
            ))

        # Train 2: Tejas (Delhi-Mumbai) runs Daily except Sunday
        if day_name != "Sunday":
            schedules.append(models.TrainDailyRoute(
                train_id=trains[1].id, # Tejas
                date=current_date,
                route_id=route_west.id,
                start_time=time(17, 00) # 5:00 PM
            ))

        # Train 3: Garib Rath (Delhi-Kolkata) runs Tue, Thu
        if day_name in ["Tuesday", "Thursday"]:
             schedules.append(models.TrainDailyRoute(
                train_id=trains[2].id, # Garib Rath
                date=current_date,
                route_id=route_east.id,
                start_time=time(10, 00) # 10:00 AM
            ))
            
    db.add_all(schedules)
    db.commit()
    print(f"✅ Scheduled {len(schedules)} train runs for the next 60 days.")

    # --- 7. CREATE SEATS (INVENTORY) ---
    print("💺 Installing Seats...")
    seats = []
    
    # Add seats for all trains
    for train in trains:
        for i in range(1, train.total_seats + 1): # type: ignore
            seats.append(models.Seat(train_id=train.id, number=str(i)))
    
    db.add_all(seats)
    db.commit()
    print(f"✅ Installed {len(seats)} seats across {len(trains)} trains.")

    print("🚀 SYSTEM READY! LIFT OFF!")

if __name__ == "__main__":
    seed_data()