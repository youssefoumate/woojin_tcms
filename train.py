# train.py
"""Train module managing the state and behavior of the train."""

import random
import time
from constants import CRUISING_SPEED, NUM_DOORS, MAX_PASSENGERS, STATION_DISTANCE

class Train:
    """Represents the train with its state and movement logic."""
    
    def __init__(self):
        self.speed = 0.0
        self.target_speed = 0.0
        self.brakes_applied = False
        self.emergency_stop = False
        self.doors = [False] * NUM_DOORS
        self.passengers = 0
        self.distance_traveled = 0
        self.at_station = False
        self.station_stop_time = None
        self.DWELL_TIME = 1  # Seconds to dwell at a station
        self.leaving_station = False
        self.leaving_station_time = None
        self.LEAVING_COOLDOWN = 5.0  # Seconds before re-detecting a station

    def update(self, delta_time):
        """Updates the train's state based on control inputs and physics."""
        wind_effect = random.uniform(-0.01, 0.01)
        if self.emergency_stop:
            self.speed = max(0, self.speed - 24.0 * delta_time)
            self.target_speed = 0
            if self.speed == 0.0:
                self.emergency_stop = False
        elif self.brakes_applied:
            self.speed = max(0, self.speed - 12.0 * delta_time)
        elif self.at_station:
            self.speed = 0
            self.target_speed = 0
        elif self.speed < self.target_speed:
            self.speed = min(self.target_speed, self.speed + 6.0 * delta_time + wind_effect * delta_time)
        else:
            self.speed = max(0, self.speed - 0.01 * delta_time + wind_effect * delta_time)

        self.distance_traveled += self.speed * delta_time
        total_loop = STATION_DISTANCE * 3
        current_pos = self.distance_traveled % total_loop
        station_positions = [0, STATION_DISTANCE, STATION_DISTANCE * 2]

        nearest_station = min(station_positions, key=lambda s: min(abs(current_pos - s), total_loop - abs(current_pos - s)))
        nearest_distance = min(abs(current_pos - nearest_station), total_loop - abs(current_pos - nearest_station))

        if self.leaving_station and time.time() - self.leaving_station_time >= self.LEAVING_COOLDOWN:
            self.leaving_station = False
            print("[Train] No longer in leaving_station state")

        if self.at_station and self.speed > 0.1:
            self.at_station = False
            self.leaving_station = True
            self.leaving_station_time = time.time()
            self.station_stop_time = None
            print("[Train] Leaving station, setting cooldown")

        if nearest_distance < 50 and self.speed < 0.1 and not self.leaving_station:
            if self.station_stop_time is None:
                self.station_stop_time = time.time()
            if time.time() - self.station_stop_time >= self.DWELL_TIME:
                self.at_station = True
                self.target_speed = 0
        elif nearest_distance > 50 and not self.leaving_station:
            self.at_station = False
            self.station_stop_time = None

    def board_passengers(self):
        """Increases passenger count when at a station."""
        self.passengers += 1
        if self.passengers > MAX_PASSENGERS:
            self.passengers = MAX_PASSENGERS