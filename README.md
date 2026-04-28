# 🧊 Fridge Manager (Web + Desktop)

> **A smart, AI-powered multi-platform fridge management system.** This project has evolved from a Python desktop application into a high-end, Vaporwave-themed web dashboard with AI Vision scanning and Telegram alerts.

---

## ⚡ Multi-Platform Support

| Version | Status | Tech Stack |
|---|---|---|
| 🌐 **Web Dashboard** | **Latest** | Flask, Vanilla JS, CSS (Vaporwave/Glassmorphism) |
| 💻 **Legacy Desktop** | **Legacy** | Python (Tkinter) |

---

## ✨ Features

| Feature | Description |
|---|---|
| 📦 **Inventory** | Track items with quantity, storage location (Fridge/Freezer), and expiry dates |
| 🛒 **Restock Alerts** | Auto-detect low-stock items below a configurable threshold |
| ⏰ **Expiry Monitor** | Get warnings for items expiring within a set number of days |
| 🍳 **Recipe Suggestions** | AI-matched recipes based on available ingredients |
| 🥗 **Nutrition Logger** | Log meals with calories & protein, view daily/weekly summaries |
| 📸 **Camera Scan** | Point your webcam at fridge contents — LLaVA AI detects food items automatically |
| 📲 **Telegram Bot** | Send restock / expiry reports and evening meal reminders to Telegram |
| 🎮 **Easter Egg** | Hold the logo for 3 seconds to unlock a hidden car-racing mini-game |

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/fridge-manager.git
cd fridge-manager
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure secrets
```bash
# Copy the template
cp .env.example .env
```

Open `.env` and fill in your values — see [Configuration](#%EF%B8%8F-configuration) below.

### 5. Run the app
```bash
python web_app.py
```

Open **http://localhost:5000** in your browser.

---

## ⚙️ Configuration

All secrets and runtime settings live in a `.env` file (**never committed**). Copy `.env.example` → `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Optional | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Optional | Your Telegram user/chat ID |
| `EVENING_HOUR` | Optional | Hour for evening reminder (24h, default `20`) |
| `EVENING_MINUTE` | Optional | Minute for evening reminder (default `0`) |
| `OLLAMA_URL` | Optional | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_VISION_MODEL` | Optional | Vision model name (default `llava`) |
| `FLASK_DEBUG` | Optional | `true` for dev hot-reload (default `true`) |
| `FLASK_PORT` | Optional | Port to run Flask on (default `5000`) |

> **Telegram is optional** — the app works fully without it. Camera scanning requires Ollama.

---

## 📸 Camera Scanning (Ollama + LLaVA)

1. [Install Ollama](https://ollama.com/download)
2. Pull the vision model:
   ```bash
   ollama pull llava
   ```
3. Start Ollama:
   ```bash
   ollama serve
   ```
4. Open the **Scan** tab in the app and click **Capture & Scan**.

---

## 📲 Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
2. Copy the token → paste into `TELEGRAM_TOKEN` in `.env`
3. Send a message to your new bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Copy the `id` from the response → paste into `TELEGRAM_CHAT_ID` in `.env`

---

## 🗂️ Project Structure

```
fridge_manager/
├── web_app.py              # Flask server & API routes (V2 Web App)
├── desktop_version/        # Legacy Desktop App (V1)
│   ├── main.py             # Entry point for desktop version
│   └── fridge.py           # Tkinter UI logic
├── database.py             # Shared: SQLAlchemy models & seed data
├── inventory.py            # Shared: Inventory CRUD helpers
├── scan.py                 # Shared: Ollama/LLaVA camera scan logic
├── recipes_recommendation.py  # Recipe matching logic
├── nutrition_calculator.py # Meal logging & nutrition stats
├── telegram_bot.py         # Telegram API + APScheduler reminders
├── requirements.txt        # Python dependencies
├── .env.example            # ← Template — copy to .env and fill in
├── .env                    # ← Your local secrets (git-ignored)
├── .gitignore
├── static/
│   ├── css/style.css       # Vaporwave UI styles
│   └── js/
│       ├── app.js          # Main frontend logic
│       └── game.js         # Easter egg mini-game
└── templates/
    └── index.html          # Single-page app template
```

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy (SQLite)
- **Frontend**: Vanilla JS, CSS (Glassmorphism / Vaporwave)
- **AI Vision**: [Ollama](https://ollama.com/) + LLaVA (local, no API key needed)
- **Notifications**: Telegram Bot API, APScheduler
- **Data**: NumPy, Pandas, Pillow, OpenCV

---

## 📜 License

MIT — feel free to fork, remix, and build on it.
