# simulation.py
"""Main simulation module for the TCMS with networked MVB communication."""

import pygame
import time
import threading
import asyncio
from network_bus import NetworkMVB_Bus
from train import Train
from nodes import SensorNode, ActuatorNode, ControlUnitNode
from constants import *

# Setup asyncio event loop in a separate thread
async_loop = asyncio.new_event_loop()

def start_async_loop(loop):
    """Start the asyncio event loop in a separate thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_async_loop, args=(async_loop,), daemon=True).start()

# Initialize network bus
network_bus = NetworkMVB_Bus("SimulationBus")
asyncio.run_coroutine_threadsafe(network_bus.listen(), async_loop)

def send_network_message(sender, target, message):
    """Sends a network message asynchronously."""
    asyncio.run_coroutine_threadsafe(
        network_bus.send_message(sender, "SimulationBus", message, real_target=target), async_loop
    )

# Define button layout
BUTTONS = {
    "Start Moving": pygame.Rect(50, 10, 120, 30),
    "Apply Brakes": pygame.Rect(180, 10, 120, 30),
    "Release Brakes": pygame.Rect(310, 10, 120, 30),
    "Open Doors": pygame.Rect(440, 10, 120, 30),
    "Close Doors": pygame.Rect(570, 10, 120, 30),
    "Emergency Stop": pygame.Rect(700, 10, 120, 30)
}

def initialize_pygame():
    """Initialize pygame and setup the display."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TCMS with Networked MVB Communication")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    return screen, clock, font

def create_train():
    """Create and return a train instance."""
    return Train()

def create_sensor_nodes(train):
    """Create and return all sensor nodes for the train."""
    speed_sensor = SensorNode("Speed", lambda: f"Speed:{train.speed:.1f}", interval=0.5)
    door_sensors = [SensorNode(f"DoorS{i}", lambda i=i: f"Door{i}:{'Open' if train.doors[i] else 'Closed'}") for i in range(NUM_DOORS)]
    passenger_sensor = SensorNode("Pass", lambda: f"Passengers:{train.passengers}")
    station_sensor = SensorNode("Station", lambda: f"Station:{'Yes' if train.at_station else 'No'}")
    return speed_sensor, door_sensors, passenger_sensor, station_sensor

def create_actuator_nodes(train):
    """Create and return all actuator nodes for the train."""
    # Define actuator callbacks
    def set_target_speed(msg):
        if "Set Target Speed:" in msg:
            train.target_speed = float(msg.split(":")[1])
            print(f"[Traction] Setting target speed to {train.target_speed}")

    def set_brake_state(msg):
        if msg == "Apply Brakes":
            train.brakes_applied = True
            print("[Brake] Brakes applied")
        if msg == "Release Brakes":
            train.brakes_applied = False
            print("[Brake] Brakes released")

    def set_emergency_state(msg):
        if  "Emergency Stop" in msg:
            train.emergency_stop = True
            train.target_speed = 0
            print("[Emergency] Emergency stop activated")

    def set_door_state(msg, door_idx):
        if f"Open Door{door_idx}" in msg:
            train.doors[door_idx] = True
            print(f"[Door{door_idx}] Door opened")
        elif f"Close Door{door_idx}" in msg:
            train.doors[door_idx] = False
            print(f"[Door{door_idx}] Door closed")

    traction_actuator = ActuatorNode("Traction", set_target_speed)
    brake_actuator = ActuatorNode("Brake", set_brake_state)
    emergency_actuator = ActuatorNode("Emerg", set_emergency_state)
    door_actuators = [ActuatorNode(f"DoorActuator{i}", lambda msg, i=i: set_door_state(msg, i)) for i in range(NUM_DOORS)]
    
    return traction_actuator, brake_actuator, emergency_actuator, door_actuators

def create_control_unit():
    """Create and return the control unit node."""
    return ControlUnitNode("Control")

def position_nodes(nodes):
    """Position all nodes along the bus line."""
    bus_start = 50
    bus_end = WIDTH - 50
    spacing = (bus_end - bus_start) / (len(nodes) - 1)
    for i, node in enumerate(nodes):
        node.x = bus_start + i * spacing

