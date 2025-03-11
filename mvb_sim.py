import pygame
import random
import time

# Initialize Pygame
pygame.init()

# Window settings – increased size for more space between nodes
WIDTH = 1200
HEIGHT = 800
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
PURPLE = (128, 0, 128)  # Color for control node

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
        self.distance_traveled += self.speed * delta_time * 0.5  # Scale for visibility
        self.distance_traveled %= STATION_DISTANCE * 3  # Loop every 3 stations

        stopping_points = [0, 220, 525]
        if self.speed == 0:
            for s in stopping_points:
                if abs(self.distance_traveled % 900 - s) < 30:
                    self.distance_traveled = s + (self.distance_traveled // 900) * 900
                    break
        self.at_station = any(abs(self.distance_traveled % 900 - s) < 5 for s in stopping_points) and self.speed == 0

    def board_passengers(self):
        if self.at_station and any(self.doors):
            boarding = random.randint(0, 10)
            alighting = random.randint(0, min(10, self.passengers))
            self.passengers = max(0, min(MAX_PASSENGERS, self.passengers + boarding - alighting))

# MVB Bus class – updated to use node.x for transmissions
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
        # Draw bus line along the bottom of the nodes
        bus_start = 50
        bus_end = WIDTH - 50
        bus_y = 500
        pygame.draw.line(screen, BLACK, (bus_start, bus_y), (bus_end, bus_y), 5)
        font = pygame.font.SysFont(None, 20)
        for t in self.transmissions:
            start_x = t['sender'].x
            end_x = t['receiver'].x
            current_x = start_x + (end_x - start_x) * t['progress']
            pygame.draw.circle(screen, RED, (int(current_x), bus_y), 5)
            label = font.render(t['message'], True, BLACK)
            screen.blit(label, (current_x - 20, bus_y - 20))

# Base Node class – now each node gets its own x coordinate so it touches the bus
class Node:
    def __init__(self, name):
        self.name = name
        self.x = 0  # Will be assigned later

    def draw(self):
        # Nodes are drawn with their bottom touching the bus line at y=500
        node_y = 450
        pygame.draw.circle(screen, BLUE, (int(self.x), node_y), 20)
        pygame.draw.line(screen, BLACK, (int(self.x), node_y), (int(self.x), node_y + 50), 2)
        font = pygame.font.SysFont(None, 24)
        screen.blit(font.render(self.name, True, BLACK), (int(self.x) - 40, node_y - 30))

# Sensor Node (inherits from Node)
class SensorNode(Node):
    def __init__(self, name, read_state_func, interval=SENSOR_INTERVAL):
        super().__init__(name)
        self.read_state_func = read_state_func
        self.interval = interval
        self.last_send_time = 0

    def update(self, current_time, bus, receiver):
        if current_time - self.last_send_time > self.interval:
            bus.send_message(self, receiver, self.read_state_func())
            self.last_send_time = current_time

# Actuator Node (inherits from Node)
class ActuatorNode(Node):
    def __init__(self, name, set_state_func):
        super().__init__(name)
        self.set_state_func = set_state_func

    def receive_message(self, message):
        self.set_state_func(message)

# Control Unit Node (inherits from Node) with different drawing color
class ControlUnitNode(Node):
    def __init__(self, name):
        super().__init__(name)
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

    def draw(self):
        # Draw the control node with a different color (purple) 
        node_y = 450
        pygame.draw.circle(screen, PURPLE, (int(self.x), node_y), 20)
        pygame.draw.line(screen, BLACK, (int(self.x), node_y), (int(self.x), node_y + 50), 2)
        font = pygame.font.SysFont(None, 24)
        screen.blit(font.render(self.name, True, BLACK), (int(self.x) - 40, node_y - 30))

# Main simulation function
def simulate_tcms():
    global traction_actuator, brake_actuator, emergency_actuator, door_actuators

    train = Train()
    bus = MVB_Bus()

    # Create nodes
    speed_sensor = SensorNode("Speed", lambda: f"Speed: {train.speed:.1f}")
    door_sensors = [SensorNode(f"DoorS{i}", lambda i=i: f"Door{i}: {'Open' if train.doors[i] else 'Closed'}") for i in range(NUM_DOORS)]
    passenger_sensor = SensorNode("Pass", lambda: f"Passengers: {train.passengers}")
    station_sensor = SensorNode("Station", lambda: f"Station: {'Yes' if train.at_station else 'No'}")
    traction_actuator = ActuatorNode("Traction", lambda msg: setattr(train, 'target_speed', float(msg.split(":")[1]) if "Speed" in msg else train.target_speed))
    brake_actuator = ActuatorNode("Brake", lambda msg: setattr(train, 'brakes_applied', msg == "Apply Brakes"))
    emergency_actuator = ActuatorNode("Emerg", lambda msg: setattr(train, 'emergency_stop', msg == "Emergency Stop"))
    door_actuators = [ActuatorNode(f"DoorA{i}", lambda msg, i=i: train.doors.__setitem__(i, "Open" in msg)) for i in range(NUM_DOORS)]
    control_unit = ControlUnitNode("Control")

    # Build the list of nodes in the order they will appear on the bus.
    nodes = [speed_sensor] + door_sensors + [passenger_sensor, station_sensor, traction_actuator, brake_actuator, emergency_actuator] + door_actuators + [control_unit]

    # Assign unique x positions along the bus line with extra space between nodes.
    bus_start = 50
    bus_end = WIDTH - 50  # 1150 in a 1200-wide window
    spacing = (bus_end - bus_start) / (len(nodes) - 1)
    for i, node in enumerate(nodes):
        node.x = bus_start + i * spacing

    clock = pygame.time.Clock()
    running = True
    message_timer = 0
    previous_at_station = False
    font = pygame.font.SysFont(None, 24)

    while running:
        if not train.at_station:
            stopping_points = [200, 500, 800]
            d = train.distance_traveled % 900
            distances = [(s - d) % 900 for s in stopping_points]
            distance_to_next_stop = min([dist for dist in distances if dist > 0])
            u = train.speed
            s = 0
            speed = u
            while speed > 0:
                speed = max(0, speed - DECELERATION)
                s += speed * (1 / 60) * 0.5
            if distance_to_next_stop <= s and not control_unit.brakes_applied:
                bus.send_message(control_unit, brake_actuator, "Apply Brakes")
                control_unit.brakes_applied = True
                control_unit.display_message = "Automatic braking applied"
        else:
            if control_unit.brakes_applied:
                bus.send_message(control_unit, brake_actuator, "Release Brakes")
                control_unit.brakes_applied = False
                control_unit.display_message = "Brakes released at station"

        delta_time = clock.tick(60) / 1000.0
        current_time = pygame.time.get_ticks() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                for name, rect in BUTTONS.items():
                    if rect.collidepoint(pos):
                        control_unit.on_button_click(name, bus, train)
                        message_timer = current_time + 2

        # Update sensors
        speed_sensor.update(current_time, bus, control_unit)
        for sensor in door_sensors:
            sensor.update(current_time, bus, control_unit)
        passenger_sensor.update(current_time, bus, control_unit)
        station_sensor.update(current_time, bus, control_unit)

        bus.update(delta_time)
        train.update(delta_time)
        if train.at_station and not previous_at_station and train.speed < 1:
            for i in range(NUM_DOORS):
                bus.send_message(control_unit, door_actuators[i], f"Open Door{i}")
            control_unit.display_message = "Doors automatically opening at station"
        if train.at_station:
            train.board_passengers()
        previous_at_station = train.at_station

        if current_time > message_timer and control_unit.display_message:
            control_unit.display_message = ""

        train_x = 50 + (train.distance_traveled % 900)

        screen.fill(WHITE)
        pygame.draw.line(screen, BLACK, (50, 600), (WIDTH - 50, 600), 5)
        for i in range(3):
            station_x = 50 + i * 300
            color = YELLOW if train.at_station and abs(train_x - station_x) < 10 else GRAY
            pygame.draw.rect(screen, color, (station_x - 10, 590, 20, 20))
            screen.blit(font.render(f"Station {i+1}", True, BLACK), (station_x - 20, 610))
        pygame.draw.rect(screen, BLACK, (train_x, 550, 200, 50))
        door_positions = [train_x + 20 + i * 45 for i in range(4)]
        for i, pos in enumerate(door_positions):
            color = RED if train.doors[i] else GREEN
            pygame.draw.rect(screen, color, (pos, 550, 30, 50))
        screen.blit(font.render(f"{train.speed:.1f} km/h", True, BLACK), (train_x + 50, 520))

        bus.draw()
        for node in nodes:
            node.draw()
        control_unit.draw_interface()

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    simulate_tcms()
