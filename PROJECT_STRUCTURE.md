# 📂 Project Structure Guide

This document outlines the folder structure and the purpose of each file in the **NewBot** project. Use this as a reference when collaborating.

## 📌 Root Directory

The main folder contains the core bot files and configuration.

| File / Folder | Description |
|--------------|-------------|
| `main.py` |  This is the entry point of the bot. It handles startup, loading extensions (cogs), and global error handling. |
| `config.py` | Contains sensitive configuration variables (like your Discord Token). **Do not share this file.** |
| `config_example.py` | A template for `config.py`. Collaborators should rename this to `config.py` and add their own token. |
| `requirements.txt` | Lists all Python libraries required to run the bot (e.g., `discord.py`). |
| `README.md` | General introduction and setup instructions for the project. |
| `.gitignore` | Tells Git which files to ignore (like `config.py` and `__pycache__`). |

---

## ⚙️ Cogs Folder (`/cogs`)

This folder contains modular extensions. Each file represents a category of commands.

| File | Description |
|------|-------------|
| `social.py` | Contains social commands like `hello` and `whoami`. Handles user interactions. |
| `utility.py` | unexpected/fun tools. Contains `roll` (dice) and `ping` (latency check). |
| `info.py` | properties of the bot. Contains `whomadeyou`, `whoareyou`, and `botinfo`. |
| `hidden.py` | **Admin/Maintenance**. Contains commands that are hidden from the help menu, like `downtime`. |

## 🚀 Quick Start for Collaborators

1. **Clone the repo**.
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Setup Config**: Rename `config_example.py` to `config.py` and add your bot token.
4. **Run**: `python main.py`
