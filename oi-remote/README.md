# Stupidly-Simple Remote AI Desktop Controller

Control your desktop PC from a phone browser by chatting with an AI. This project provides a minimal viable product (MVP) to achieve this, using Open Interpreter (forked), FastAPI, and a React PWA.

## Project Structure

```
oi-remote/
├── openinterpreter/        # Forked Open Interpreter code (to be added/integrated)
├── oi_remote/              # Python backend modules (FastAPI, WebSocket, LLM selection)
│   ├── __init__.py
│   ├── llm_selector.py
│   ├── screen_streamer.py
│   ├── remote_gateway.py
│   └── __main__.py
├── web/                    # React + Vite PWA client
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ... (other PWA files)
├── tests/                  # End-to-end tests (to be added)
├── scripts/                # Build and run scripts (to be added)
├── requirements.txt        # Python dependencies for oi_remote
└── README.md               # This file
```

## Core Features

*   **Remote Control via Chat**: Interact with an LLM through a web interface on your phone to control your desktop.
*   **QR Code Pairing**: Securely pair your phone client with the desktop application using a QR code containing a JWT.
*   **Screen Streaming**: (Optional) View a live stream of your desktop on your phone.
*   **Configurable LLM**: Supports various LLM providers (OpenAI, Anthropic, Ollama) via environment variables.
*   **Cross-Platform**: Python backend and web-based client ensure broad compatibility.

## Setup and Running

**Prerequisites:**

*   Python 3.8+ and pip
*   Node.js and npm (for the PWA client)
*   An LLM provider API key or a running Ollama instance.

**1. Backend (`oi_remote` - FastAPI Server):**

   a. **Clone the repository (if you haven't already).**

   b. **Set up a Python virtual environment (recommended):**
      ```bash
      python -m venv .venv
      source .venv/bin/activate  # On Windows: .venv\Scripts\activate
      ```

   c. **Install Python dependencies:**
      ```bash
      pip install -r requirements.txt
      ```

   d. **Configure Environment Variables:**
      Create a `.env` file in the `oi-remote` root directory or set environment variables directly. See the "Environment Variables" section below for details. Minimally, you'll need to set `OI_LLM_PROVIDER` and the relevant API key/model, and `OI_REMOTE_JWT_SECRET`.
      
      Example `.env` file:
      ```env
      OI_LLM_PROVIDER="openai"
      OI_LLM_KEY="sk-your_openai_api_key_here"
      OI_LLM_MODEL="gpt-4-turbo-preview"
      OI_REMOTE_JWT_SECRET="your-super-strong-and-secret-jwt-key-please-change-me"
      # OI_REMOTE_PORT=3333 (Defaults to 3333)
      # OI_VERBOSE_LOGGING=true
      ```

   e. **Run the backend server:**
      ```bash
      python -m oi_remote
      ```
      The server will typically start on `http://localhost:3333`.

**2. Frontend (`web` - PWA Client):**

   a. **Navigate to the `web` directory:**
      ```bash
      cd web
      ```

   b. **Install Node.js dependencies:**
      ```bash
      npm install
      ```

   c. **Run the development server:**
      ```bash
      npm run dev
      ```
      The PWA will typically be available at `http://localhost:3000` (or the port shown in the terminal).

**3. Pairing:**

   a. Once the backend is running, it should print a QR code to the terminal OR you can navigate to `http://localhost:3333/pair` in a desktop browser to see the QR code.
   b. Open the PWA on your phone (e.g., `http://<your-desktop-ip>:3000`). 
   c. The PWA should attempt to fetch connection details automatically. If it were a separate device, you would scan the QR code displayed by the desktop application with your phone.

## Environment Variables (for `oi_remote`)

*   `OI_LLM_PROVIDER`: (Required) `openai`, `anthropic`, or `ollama`.
*   `OI_LLM_KEY`: API key for OpenAI or Anthropic.
*   `OI_LLM_MODEL`: Model name (e.g., `gpt-4-turbo-preview`, `claude-2`, `llama2`).
*   `OI_LLM_API_BASE`: (Optional) Custom API base URL, e.g., for local LLM proxies or Ollama if not at default `http://localhost:11434`.
*   `OI_REMOTE_JWT_SECRET`: (Required) A strong secret key for JWT generation. **CHANGE THE DEFAULT IF PROVIDED.**
*   `OI_REMOTE_PORT`: Port for the FastAPI server (default: `3333`).
*   `OI_STREAM_FPS`: Frames per second for screen streaming (default: `5`).
*   `OI_STREAM_QUALITY`: JPEG quality for screen streaming (default: `70`).
*   `OI_STREAM_WIDTH`, `OI_STREAM_HEIGHT`: (Optional) Resize stream to this resolution. If not set, uses primary monitor resolution.
*   `OI_VERBOSE_LOGGING`: Set to `true` for more detailed server logs.
*   `OI_ALLOW_ORIGINS`: Comma-separated list of allowed origins for CORS (e.g., `http://localhost:3000,http://127.0.0.1:3000`). Defaults to a permissive set for development.

## Next Steps / To-Do

*   **Integrate Open Interpreter**: Properly fork and patch the Open Interpreter codebase to use `llm_selector.py` and enable computer control functions.
*   **Implement Computer Control**: Wire up the `ChatBox` commands to actual Open Interpreter execution.
*   **Refine UI/UX**: Improve the PWA's design and user experience.
*   **Error Handling**: Enhance error handling and feedback in both backend and frontend.
*   **Testing**: Add comprehensive unit and end-to-end tests.
*   **Build/Run Scripts**: Create helper scripts for easier building and running.
*   **Security**: Review and harden security aspects (CORS, JWT handling, input sanitization).
*   **Documentation**: Expand on usage, advanced configuration, and troubleshooting.

## Contributing

(To be defined)
