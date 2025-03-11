import pygame
import random
import time

# Initialize Pygame
pygame.init()

# Window settings
WIDTH = 900
HEIGHT = 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TCMS with Train Movement Animation")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (200, 200, 200)
YELLOW = (255, 255, 0)

# Train parameters
CRUISING_SPEED = 80  # km/h
ACCELERATION = 0.1   # km/h per frame
DECELERATION = 0.2   # km/h per frame
EMERGENCY_DECEL = 0.5  # km/h per frame
NUM_DOORS = 4
MAX_PASSENGERS = 200
STATION_DISTANCE = 300  # Pixels between stations

# MVB parameters
TRANSMISSION_TIME = 0.5  # Seconds
SENSOR_INTERVAL = 1.0    # Seconds

# Node positions
NODE_POSITIONS = [100, 200, 300, 400, 500, 600, 700, 800]

# Button definitions
BUTTONS = {
    "Start Moving": pygame.Rect(50, 10, 120, 30),
    "Apply Brakes": pygame.Rect(180, 10, 120, 30),
    "Release Brakes": pygame.Rect(310, 10, 120, 30),
    "Open Doors": pygame.Rect(440, 10, 120, 30),
    "Close Doors": pygame.Rect(570, 10, 120, 30),
    "Emergency Stop": pygame.Rect(700, 10, 120, 30)
}

