"""
Local HTTP/WebSocket proxy for TryllServer.
Run this locally, then use cloudflared to expose it.

Usage:
1. Start TryllServer on port 1234
2. Run: python local_proxy.py
3. Run: cloudflared tunnel --url http://localhost:8765
4. Copy the URL and set it in Render environment variables
"""

import asyncio
import json
import socket
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "tryll_server": f"{TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}"}


@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """
    WebSocket proxy to TryllServer.
    Connects browser WebSocket to local TryllServer TCP socket.
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
                buffer = ""
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break

                    # Decode and accumulate data
                    buffer += data.decode('utf-8', errors='replace')

                    # Try to parse complete JSON messages
                    # TryllServer sends JSON objects, possibly multiple
                    while buffer:
                        buffer = buffer.strip()
                        if not buffer:
                            break

                        # Find the end of a JSON object
                        try:
                            # Try to parse from the beginning
                            obj, end_idx = json.JSONDecoder().raw_decode(buffer)
                            # Send the complete JSON
                            await websocket.send_text(json.dumps(obj))
                            # Remove parsed portion
                            buffer = buffer[end_idx:].strip()
                        except json.JSONDecodeError:
                            # Incomplete JSON, wait for more data
                            break

            except Exception as e:
                print(f"Forward to client error: {e}")

        async def forward_to_server():
            """Forward messages from WebSocket client to TryllServer."""
            try:
                while True:
                    data = await websocket.receive_text()
                    print(f"Received from client: {data[:100]}...")
                    writer.write(data.encode('utf-8'))
                    await writer.drain()
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
        error_msg = json.dumps({
            "error": "TryllServer not running",
            "message": f"Cannot connect to TryllServer at {TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}"
        })
        await websocket.send_text(error_msg)
        await websocket.close()
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
    print("Next steps:")
    print("1. Make sure TryllServer is running on port 1234")
    print("2. In another terminal, run:")
    print("   C:\\Users\\utente\\Downloads\\cloudflared.exe tunnel --url http://localhost:8765")
    print("3. Copy the https://xxx.trycloudflare.com URL")
    print("4. Set TRYLL_TUNNEL_URL in Render environment variables")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8765)