def handle_station_approach(train, control_unit):
    """Handle automated station approach logic."""
    if not train.at_station and not train.emergency_stop and not train.leaving_station:
        current_pos = train.distance_traveled % (STATION_DISTANCE * 3)
        distances_to_stations = [(pos - current_pos) % (STATION_DISTANCE * 3) for pos in [0, STATION_DISTANCE, STATION_DISTANCE * 2]]
        distance_to_next_stop = min([dist for dist in distances_to_stations if dist > 0], default=STATION_DISTANCE)
        stopping_distance = (train.speed ** 2) / (2 * DECELERATION)
        buffer = 20
        
        if distance_to_next_stop <= (stopping_distance + buffer) and train.speed > 2:
            if not control_unit.approaching_station:
                control_unit.approaching_station = True
                control_unit.send_command("Brake", "Apply Brakes", send_network_message)
                control_unit.brakes_applied = True
                control_unit.display_message = f"Approaching station, braking. Distance: {distance_to_next_stop:.1f}"
                
        if distance_to_next_stop < 10 and train.speed < 5:
            train.speed = 0
            train.target_speed = 0
            control_unit.send_command("Traction", "Set Target Speed:0", send_network_message)
            control_unit.approaching_station = False
            control_unit.display_message = "Arrived at station"

def handle_events(control_unit, train, current_time):
    """Handle pygame events."""
    message_timer = 0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, message_timer
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            for name, rect in BUTTONS.items():
                if rect.collidepoint(pos):
                    control_unit.on_button_click(name, train, send_network_message)
                    message_timer = current_time + 2
    return True, message_timer

def update_sensors(speed_sensor, door_sensors, passenger_sensor, station_sensor, current_time):
    """Update all sensor nodes."""
    speed_sensor.update(current_time, send_network_message)
    for sensor in door_sensors:
        sensor.update(current_time, send_network_message)
    passenger_sensor.update(current_time, send_network_message)
    station_sensor.update(current_time, send_network_message)

def process_network_messages(network_bus, nodes):
    """Process all pending network messages."""
    while not network_bus.received_messages.empty():
        msg = network_bus.received_messages.get()
        intended_target = msg.get("real_target", msg.get("target"))
        for node in nodes:
            if hasattr(node, 'receive_message') and node.name == intended_target:
                node.receive_message(msg["message"])
                break

def handle_station_actions(train, control_unit, previous_at_station):
    """Handle actions when arriving at stations."""
    if train.at_station and not previous_at_station and train.speed < 0.1:
        for i in range(NUM_DOORS):
            control_unit.send_command(f"DoorActuator{i}", f"Open Door{i}", send_network_message)
        control_unit.display_message = "At station, opening doors"
    if train.at_station:
        train.board_passengers()
    return train.at_station

def update_positions(train, network_bus, nodes):
    """Update positions of train and message transmissions."""
    train_x = 50 + (train.distance_traveled % (STATION_DISTANCE * 3))
    network_bus.update_transmissions(min(1/60, 0.1))  # Cap delta_time at 1/60 for consistent animation
    
    # Update transmission positions
    for t in network_bus.transmissions:
        sender_node = next((n for n in nodes if n.name == t["sender"]), None)
        target_node = next((n for n in nodes if n.name == t["target"]), None)
        if sender_node and target_node:
            t["start_x"] = sender_node.x
            t["end_x"] = target_node.x
        elif sender_node:
            # Find control unit if real target not found
            control_unit = next((n for n in nodes if n.name == "Control"), None)
            if control_unit:
                t["start_x"] = sender_node.x
                t["end_x"] = control_unit.x
    
    return train_x

