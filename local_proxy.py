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

Logs are saved to: C:/Users/utente/Desktop/TryllEngine/testllmsite/reports_playes/
"""

import asyncio
import json
import struct
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Logging configuration
LOG_DIR = Path("C:/Users/utente/Desktop/TryllEngine/testllmsite/reports_playes")
LOG_DIR.mkdir(parents=True, exist_ok=True)
INTERACTIONS_FILE = LOG_DIR / "interactions.json"
FEEDBACK_FILE = LOG_DIR / "feedback.json"

# Current session tracking
current_session = {
    "session_id": None,
    "started_at": None,
    "messages": []
}


def load_json_file(filepath: Path) -> list:
    """Load JSON array from file, return empty list if not exists."""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []


def save_json_file(filepath: Path, data: list):
    """Save JSON array to file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_interaction(direction: str, message_type: str, content: dict):
    """Log an interaction (question/answer/rag)."""
    global current_session

    # Start new session if needed
    if current_session["session_id"] is None:
        current_session = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "started_at": datetime.now().isoformat(),
            "messages": []
        }

    entry = {
        "timestamp": datetime.now().isoformat(),
        "direction": direction,  # "client_to_server" or "server_to_client"
        "type": message_type,
        "content": content
    }
    current_session["messages"].append(entry)

    # Save to file
    interactions = load_json_file(INTERACTIONS_FILE)

    # Find or create session in interactions
    session_found = False
    for i, sess in enumerate(interactions):
        if sess.get("session_id") == current_session["session_id"]:
            interactions[i] = current_session
            session_found = True
            break

    if not session_found:
        interactions.append(current_session)

    save_json_file(INTERACTIONS_FILE, interactions)


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    message_index: Optional[int] = None
    question: str
    answer: str
    rating: str  # "positive" or "negative"
    comment: Optional[str] = None
    rag_chunks: Optional[list] = None


TRYLL_CONFIG_PATH = Path("C:/Users/utente/AppData/Local/Tryll/server/config.json")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "tryll_server": f"{TRYLL_SERVER_HOST}:{TRYLL_SERVER_PORT}"}


@app.get("/config")
async def get_config():
    """Get TryllServer configuration from local config file."""
    if TRYLL_CONFIG_PATH.exists():
        try:
            with open(TRYLL_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Config file not found"}


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Save user feedback locally."""
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": feedback.session_id or current_session.get("session_id"),
        "question": feedback.question,
        "answer": feedback.answer,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "rag_chunks": feedback.rag_chunks
    }

    feedbacks = load_json_file(FEEDBACK_FILE)
    feedbacks.append(feedback_entry)
    save_json_file(FEEDBACK_FILE, feedbacks)

    print(f"Feedback saved: {feedback.rating} - {feedback.question[:50]}...")
    return {"status": "ok", "message": "Feedback saved locally"}


@app.get("/logs/interactions")
async def get_interactions():
    """Get all logged interactions."""
    return load_json_file(INTERACTIONS_FILE)


@app.get("/logs/feedback")
async def get_feedback():
    """Get all feedback."""
    return load_json_file(FEEDBACK_FILE)


@app.get("/logs/stats")
async def get_stats():
    """Get statistics about interactions and feedback."""
    interactions = load_json_file(INTERACTIONS_FILE)
    feedbacks = load_json_file(FEEDBACK_FILE)

    total_sessions = len(interactions)
    total_messages = sum(len(s.get("messages", [])) for s in interactions)
    total_feedback = len(feedbacks)
    positive_feedback = len([f for f in feedbacks if f.get("rating") == "positive"])
    negative_feedback = len([f for f in feedbacks if f.get("rating") == "negative"])

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_feedback": total_feedback,
        "positive_feedback": positive_feedback,
        "negative_feedback": negative_feedback,
        "log_dir": str(LOG_DIR)
    }


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

                    # Log server response
                    try:
                        msg_json = json.loads(message)
                        if "agent" in msg_json:
                            agent_data = msg_json["agent"]
                            # Log complete response (state 5 = STREAMING_END)
                            if agent_data.get("state") == 5 and agent_data.get("response"):
                                log_interaction("server_to_client", "llm_response", {
                                    "response": agent_data.get("response"),
                                    "rag_ids": agent_data.get("rag_ids", []),
                                    "rag_scores": agent_data.get("rag_scores", [])
                                })
                    except:
                        pass

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

                    # Log user question
                    try:
                        msg_json = json.loads(data)
                        if "agent_message" in msg_json:
                            agent_msg = msg_json["agent_message"]
                            if agent_msg.get("message"):
                                log_interaction("client_to_server", "user_question", {
                                    "question": agent_msg.get("message")
                                })
                    except:
                        pass

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