# Train class
class Train:
    def __init__(self):
        self.speed = 0.0
        self.target_speed = 0.0
        self.brakes_applied = False
        self.emergency_stop = False
        self.doors = [False] * NUM_DOORS  # False: closed, True: open
        self.passengers = 0
        self.distance_traveled = 0  # Pixels
        self.at_station = False

    def update(self, delta_time):
        # Simulate wind resistance
        wind_effect = random.uniform(-0.01, 0.01)
        
        if self.emergency_stop:
            self.speed = max(0, self.speed - EMERGENCY_DECEL)
            self.target_speed = 0
        elif self.brakes_applied:
            self.speed = max(0, self.speed - DECELERATION)
        elif self.speed < self.target_speed:
            self.speed = min(self.target_speed, self.speed + ACCELERATION + wind_effect)
        else:
            self.speed = max(0, self.speed - 0.01 + wind_effect)

        # Update distance traveled
        self.distance_traveled += self.speed * delta_time * 0.5  # Scale for visibility
        self.distance_traveled %= STATION_DISTANCE * 3  # Loop every 3 stations

        # Snapping logic when the train stops
        stopping_points = [0, 220, 525]  # Stopping points for stations 2, 3, 1
        if self.speed == 0:
            for s in stopping_points:
                if abs(self.distance_traveled % 900 - s) < 30:  # Tolerance of 30 units
                    # Snap to the exact stopping point
                    self.distance_traveled = s + (self.distance_traveled // 900) * 900
                    break
        # Check if at station
        self.at_station = any(abs(self.distance_traveled % 900 - s) < 5 for s in stopping_points) and self.speed == 0

    def board_passengers(self):
        if self.at_station and any(self.doors):
            boarding = random.randint(0, 10)
            alighting = random.randint(0, min(10, self.passengers))
            self.passengers = max(0, min(MAX_PASSENGERS, self.passengers + boarding - alighting))

# MVB Bus class
class MVB_Bus:
    def __init__(self):
        self.transmissions = []

    def send_message(self, sender, receiver, message):
        self.transmissions.append({'sender': sender, 'receiver': receiver, 'message': message, 'progress': 0.0})

    def update(self, delta_time):
        for t in self.transmissions[:]:
            t['progress'] += delta_time / TRANSMISSION_TIME
            if t['progress'] >= 1.0:
                t['receiver'].receive_message(t['message'])
                self.transmissions.remove(t)

    def draw(self):
        pygame.draw.line(screen, BLACK, (50, 500), (850, 500), 5)
        font = pygame.font.SysFont(None, 20)
        for t in self.transmissions:
            start_x = NODE_POSITIONS[t['sender'].index]
            end_x = NODE_POSITIONS[t['receiver'].index]
            current_x = start_x + (end_x - start_x) * t['progress']
            pygame.draw.circle(screen, RED, (int(current_x), 500), 5)
            label = font.render(t['message'], True, BLACK)
            screen.blit(label, (current_x - 20, 480))

# Base Node class
class Node:
    def __init__(self, name, index):
        self.name = name
        self.index = index

    def draw(self):
        x = NODE_POSITIONS[self.index]
        pygame.draw.circle(screen, BLUE, (x, 450), 20)
        pygame.draw.line(screen, BLACK, (x, 450), (x, 500), 2)
        font = pygame.font.SysFont(None, 24)
        label = font.render(self.name, True, BLACK)
        screen.blit(label, (x - 40, 420))

# Sensor Node
class SensorNode(Node):
    def __init__(self, name, index, read_state_func, interval=SENSOR_INTERVAL):
        super().__init__(name, index)
        self.read_state_func = read_state_func
        self.interval = interval
        self.last_send_time = 0

    def update(self, current_time, bus, receiver):
        if current_time - self.last_send_time > self.interval:
            bus.send_message(self, receiver, self.read_state_func())
            self.last_send_time = current_time

# Actuator Node
class ActuatorNode(Node):
    def __init__(self, name, index, set_state_func):
        super().__init__(name, index)
        self.set_state_func = set_state_func

    def receive_message(self, message):
        self.set_state_func(message)

# Control Unit Node
class ControlUnitNode(Node):
    def __init__(self, name, index):
        super().__init__(name, index)
        self.current_speed = 0.0
        self.door_states = [False] * NUM_DOORS
        self.brakes_applied = False
        self.emergency_stop = False
        self.passengers = 0
        self.at_station = False
        self.display_message = ""

    def receive_message(self, message):
        if "Speed:" in message:
            self.current_speed = float(message.split(":")[1])
        elif "Door" in message:
            door_num = int(message.split(":")[0][-1])
            self.door_states[door_num] = "Open" in message.split(":")[1]
        elif "Passengers:" in message:
            self.passengers = int(message.split(":")[1])
        elif "Station:" in message:
            self.at_station = "Yes" in message

    def on_button_click(self, button, bus, train):
        if button == "Start Moving":
            if all(not state for state in self.door_states):
                bus.send_message(self, traction_actuator, f"Set Target Speed: {CRUISING_SPEED}")
                self.display_message = "Train starting..."
            else:
                self.display_message = "Cannot start with doors open"
        elif button == "Apply Brakes":
            bus.send_message(self, brake_actuator, "Apply Brakes")
            self.brakes_applied = True
        elif button == "Release Brakes":
            bus.send_message(self, brake_actuator, "Release Brakes")
            self.brakes_applied = False
        elif button == "Open Doors":
            if self.current_speed == 0:
                for i in range(NUM_DOORS):
                    bus.send_message(self, door_actuators[i], f"Open Door{i}")
            else:
                self.display_message = "Cannot open doors while moving"
        elif button == "Close Doors":
            for i in range(NUM_DOORS):
                bus.send_message(self, door_actuators[i], f"Close Door{i}")
        elif button == "Emergency Stop":
            bus.send_message(self, emergency_actuator, "Emergency Stop")
            self.emergency_stop = True

    def draw_interface(self):
        font = pygame.font.SysFont(None, 24)
        for name, rect in BUTTONS.items():
            pygame.draw.rect(screen, GRAY, rect)
            label = font.render(name, True, BLACK)
            screen.blit(label, (rect.x + 10, rect.y + 5))
        status_texts = [
            f"Speed: {self.current_speed:.1f} km/h",
            f"Brakes: {'On' if self.brakes_applied else 'Off'}",
            f"Emergency: {'On' if self.emergency_stop else 'Off'}",
            f"Doors: {sum(self.door_states)} Open, {NUM_DOORS - sum(self.door_states)} Closed",
            f"Passengers: {self.passengers}/{MAX_PASSENGERS}",
            f"At Station: {'Yes' if self.at_station else 'No'}"
        ]
        for i, text in enumerate(status_texts):
            screen.blit(font.render(text, True, BLACK), (50, 50 + i * 30))
        if self.display_message:
            screen.blit(font.render(self.display_message, True, RED), (50, 230))

# Main simulation function
def simulate_tcms():
    global traction_actuator, brake_actuator, emergency_actuator, door_actuators

    train = Train()
    bus = MVB_Bus()

    # Create nodes
    speed_sensor = SensorNode("Speed", 0, lambda: f"Speed: {train.speed:.1f}")
    door_sensors = [SensorNode(f"Door{i}", i+1, lambda i=i: f"Door{i}: {'Open' if train.doors[i] else 'Closed'}") for i in range(NUM_DOORS)]
    passenger_sensor = SensorNode("Pass", 5, lambda: f"Passengers: {train.passengers}")
    station_sensor = SensorNode("Station", 6, lambda: f"Station: {'Yes' if train.at_station else 'No'}")
    traction_actuator = ActuatorNode("Traction", 7, lambda msg: setattr(train, 'target_speed', float(msg.split(":")[1]) if "Speed" in msg else train.target_speed))
    brake_actuator = ActuatorNode("Brake", 3, lambda msg: setattr(train, 'brakes_applied', msg == "Apply Brakes"))
    emergency_actuator = ActuatorNode("Emerg", 4, lambda msg: setattr(train, 'emergency_stop', msg == "Emergency Stop"))
    door_actuators = [ActuatorNode(f"Door{i}A", i+1, lambda msg, i=i: train.doors.__setitem__(i, "Open" in msg)) for i in range(NUM_DOORS)]

    control_unit = ControlUnitNode("Control", 2)
    nodes = [speed_sensor, *door_sensors, passenger_sensor, station_sensor, traction_actuator, brake_actuator, emergency_actuator, *door_actuators, control_unit]

    clock = pygame.time.Clock()
    running = True
    message_timer = 0
    previous_at_station = False

    while running:
        # Inside the main loop, after updating train state (e.g., train.update(delta_time))
        
        if not train.at_station:
            # Define target stopping points (where train_x aligns middle with station)
            stopping_points = [200, 500, 800]  # Adjusted for stations at 300, 600, 0
            d = train.distance_traveled % 900
            distances = [(s - d) % 900 for s in stopping_points]
            distance_to_next_stop = min([dist for dist in distances if dist > 0])

            # Calculate stopping distance based on current speed
            u = train.speed
            s = 0
            speed = u
            while speed > 0:
                speed = max(0, speed - DECELERATION)  # DECELERATION = 0.2 km/h per frame
                s += speed * (1 / 60) * 0.5  # Distance per frame (60 FPS)

            # Apply brakes if within stopping distance
            if distance_to_next_stop <= s and not control_unit.brakes_applied:
                bus.send_message(control_unit, brake_actuator, "Apply Brakes")
                control_unit.brakes_applied = True
                control_unit.display_message = "Automatic braking applied"
        else:
            # Release brakes when stopped at station
            if control_unit.brakes_applied:
                bus.send_message(control_unit, brake_actuator, "Release Brakes")
                control_unit.brakes_applied = False
                control_unit.display_message = "Brakes released at station"
        delta_time = clock.tick(60) / 1000.0  # Seconds
        current_time = pygame.time.get_ticks() / 1000.0

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                for name, rect in BUTTONS.items():
                    if rect.collidepoint(pos):
                        control_unit.on_button_click(name, bus, train)
                        message_timer = current_time + 2  # Show message for 2 seconds

        # Update sensors
        speed_sensor.update(current_time, bus, control_unit)
        for door_sensor in door_sensors:
            door_sensor.update(current_time, bus, control_unit)
        passenger_sensor.update(current_time, bus, control_unit)
        print(train.at_station)
        station_sensor.update(current_time, bus, control_unit)

        # Update MVB bus
        bus.update(delta_time)

        # Update train state
        train.update(delta_time)
        print(f"Speed: {train.speed}, Position: {train.distance_traveled % 900}, At Station: {train.at_station}")
        if train.at_station and not previous_at_station and train.speed < 1:
        # Automatically open doors after stopping at station
            for i in range(NUM_DOORS):
                bus.send_message(control_unit, door_actuators[i], f"Open Door{i}")
            control_unit.display_message = "Doors automatically opening at station"
        if train.at_station:
            train.board_passengers()
        # Update the previous state for the next loop iteration
        previous_at_station = train.at_station

        # Clear display message after timeout
        if current_time > message_timer and control_unit.display_message:
            control_unit.display_message = ""

        # Calculate train's x-position
        train_x = 50 + (train.distance_traveled % 900)

        # Clear screen
        screen.fill(WHITE)

        # Draw track
        pygame.draw.line(screen, BLACK, (0, 600), (900, 600), 5)

        # Draw stations
        for i in range(3):
            station_x = 50 + i * 300
            color = YELLOW if train.at_station and abs(train_x - station_x) < 10 else GRAY
            pygame.draw.rect(screen, color, (station_x - 10, 590, 20, 20))
            font = pygame.font.SysFont(None, 20)
            screen.blit(font.render(f"Station {i+1}", True, BLACK), (station_x - 20, 610))

        # Draw train
        pygame.draw.rect(screen, BLACK, (train_x, 550, 200, 50))

        # Draw doors
        door_positions = [train_x + 20 + i*45 for i in range(4)]
        for i, pos in enumerate(door_positions):
            color = RED if train.doors[i] else GREEN
            pygame.draw.rect(screen, color, (pos, 550, 30, 50))

        # Draw speed label
        speed_label = font.render(f"{train.speed:.1f} km/h", True, BLACK)
        screen.blit(speed_label, (train_x + 50, 520))

        # Draw MVB bus and nodes
        bus.draw()
        for node in nodes:
            node.draw()

        # Draw driver interface
        control_unit.draw_interface()

        # Update display
        pygame.display.flip()

    pygame.quit()

# Run the simulation
if __name__ == "__main__":
    simulate_tcms()
