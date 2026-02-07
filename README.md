# NewBot 🤖

A simple Discord bot built with Python and `discord.py`, developed by Momo. This bot performs various fun and utility tasks for your server.

## Features ✨

- **General Commands**
  - `$hello`: Get a friendly greeting! 👋
  - `$roll`: Roll a 6-sided dice 🎲
  - `$me`: View your user information (ID, Join Date, Avatar) 👤
  - `$ping`: Check the bot's latency with witty responses ⚡

- **Bot Information**
  - `$whomadeyou`: Find out who created the bot 🛠️
  - `$whoareyou`: Learn about the bot's purpose 🤖
  - `$botinfo`: Get the link to the GitHub repository 🔗
  - `$help`: Display a list of all available commands 📜

## Prerequisites 📋

- Python 3.8 or higher
- A Discord Bot Token (from the [Discord Developer Portal](https://discord.com/developers/applications))

## Installation 🚀

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mohit-Mano06/NewBot.git
   cd NewBot
   ```

2. **Install dependencies**
   ```bash
   pip install discord.py
   ```

3. **Configuration**
   - Rename `config_example.py` to `config.py`:
     - On Windows: `ren config_example.py config.py`
     - On Linux/Mac: `mv config_example.py config.py`
   - Open `config.py` and replace `DISCORD_BOT_TOKEN_HERE` with your actual bot token.

   ```python
   # config.py
   TOKEN = "your_actual_bot_token_here"
   ```

## Usage 🎮

Run the bot using Python:

```bash
python bot.py
```

Once online, use the prefix `$` to interact with the bot (e.g., `$hello`, `$ping`).

## Contributing 🤝

Contributions are welcome! Feel free to open issues or submit pull requests to improve the bot.

## Author ✍️

- **Momo** - *Creator & Developer*

---
*Created with ❤️ by Momo*
