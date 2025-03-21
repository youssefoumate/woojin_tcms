# network_bus.py
"""Network communication module simulating an MVB bus using websockets."""

import asyncio
import json
import random
import time
import websockets
import queue
import pygame
import logging
from constants import RED, BLACK

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Default configuration
PACKET_LOSS_PROB = 0.05
MIN_DELAY = 0.1
MAX_DELAY = 0.5

class NetworkMVB_Bus:
    """Manages network communication for the TCMS simulation."""
    
    def __init__(self, node_name, uri="ws://localhost:8765", debug_level="DEBUG"):
        self.node_name = node_name
        self.uri = uri
        self.websocket = None
        self.transmissions = []  # For message animation
        self.received_messages = queue.Queue()  # Thread-safe queue for received messages
        
        # Setup logger for this instance
        self.logger = logging.getLogger(f"NetworkBus.{node_name}")
        self.set_debug_level(debug_level)

    def set_debug_level(self, level):
        """Set the debug level for this instance."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "OFF": logging.CRITICAL + 10  # Higher than any standard level
        }
        
        numeric_level = level_map.get(level.upper(), logging.INFO)
        self.logger.setLevel(numeric_level)
        self.debug_enabled = numeric_level <= logging.DEBUG
        
    async def connect(self):
        """Establishes a websocket connection to the server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            await self.websocket.send(json.dumps({"register": self.node_name}))
            self.logger.info(f"Connected to network bus at {self.uri}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.websocket = None

    async def send_message(self, sender, target, message, real_target=None):
        """Sends a message over the network with simulated delay and packet loss."""
        if self.websocket is None:
            await self.connect()
        if self.websocket is None:
            self.logger.warning("Unable to connect; message not sent.")
            return

        effective_target = real_target if real_target is not None else target
        data = {
            "sender": sender,
            "target": "SimulationBus",
            "real_target": effective_target,
            "message": message
        }

        # Cache command messages locally for immediate processing
        if sender not in ["Speed", "Station", "Pass"]:
            self.received_messages.put(data.copy())

        if random.random() < PACKET_LOSS_PROB:
            self.logger.debug(f"Packet lost: {data}")
            return

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        self.logger.debug(f"Delaying packet to {effective_target} by {delay:.2f} sec: {message}")
        await asyncio.sleep(delay)
        try:
            await self.websocket.send(json.dumps(data))

            self.logger.debug(f"Sent: {sender} → {effective_target}: {message}")
            self.transmissions.append({
                "sender": sender,
                "target": effective_target,
                "message": message,
                "progress": 0.0,
                "start_x": None,
                "end_x": None
            })
        except websockets.ConnectionClosed:
            self.logger.warning("Connection closed while sending message.")
            self.websocket = None

    async def receive_message(self):
        """Receives a message from the websocket server."""
        if self.websocket is None:
            await self.connect()
        if self.websocket is None:
            return None
        try:
            message = await self.websocket.recv()
            data = json.loads(message)
            self.logger.debug(f"Received: {data.get('sender', 'unknown')} → {data.get('real_target', data.get('target', 'unknown'))}: {data.get('message', '')}")
            return data
        except websockets.ConnectionClosed:
            self.logger.warning("Connection closed during recv().")
            self.websocket = None
            return None

    async def listen(self):
        """Continuously listens for incoming messages."""
        while True:
            msg = await self.receive_message()
            if msg:
                self.received_messages.put(msg)
            else:
                self.logger.info("Attempting to reconnect...")
                await asyncio.sleep(1)
                await self.connect()

    def update_transmissions(self, delta_time):
        """Updates the progress of message transmission animations."""
        TRANSMISSION_TIME = 0.5
        for t in self.transmissions[:]:
            t["progress"] += delta_time / TRANSMISSION_TIME
            if t["progress"] >= 1.0:
                self.logger.debug(f"Transmission complete: {t['sender']} → {t['target']}: {t['message']}")
                self.transmissions.remove(t)

    def draw_transmissions(self, screen, font):
        """Draws animated message transmissions on the screen."""
        bus_y = 500
        for t in self.transmissions:
            if t["start_x"] is None or t["end_x"] is None:
                continue
            current_x = t["start_x"] + (t["end_x"] - t["start_x"]) * t["progress"]
            pygame.draw.circle(screen, RED, (int(current_x), bus_y), 5)
            label = font.render(t["message"], True, BLACK)
            screen.blit(label, (current_x - 20, bus_y - 20))