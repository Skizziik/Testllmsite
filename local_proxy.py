"""
Local HTTP/WebSocket proxy for TryllServer.
Run this locally, then use cloudflared to expose it.

TryllServer uses a binary protocol:
- Messages are prefixed with 8-byte (uint64) size
- Message format: [8-byte size][JSON message + comma]

Usage:
1. Start TryllServer on port 1234
2. Run: python local_proxy.py
3. Run: cloudflared tunnel --url http://localhost:8765
4. Copy the URL and set it in Render environment variables
"""

import asyncio
import json
import struct
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="TryllServer Local Proxy")

# Allow CORS from any origin (for Render website)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRYLL_SERVER_HOST = "localhost"
TRYLL_SERVER_PORT = 1234
MESSAGE_SIZE_BYTES = 8  # uint64


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "tryll_server": f"{TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}"}


@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """
    WebSocket proxy to TryllServer.
    Handles the binary protocol (8-byte size prefix).
    """
    await websocket.accept()

    reader = None
    writer = None

    try:
        # Connect to TryllServer
        reader, writer = await asyncio.open_connection(
            TRYLL_SERVER_HOST,
            TRYLL_SERVER_PORT
        )
        print(f"Connected to TryllServer at {TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}")

        async def forward_to_client():
            """Forward messages from TryllServer to WebSocket client."""
            try:
                while True:
                    # Read 8-byte size prefix
                    size_data = await reader.readexactly(MESSAGE_SIZE_BYTES)
                    if not size_data:
                        break

                    message_size = struct.unpack('Q', size_data)[0]
                    print(f"Receiving message of size: {message_size}")

                    # Read the message
                    message_data = await reader.readexactly(message_size)
                    message = message_data.decode('utf-8', errors='replace')

                    # Remove trailing comma if present (TryllServer adds it)
                    if message.endswith(','):
                        message = message[:-1]

                    print(f"Forwarding to client: {message[:200]}...")
                    await websocket.send_text(message)

            except asyncio.IncompleteReadError:
                print("TryllServer closed connection")
            except Exception as e:
                print(f"Forward to client error: {e}")

        async def forward_to_server():
            """Forward messages from WebSocket client to TryllServer."""
            try:
                while True:
                    data = await websocket.receive_text()
                    print(f"Received from client: {data[:100]}...")

                    # Encode with size prefix (TryllServer protocol)
                    message_bytes = (data + ",").encode('utf-8')
                    size_prefix = struct.pack('Q', len(message_bytes))

                    writer.write(size_prefix + message_bytes)
                    await writer.drain()
                    print(f"Sent to TryllServer: {len(message_bytes)} bytes")

            except WebSocketDisconnect:
                print("WebSocket disconnected")
            except Exception as e:
                print(f"Forward to server error: {e}")

        # Run both directions concurrently
        await asyncio.gather(
            forward_to_client(),
            forward_to_server()
        )

    except ConnectionRefusedError:
        print(f"ERROR: Cannot connect to TryllServer at {TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}")
        error_msg = json.dumps({
            "error": "TryllServer not running",
            "message": f"Cannot connect to TryllServer at {TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}"
        })
        try:
            await websocket.send_text(error_msg)
            await websocket.close()
        except:
            pass
    except Exception as e:
        print(f"WebSocket proxy error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass


if __name__ == "__main__":
    print("=" * 50)
    print("TryllServer Local Proxy")
    print("=" * 50)
    print(f"Proxying to TryllServer at {TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}")
    print("WebSocket endpoint: ws://localhost:8765/ws")
    print("")
    print("TryllServer protocol: 8-byte size prefix + JSON + comma")
    print("")
    print("Next steps:")
    print("1. Make sure TryllServer is running on port 1234")
    print("2. In another terminal, run:")
    print("   C:\\Users\\utente\\Downloads\\cloudflared.exe tunnel --url http://localhost:8765")
    print("3. Copy the https://xxx.trycloudflare.com URL")
    print("4. Set TRYLL_TUNNEL_URL in Render environment variables")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8765)
