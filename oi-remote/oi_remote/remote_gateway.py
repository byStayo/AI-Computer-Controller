import asyncio
import json
import time
import os
import jwt
import qrcode
import io
import socket
import logging
from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware # For PWA dev if on different port
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

# Assuming Open Interpreter server might run on a different port or be interacted with via its own API/CLI
# For this MVP, we'll assume the core logic of Open Interpreter is either imported and used directly,
# or its server component is running and we make API calls to it.
# The prompt "interpreter --server && python -m oi_remote" suggests two separate processes.
# Let's assume an HTTP client for OI server for now.
import httpx 

from .screen_streamer import ScreenStreamer # Use a class instance

# --- Configuration ---
logger = logging.getLogger("oi_remote_gateway")
logging.basicConfig(level=logging.INFO)

OI_SERVER_URL = os.getenv("OI_SERVER_URL", "http://localhost:8080") # Open Interpreter's server URL
# Port 8080 is just an example, OI's default server port might differ (e.g. 7878, or configurable)
JWT_SECRET = os.getenv("OI_REMOTE_JWT_SECRET", "CHANGE_THIS_SUPER_SECRET_KEY_PLEASE")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("OI_REMOTE_JWT_EXPIRATION", 1800))  # 30 minutes

if JWT_SECRET == "CHANGE_THIS_SUPER_SECRET_KEY_PLEASE":
    logger.warning("SECURITY WARNING: Using default JWT_SECRET. Please set a strong OI_REMOTE_JWT_SECRET.")

# --- Dependencies & State ---
app = FastAPI(title="Stupidly-Simple Remote AI Gateway")
screen_streamer = ScreenStreamer() # Instantiate the streamer

# Add CORS middleware if PWA is served from a different origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Or specify PWA origin e.g., ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active WebSocket connections and their associated OI conversation state
# Key: WebSocket connection ID (str)
# Value: { "oi_conversation_id": str | None, "mode": "YOLO" | "SAFE", "user_sub": str }
active_ws_connections = {}

# --- Utility Functions ---
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1" # Fallback
    finally:
        if 's' in locals(): s.close()
    return ip

async def get_current_user_sub(token: str = Depends(lambda ws: ws.query_params.get("token"))):
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token not provided")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_sub = payload.get("sub")
        if user_sub == "oi-remote-user": # Or more specific user ID if needed
            return user_sub
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token subject")
    except jwt.ExpiredSignatureError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token has expired")
    except jwt.InvalidTokenError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
    except Exception as e: # Catch any other jwt decode errors
        logger.error(f"Token validation error: {e}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token validation failed")

