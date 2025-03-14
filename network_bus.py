# network_bus.py
"""Network communication module simulating an MVB bus using websockets."""

import asyncio
import json
import random
import time
import websockets
import queue
import pygame
from constants import RED, BLACK

PACKET_LOSS_PROB = 0.05
MIN_DELAY = 0.1
MAX_DELAY = 0.5
net_debug = False

class NetworkMVB_Bus:
    """Manages network communication for the TCMS simulation."""
    
    def __init__(self, node_name, uri="ws://localhost:8765"):
        self.node_name = node_name
        self.uri = uri
        self.websocket = None
        self.transmissions = []  # For message animation
        self.received_messages = queue.Queue()  # Thread-safe queue for received messages

    async def connect(self):
        """Establishes a websocket connection to the server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            await self.websocket.send(json.dumps({"register": self.node_name}))
            if net_debug:
                print(f"[Network Bus] {self.node_name} connected to network bus.")
        except Exception as e:
            if net_debug:
                print(f"[Network Bus] Connection error: {e}")
            self.websocket = None

    async def send_message(self, sender, target, message, real_target=None):
        """Sends a message over the network with simulated delay and packet loss."""
        if self.websocket is None:
            await self.connect()
        if self.websocket is None:
            if net_debug:
                print("[Network Bus] Unable to connect; message not sent.")
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
            if net_debug:
                print(f"[Network Bus] Packet lost locally: {data}")
            return

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        if net_debug:
            print(f"[Network Bus] Delaying packet {data} by {delay:.2f} sec.")
        await asyncio.sleep(delay)
        try:
            await self.websocket.send(json.dumps(data))

            if net_debug:
                print(f"[Network Bus] Sent message: {data}")
            self.transmissions.append({
                "sender": sender,
                "target": effective_target,
                "message": message,
                "progress": 0.0,
                "start_x": None,
                "end_x": None
            })
        except websockets.ConnectionClosed:
            if net_debug:
                print("[Network Bus] Connection closed while sending message.")
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
            if net_debug:
                print(f"[Network Bus] Received message: {data}")
            return data
        except websockets.ConnectionClosed:
            if net_debug:
                print("[Network Bus] Connection closed during recv().")
            self.websocket = None
            return None

    async def listen(self):
        """Continuously listens for incoming messages."""
        while True:
            msg = await self.receive_message()
            if msg:
                self.received_messages.put(msg)
            else:
                if net_debug:
                    print("[Network Bus] Attempting to reconnect...")
                await asyncio.sleep(1)
                await self.connect()

    def update_transmissions(self, delta_time):
        """Updates the progress of message transmission animations."""
        TRANSMISSION_TIME = 0.5
        for t in self.transmissions[:]:
            t["progress"] += delta_time / TRANSMISSION_TIME
            if t["progress"] >= 1.0:
                if net_debug:
                    print(f"[Network Bus] Transmission complete: {t}")
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