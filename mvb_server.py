import asyncio
import websockets
import json
import random

PACKET_LOSS_PROB = 0.1
MIN_DELAY = 0.1
MAX_DELAY = 0.5

connected_clients = {}

async def handler(websocket, path=None):  # path now defaults to None
    register_message = await websocket.recv()
    reg_data = json.loads(register_message)
    node_name = reg_data.get("register")
    connected_clients[node_name] = websocket
    print(f"[Server] {node_name} connected.")

    try:
        async for message in websocket:
            data = json.loads(message)
            # Simulate packet loss
            if random.random() < PACKET_LOSS_PROB:
                print(f"[Server] Packet dropped: {data}")
                continue
            # Simulate network delay
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)
            target = data.get("target")
            if target in connected_clients:
                await connected_clients[target].send(message)
                print(f"[Server] Message from {data.get('sender')} delivered to {target}.")
            else:
                print(f"[Server] Target {target} not connected.")
    except websockets.exceptions.ConnectionClosed:
        print(f"[Server] {node_name} disconnected.")
    finally:
        if node_name in connected_clients:
            del connected_clients[node_name]

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("[Server] MVB Server started on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
