import time
import random

# Assume these constants are defined elsewhere in your code:
NUM_DOORS = 4
STATION_DISTANCE = 300
EMERGENCY_DECEL = 24.0
DECELERATION = 12.0
ACCELERATION = 6.0
EMERGENCY_DECEL = 24.0

class Train:
    def __init__(self):
        self.speed = 0.0
        self.target_speed = 0.0
        self.brakes_applied = False
        self.emergency_stop = False
        self.doors = [False] * NUM_DOORS  
        self.passengers = 0
        self.distance_traveled = 0  
        self.at_station = False
        self.station_stop_time = None  # Timestamp when the train first came to a near-stop at a station
        self.DWELL_TIME = 2  # seconds to consider the train "at station"

    def update(self, delta_time):
        # Update speed based on control flags.
        wind_effect = random.uniform(-0.01, 0.01)
        if self.emergency_stop:
            self.speed = max(0, self.speed - 24.0 * delta_time)
            self.target_speed = 0
        elif self.brakes_applied:
            self.speed = max(0, self.speed - 12.0 * delta_time)
        elif self.speed < self.target_speed:
            self.speed = min(self.target_speed, self.speed + 6.0 * delta_time + wind_effect * delta_time)
        else:
            self.speed = max(0, self.speed - 0.01 * delta_time + wind_effect * delta_time)
            
        # Update distance traveled.
        distance_change = self.speed * delta_time
        self.distance_traveled += distance_change

        # Determine current position on the loop.
        # The train runs on a circular track with three stations.
        total_loop = STATION_DISTANCE * 3
        current_pos = self.distance_traveled % total_loop
        # List of station positions.
        station_positions = [0, STATION_DISTANCE, STATION_DISTANCE * 2]

        # Find the closest station using a simple distance measure.
        nearest_station = None
        nearest_distance = float('inf')
        for s in station_positions:
            # Account for wrap-around if needed.
            d = abs(current_pos - s)
            if d > total_loop / 2:
                d = total_loop - d
            if d < nearest_distance:
                nearest_distance = d
                nearest_station = s

        # Station detection:
        # Only flag as "at_station" if within 5 pixels and nearly stopped.
        if nearest_distance < 5 and self.speed < 0.1:
            if self.station_stop_time is None:
                self.station_stop_time = time.time()  # Record the time when station was reached
            # Keep at_station True if we've been dwelling for at least DWELL_TIME.
            if time.time() - self.station_stop_time >= self.DWELL_TIME:
                self.at_station = True
        else:
            # If the train is moving or it has left the immediate station zone, clear the flag.
            # Using a 10 pixel threshold to clear the flag.
            if nearest_distance > 10:
                self.at_station = False
                self.station_stop_time = None

# For testing purposes, here's a simple loop that simulates updating the train:
if __name__ == "__main__":
    train = Train()
    train.target_speed = 22.22  # Some cruising speed
    last_time = time.time()
    while True:
        now = time.time()
        dt = now - last_time
        last_time = now
        train.update(dt)
        print(f"Distance: {train.distance_traveled:.2f}, Speed: {train.speed:.2f}, At Station: {train.at_station}")
        time.sleep(0.1)