# --- FastAPI Routes ---
@app.get("/pair", response_class=StreamingResponse, tags=["Pairing"])
async def pair_qr_code_image():
    local_ip = get_local_ip()
    # The PWA client will connect to this gateway
    gateway_port = os.getenv("OI_REMOTE_PORT", "3333") 
    token = jwt.encode(
        {"exp": time.time() + JWT_EXPIRATION_SECONDS, "sub": "oi-remote-user"},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    # This URL is what the PWA will use to connect via WebSocket
    pairing_url_for_pwa = f"ws://{local_ip}:{gateway_port}/ws?token={token}"
    
    img = qrcode.make(pairing_url_for_pwa)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    logger.info(f"Generated QR code for pairing URL: {pairing_url_for_pwa}")
    return StreamingResponse(buf, media_type="image/png")

@app.get("/pair/url", response_class=PlainTextResponse, tags=["Pairing"])
async def pair_qr_code_text_url():
    local_ip = get_local_ip()
    gateway_port = os.getenv("OI_REMOTE_PORT", "3333")
    token = jwt.encode(
        {"exp": time.time() + JWT_EXPIRATION_SECONDS, "sub": "oi-remote-user"},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    pairing_url_for_pwa = f"ws://{local_ip}:{gateway_port}/ws?token={token}"
    return pairing_url_for_pwa

@app.get("/stream", tags=["Screen Streaming"])
async def video_stream_endpoint(request: Request):
    # Basic check: is streaming globally enabled and active?
    # More robust auth could be added here if needed (e.g., check JWT from a cookie)
    if not screen_streamer.is_streaming:
        return HTMLResponse("Screen streaming is not currently active. Send 'WATCH' command via WebSocket to start.", status_code=404)
    
    return StreamingResponse(
        screen_streamer.stream_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_sub: str = Depends(get_current_user_sub)):
    await websocket.accept()
    ws_id = str(websocket.client.host) + ":" + str(websocket.client.port) # Simple ID
    active_ws_connections[ws_id] = {"oi_conversation_id": None, "mode": "YOLO", "user_sub": user_sub}
    logger.info(f"WebSocket connection {ws_id} accepted for user: {user_sub}")

    try:
        while True:
            raw_data = await websocket.receive_text()
            message = json.loads(raw_data)
            msg_type = message.get("type")
            payload = message.get("payload")
            logger.debug(f"Msg from {ws_id}: Type={msg_type}, Payload={payload}")

            if msg_type == "command":
                command_text = payload.get("text")
                # For SAFE mode, the plan would be sent from OI, then user confirms here.
                # For YOLO, command goes straight to OI for execution.
                
                # Interact with Open Interpreter Server
                # This is a simplified interaction. OI's actual /chat or /execute API might be more complex.
                oi_response_data = None
                async with httpx.AsyncClient(timeout=300.0) as client: # 5 min timeout
                    try:
                        # Construct message for OI server
                        # OI server may manage conversations internally, or we pass a conversation_id
                        # Example using OI's /chat endpoint format (hypothetical)
                        oi_payload = {
                            "messages": [{"role": "user", "content": command_text}],
                            # "conversation_id": active_ws_connections[ws_id].get("oi_conversation_id") # If OI supports it
                            # Model/provider selection should be handled by the patched OI instance itself via env vars
                        }
                        response = await client.post(f"{OI_SERVER_URL}/chat", json=oi_payload)
                        response.raise_for_status() # Raise an exception for bad status codes
                        oi_response_data = response.json()
                    except httpx.RequestError as e:
                        logger.error(f"OI Server Request Error: {e}")
                        await websocket.send_json({"type": "error", "payload": f"Failed to connect to Open Interpreter: {e}"})
                        continue
                    except httpx.HTTPStatusError as e:
                        logger.error(f"OI Server HTTP Error: {e.response.status_code} - {e.response.text}")
                        await websocket.send_json({"type": "error", "payload": f"Open Interpreter error: {e.response.status_code} - {e.response.text}"})
                        continue
                    except Exception as e:
                        logger.error(f"Error processing OI response: {e}")
                        await websocket.send_json({"type": "error", "payload": f"Error processing OI response: {e}"})
                        continue
                
                if oi_response_data:
                    # Assume oi_response_data = {"messages": [{"role": "assistant", "content": "..."}], "conversation_id": "..."}
                    # This is a highly simplified model of OI's output.
                    # OI usually yields multiple message types (code, execution, confirmation requests).
                    assistant_reply = next((m["content"] for m in oi_response_data.get("messages", []) if m["role"] == "assistant"), "No reply from assistant.")
                    await websocket.send_json({"type": "response", "payload": {"text": assistant_reply}})
                    # Update conversation ID if OI provides it
                    if "conversation_id" in oi_response_data:
                        active_ws_connections[ws_id]["oi_conversation_id"] = oi_response_data["conversation_id"]

            elif msg_type == "control_stream":
                action = payload.get("action")
                if action == "WATCH":
                    if not screen_streamer.is_streaming:
                        screen_streamer.start()
                    await websocket.send_json({"type": "stream_status", "payload": {"status": "active"}})
                elif action == "STOP":
                    if screen_streamer.is_streaming:
                        screen_streamer.stop()
                    await websocket.send_json({"type": "stream_status", "payload": {"status": "inactive"}})
            
            elif msg_type == "set_mode":
                mode = payload.get("mode")
                if mode in ["SAFE", "YOLO"]:
                    active_ws_connections[ws_id]["mode"] = mode
                    await websocket.send_json({"type": "mode_status", "payload": {"mode": mode}})
                else:
                    await websocket.send_json({"type": "error", "payload": "Invalid mode specified"})
            else:
                await websocket.send_json({"type": "error", "payload": "Unknown message type"})

    except (ConnectionClosed, ConnectionClosedOK):
        logger.info(f"WebSocket connection {ws_id} closed.")
    except WebSocketException as e: # Custom exception for auth failures to send specific close codes
        logger.warning(f"WebSocket policy violation for {ws_id}: Code={e.code}, Reason={e.reason}")
        # FastAPI handles sending the close frame for WebSocketException
    except Exception as e:
        logger.error(f"Unexpected WebSocket error for {ws_id}: {e}", exc_info=True)
        # Attempt to send a generic error before closing if socket is still open
        if not websocket.client_state == websocket.WebSocketState.DISCONNECTED:
            try:
                await websocket.send_json({"type": "error", "payload": "An unexpected server error occurred."})
            except Exception:
                pass # Ignore if cannot send
    finally:
        if screen_streamer.is_streaming and not any(conn.get("is_watching_stream") for conn_id, conn in active_ws_connections.items() if conn_id != ws_id):
            # A more sophisticated check would be if THIS ws was watching.
            # For simplicity, stop if this was the last connection (or only connection) that might have been watching.
            # screen_streamer.stop() # Or manage based on explicit WATCH/STOP from clients
            pass # Let clients explicitly stop the stream or stop on last disconnect
        if ws_id in active_ws_connections:
            del active_ws_connections[ws_id]
            logger.info(f"Cleaned up connection state for {ws_id}")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_landing_page():
    return """
    <html><head><title>Stupidly-Simple Remote AI Gateway</title></head>
    <body><h1>Remote AI Gateway Active</h1>
    <p>Scan QR from PWA to connect. Status endpoints:</p>
    <ul>
        <li><a href="/docs">/docs</a> - API Documentation</li>
        <li><a href="/pair">/pair</a> - Pairing QR Code Image</li>
        <li><a href="/pair/url">/pair/url</a> - Pairing URL Text</li>
    </ul>
    </body></html>
    """

# Custom WebSocketException to allow specific close codes for auth
class WebSocketException(HTTPException):
    def __init__(self, code: int, reason: str):
        super().__init__(status_code=code, detail=reason) # Misusing HTTPException for structure
        self.code = code
        self.reason = reason

@app.exception_handler(WebSocketException)
async def websocket_exception_handler(websocket: WebSocket, exc: WebSocketException):
    await websocket.close(code=exc.code, reason=exc.reason)
