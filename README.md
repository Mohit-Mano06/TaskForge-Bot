# TaskForge-Bot🤖

A simple Discord bot built with Python and `discord.py`, developed by Mohit and Anis. This bot performs various fun and utility tasks for your server.

## Features ✨

- **Fun & Social**: Greet the bot and get friendly responses.
- **Utilities**: Roll dice, check latency, and monitor uptime.
- **Information**: Detailed bot stats and user profile information.
- **Reminders**: Set pending reminders for yourself or voice channel members.
- **Voice**: Connect to voice channels, check status, and play sounds (WIP).

## Bot Information ℹ️

- **Developer**: Momo (Mohit & Anis)
- **Library**: discord.py
- **Language**: Python 3.12+

## Commands 🛠️

The bot uses the `$` prefix for all commands.

### General & Utilities
- `$hello`: Get a friendly greeting! 👋
- `$roll`: Roll a 6-sided dice 🎲
- `$ping`: Check the bot's latency (API & WebSocket) ⚡
- `$uptime`: View how long the bot has been running ⏱️
- `$help`: Display this help menu 📜

### Reminders
- `$reminder <time> <message>`: Set a personal reminder. 
  *Example: `$reminder 10m Take a break`*
- `$vcreminder <time> <message>`: Set a reminder for everyone in your current voice channel.
- `$vcmembers`: List all members currently in your voice channel. 👥

### Voice
- `$connect`: Connect the bot to your current voice channel. 🔊
- `$disconnect`: Disconnect the bot from voice. 🔇
- `$vcstat`: View voice connection quality and member stats. 📡
- `$play <sound_name>`: Play a specific sound file (WIP). 🎵

### Information
- `$whomadeyou`: Find out about the creators. 🛠️
- `$whoareyou`: Learn about the bot's purpose. 🤖
- `$botinfo`: Technical statistics about the bot instance. 📊
- `$whoami`: View your own user details (ID, Join Date, Avatar). 👤

## Upcoming Features 🔮

- **Notes System**: Save and retrieve personal notes.
- **Enhanced Voice**: Full music playback support and soundboard.
- **Advanced Logging**: Better tracking of server events.
