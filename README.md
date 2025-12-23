# WhatsApp Web PoC Bot

Proof-of-concept WhatsApp Web bot built with Python and Playwright. The bot automates the public WhatsApp Web UI to keep project scope small while demonstrating how far browser automation can go within a day.

## Features
- **Browser Automation**: Uses Playwright to control a real Chromium instance.
- **Session Persistence**: Saves login state to avoid scanning the QR code every time.
- **AI Integration**: Powered by Google Gemini (1.5 Flash) for natural language responses.
- **Dual Mode Commands**:
  - **System Commands**: Prefixed with `-` (e.g., `/bot -help`, `/bot -ping`).
  - **AI Queries**: Any other text after the prefix (e.g., `/bot explain quantum physics`).
- **Self-Response Support**: Can respond to commands sent by the bot's own account in the active chat.
- **Docker Ready**: Includes a Dockerfile for containerized deployment.

## Quickstart
1. **Setup venv**: Run `python -m venv venv` and then `venv\Scripts\Activate.ps1` on Windows
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Install Playwright browsers**: `playwright install chromium`
4. **Setup Environment**: Copy `.env.example` to `.env`. You can add your own `GOOGLE_API_KEY` if you prefer but for now a mock one is written on the example.
5. **Run the bot**: `py main.py`

On first run, scan the QR code manually. The session will be saved in `session.json` (default) for future use.

## Configuration
| Variable | Description |
| --- | --- |
| `BOT_COMMAND_PREFIX` | Prefix for the bot (default `/bot`). |
| `GOOGLE_API_KEY` | Your Google AI Studio API key for Gemini. |
| `SESSION_PATH` | Path to save the session JSON. |
| `LOG_LEVEL` | Logging detail (`INFO`, `DEBUG`). |
| `SIMULATION_MODE` | If `true`, the bot won't actually send messages to WhatsApp. Very usefull on testing the answers rather than sending functionality |
| `POLL_INTERVAL` | Seconds between checks for new messages. |

## Usage Examples
### Commands
You can define commands that you want the chatbot to respond to, for example:
- **Help**: `/bot -help`
- **Ping**: `/bot -ping`
### AI
- **AI Chat**: When wanting to ask something to the ai chatbot just follow the bot prefix with the question like this: `/bot ¿quién ganó el mundial de 1986?`

## Project Structure
```
whatsapp-web-poc-bot/
├── bot/
│   ├── browser.py
│   ├── session.py
│   ├── chat.py
│   ├── filters.py
│   └── handlers.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Implementation Notes
- **Message Detection**: The bot polls for unread chats and also monitors the active conversation for self-sent commands.
- **Command Parsing**: It distinguishes between system commands (starting with `-`) and AI queries automatically.
- **Selector Stability**: Uses scoped selectors within `main#main` to avoid "random" message detection from the sidebar.

## Limitations
- Highly dependent on WhatsApp Web selectors; DOM changes may break the automation.
- No message history persistence beyond Playwright storage state.
- Not suitable for production workloads; error handling is intentionally lightweight.
