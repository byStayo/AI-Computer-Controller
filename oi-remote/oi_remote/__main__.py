import uvicorn
import os
import logging

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    host = os.getenv("OI_REMOTE_HOST", "0.0.0.0")
    try:
        port = int(os.getenv("OI_REMOTE_PORT", "3333"))
    except ValueError:
        logger.error("Invalid OI_REMOTE_PORT specified. Must be an integer. Defaulting to 3333.")
        port = 3333
    
    # Ensure Open Interpreter server URL is configured for the gateway to connect to
    oi_server_url = os.getenv('OI_SERVER_URL', 'http://localhost:8080') # Example default
    jwt_secret_preview = os.getenv('OI_REMOTE_JWT_SECRET', 'DEFAULT_NOT_SET')[:10] + "..."

    logger.info(f"🚀 Starting Stupidly-Simple Remote AI Gateway on {host}:{port}")
    logger.info(f"🔑 JWT Secret Hint: {jwt_secret_preview}")
    logger.info(f"🤖 Gateway will attempt to connect to Open Interpreter server at: {oi_server_url}")
    logger.info("Ensure Open Interpreter server is running and accessible at that URL.")
    logger.info("   Example: `interpreter --server --port 8080` (or your configured OI server port)")
    logger.info("Ensure LLM Provider & Key are set for Open Interpreter (e.g., OI_LLM_PROVIDER, OI_LLM_KEY).")

    uvicorn.run(
        "oi_remote.remote_gateway:app", 
        host=host, 
        port=port, 
        workers=1, # Single worker for simplicity, as state (streamer, ws_connections) is in-memory
        log_level="info",
        reload=False # Set to True for development if you want auto-reload on code changes
    )