def draw_environment(screen, font, train_x, train):
    """Draw the simulation environment (track, stations, train)."""
    screen.fill(WHITE)
    # Draw bus line
    pygame.draw.line(screen, BLACK, (50, 500), (WIDTH - 50, 500), 3)
    # Draw track
    pygame.draw.line(screen, BLACK, (50, 600), (WIDTH - 50, 600), 5)
    
    # Draw stations
    for i in range(3):
        station_x = 50 + i * STATION_DISTANCE
        is_at_station = train.at_station and abs(train_x - station_x) < 15
        color = YELLOW if is_at_station else GRAY
        pygame.draw.rect(screen, color, (station_x - 10, 590, 20, 20))
        screen.blit(font.render(f"Station {i+1}", True, BLACK), (station_x - 30, 610))
    
    # Draw train
    pygame.draw.rect(screen, BLACK, (train_x, 550, 200, 50))
    # Draw doors
    door_positions = [train_x + 20 + i * 45 for i in range(NUM_DOORS)]
    for i, pos in enumerate(door_positions):
        color = RED if train.doors[i] else GREEN
        pygame.draw.rect(screen, color, (pos, 550, 30, 50))
    # Draw speed indicator
    screen.blit(font.render(f"{train.speed:.1f} km/h", True, WHITE), (train_x + 50, 570))

def draw_debug_info(screen, font, train_x, train):
    """Draw debug information."""
    debug_info = [
        f"Speed: {train.speed:.2f}",
        f"Target: {train.target_speed:.2f}",
        f"Brakes: {'On' if train.brakes_applied else 'Off'}",
        f"Emerg: {'On' if train.emergency_stop else 'Off'}",
        f"At Station: {'Yes' if train.at_station else 'No'}",
        f"Leaving Station: {'Yes' if train.leaving_station else 'No'}",
        f"Distance: {train.distance_traveled:.2f}",
        f"Passengers: {train.passengers}/{MAX_PASSENGERS}",
        f"Doors: {sum(train.doors)} Open, {NUM_DOORS - sum(train.doors)} Closed"
    ]
    for i, text in enumerate(debug_info):
        screen.blit(font.render(text, True, BLACK), (train_x + 50, 770 - (i+1) * 20))

def main():
    """Runs the TCMS simulation."""
    screen, clock, font = initialize_pygame()
    train = create_train()
    
    # Create nodes
    speed_sensor, door_sensors, passenger_sensor, station_sensor = create_sensor_nodes(train)
    traction_actuator, brake_actuator, emergency_actuator, door_actuators = create_actuator_nodes(train)
    control_unit = create_control_unit()
    
    # Compile all nodes into a list
    nodes = [speed_sensor] + door_sensors + [passenger_sensor, station_sensor, 
             traction_actuator, brake_actuator, emergency_actuator] + door_actuators + [control_unit]
    
    # Position nodes along the bus
    position_nodes(nodes)
    
    running = True
    message_timer = 0
    previous_at_station = False
    last_frame_time = time.time()

    while running:
        current_time = pygame.time.get_ticks() / 1000.0
        now = time.time()
        delta_time = min(now - last_frame_time, 0.1)  # Cap delta_time to avoid physics issues
        last_frame_time = now

        # Handle station approach logic
        handle_station_approach(train, control_unit)

        # Handle events
        running, new_message_timer = handle_events(control_unit, train, current_time)
        if new_message_timer > 0:
            message_timer = new_message_timer

        # Update sensors
        update_sensors(speed_sensor, door_sensors, passenger_sensor, station_sensor, current_time)

        # Process network messages
        process_network_messages(network_bus, nodes)

        # Update train and handle station actions
        train.update(delta_time)
        previous_at_station = handle_station_actions(train, control_unit, previous_at_station)

        # Clear message display if timer expired
        if current_time > message_timer:
            control_unit.display_message = ""

        # Update positions of train and message transmissions
        train_x = update_positions(train, network_bus, nodes)

        # Draw everything
        draw_environment(screen, font, train_x, train)
        draw_debug_info(screen, font, train_x, train)
        
        # Draw network communication
        network_bus.draw_transmissions(screen, font)
        
        # Draw all nodes
        for node in nodes:
            node.draw(screen, font)
        
        # Draw control interface
        control_unit.draw_interface(screen, font, BUTTONS)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()