# nodes.py
"""Node classes for sensors, actuators, and control unit in the TCMS simulation."""

import pygame
import time
from constants import NUM_DOORS, CRUISING_SPEED, BLUE, PURPLE, BLACK, RED, GRAY, MAX_PASSENGERS

class Node:
    """Base class for all nodes in the simulation."""
    
    def __init__(self, name, color=BLUE):
        self.name = name
        self.x = 0
        self.color = color

    def draw(self, screen, font):
        """Draws the node on the screen."""
        node_y = 450
        pygame.draw.circle(screen, self.color, (int(self.x), node_y), 20)
        pygame.draw.line(screen, BLACK, (int(self.x), node_y), (int(self.x), node_y + 50), 2)
        screen.blit(font.render(self.name, True, BLACK), (int(self.x) - 40, node_y - 30))

class SensorNode(Node):
    """Node that periodically sends state updates."""
    
    def __init__(self, name, read_state_func, interval=1.0):
        super().__init__(name)
        self.read_state_func = read_state_func
        self.interval = interval
        self.last_send_time = 0
        self.last_value = None

    def update(self, current_time, send_message_func):
        """Sends state updates if the value changes."""
        if current_time - self.last_send_time > self.interval:
            msg = self.read_state_func()
            if msg != self.last_value:
                send_message_func(self.name, "Control", msg)
                print(f"[Sensor {self.name}] Sent message: {msg}")
                self.last_value = msg
            self.last_send_time = current_time

class ActuatorNode(Node):
    """Node that receives and acts on messages."""
    
    def __init__(self, name, set_state_func):
        super().__init__(name)
        self.set_state_func = set_state_func
        self.last_message = None

    def receive_message(self, message):
        """Processes received messages if they are new."""
        if message != self.last_message:
            print(f"[Actuator {self.name}] Received message: {message}")
            self.set_state_func(message)
            self.last_message = message

class ControlUnitNode(Node):
    """Node for user interaction and train control."""
    
    def __init__(self, name):
        super().__init__(name, color=PURPLE)
        self.current_speed = 0.0
        self.door_states = [False] * NUM_DOORS
        self.brakes_applied = False
        self.emergency_stop = False
        self.passengers = 0
        self.at_station = False
        self.display_message = ""
        self.last_commands = {}
        self.approaching_station = False
        self.emergency_stops_count = 0

    def receive_message(self, message):
        """Updates control unit state based on received messages."""
        print(f"[Control Unit {self.name}] Received message: {message}")
        if "Speed:" in message:
            self.current_speed = float(message.split(":")[1])
        elif "Door" in message:
            door_num = int(message.split(":")[0][-1])
            self.door_states[door_num] = "Open" in message.split(":")[1]
        elif "Passengers:" in message:
            self.passengers = int(message.split(":")[1])
        elif "Station:" in message:
            self.at_station = "Yes" in message.split(":")[1]

    def send_command(self, target, message, send_message_func):
        """Sends a command if not recently sent."""
        command_key = f"{target}:{message}"
        current_time = pygame.time.get_ticks() / 1000.0
        if command_key not in self.last_commands or current_time - self.last_commands[command_key] > 1.0:
            send_message_func(self.name, target, message)
            self.last_commands[command_key] = current_time
            return True
        return False

    def on_button_click(self, button, train, send_message_func):
        """Handles button clicks from the user interface."""
        if button == "Start Moving":
            if all(not state for state in self.door_states):
                if self.send_command("Traction", f"Set Target Speed:{CRUISING_SPEED}", send_message_func):
                    self.display_message = "Train starting..."
                    self.approaching_station = False
                    if train.at_station:
                        train.at_station = False
                        train.leaving_station = True
                        train.leaving_station_time = time.time()
                        print("[Control] Manually leaving station, setting cooldown")
            else:
                self.display_message = "Cannot start with doors open"
        elif button == "Apply Brakes":
            if self.send_command("Brake", "Apply Brakes", send_message_func):
                self.brakes_applied = True
                self.display_message = "Brakes applied"
                self.approaching_station = True
        elif button == "Release Brakes":
            if self.send_command("Brake", "Release Brakes", send_message_func):
                self.brakes_applied = False
                self.display_message = "Brakes released"
                self.approaching_station = False
                if self.send_command("Traction", "Set Target Speed:0", send_message_func):
                    if train.at_station:
                            self.display_message = "Brakes released, train holding at station"
                    elif train.emergency_stop:
                        self.display_message = "Brakes released, train in emergency stop"
                    else:
                        self.display_message = "Brakes released, train moving"
        elif button == "Open Doors":
            if self.current_speed < 1.0:
                for i in range(NUM_DOORS):
                    self.send_command(f"DoorActuator{i}", f"Open Door{i}", send_message_func)
                self.display_message = "Opening doors"
            else:
                self.display_message = "Cannot open doors while moving"
        elif button == "Close Doors":
            for i in range(NUM_DOORS):
                self.send_command(f"DoorActuator{i}", f"Close Door{i}", send_message_func)
            self.display_message = "Closing doors"
        elif button == "Emergency Stop":
            self.emergency_stops_count += 1
            if self.send_command("Emerg", f"Emergency Stop {self.emergency_stops_count}", send_message_func):
                self.emergency_stop = True
                self.display_message = "EMERGENCY STOP ACTIVATED"

    def draw_interface(self, screen, font, buttons):
        """Draws the control unit interface with buttons and status."""
        for name, rect in buttons.items():
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