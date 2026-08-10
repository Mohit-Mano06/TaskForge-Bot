# 📂 Project Structure Guide

This document outlines the folder structure and the purpose of each file in the **TaskForge-Bot** project.

## 📌 Root Directory

| File / Folder       | Description                                                                 |
| ------------------- | --------------------------------------------------------------------------- |
| `main.py`           | Entry point. Handles startup, extension loading, and global error handling. |
| `.env`              | **Secret**. Contains `TOKEN` and `MISTRAL_TOKEN`. Do not commit!            |
| `config_example.py` | Template for environment variable setup.                                    |
| `requirements.txt`  | Python library dependencies.                                                |
| `README.md`         | Setup instructions and feature overview.                                    |
| `logger.py`         | Specialized logging utility for moderation events.                          |
| `start.bat`         | Windows batch script to launch the bot.                                     |

---

## ⚙️ Cogs Directory (`/cogs`)

Modular extensions grouped by functionality.

### 📁 `cogs/ai/`

AI-powered features leveraging the Mistral SDK.

- `assistant.py`: Personal AI assistant with conversation memory (`$chat`).
- `chat.py`: Multi-turn bot interactions and roast battles (`$talktamabot`, `$roasttamabot`).
- `insights.py`: AI-driven server insights (`$obsessions`) and concept explanations (`$explain`).

### 📁 `cogs/music/`

High-performance audio engine.

- `player.py`: Core `yt-dlp` & `FFmpeg` playback system with queueing.
- `dj.py`: AI-powered playlist generation and auto-queueing (`$dj`).
- `ffmpeg/`: Local binaries for audio processing.

### 📁 `cogs/admin/`

Server management and security.

- `moderation.py`: Server control (kick, ban, purge, warn, lock).
- `logging.py`: Cross-server moderation event logging.
- `config.py`: Hardcoded settings (admin roles, channel IDs).
- `warnings.json`: Persistent storage for member warnings.

### 📁 `cogs/general/`

Core information and utility commands.

- `help.py`: Dynamic help menu with selection UI.
- `info.py`: Server/Bot statistics and user profiles.
- `announcement.py`: Automated AI-formatted version updates for the owner.
- `guide.py`: Setup instructions for developers (`$setupguide`).
- `status.py`: Automated bot status (presence) cycling logic.

### 📁 `cogs/utility/`

Productivity and helpful tools.

- `reminder.py`: User-facing personal reminders (`$reminder`).
- `tools.py`: General utilities (ping, roll, voice stats).

### 📁 `cogs/social/`

Interaction and fun.

- `confession.py`: Anonymous messaging system (`$confess`).

### ⚙️ System Cog (`cogs/system.py`)

- `system.py`: Real-time monitoring of CPU, RAM, and Bot Uptime.
