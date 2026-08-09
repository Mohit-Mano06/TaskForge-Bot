# TaskForge-Bot 🤖 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**TaskForge** is a high-performance, AI-integrated Discord bot built with `discord.py`. It transforms your server into a productive and entertaining hub with advanced AI assistants, high-fidelity music streaming, and smart automation.

---

## 🌟 Key Features

### 🧠 TaskForge AI Ecosystem (Powered by Mistral AI)

- **Personal AI Assistant**: Engage in natural, context-aware conversations using `$chat`. TaskForge remembers your last few messages for a truly interactive experience.
- **AI DJ**: Generate custom, high-quality playlists based on your mood, genre, or artist using `$dj`. TaskForge automatically searches and queues the tracks for you.
- **Server Insights & "Obsessions"**: Use `$obsessions` to see what your server is currently hyped about. TaskForge analyzes recent chat trends to find trending topics.
- **Explain Anything**: Use `$explain` to get simplified explanations of complex topics at 4 different levels (Beginner to Expert).
- **Bot Interactions**: Experience witty AI-driven roasts and multi-turn conversations between TaskForge and other bots like Tamabot.

### 🎵 High-Fidelity Music Experience

- **Crystal Clear Audio**: YouTube streaming powered by `yt-dlp` and local `FFmpeg` processing for zero-lag playback.
- **Intelligent Queueing**: Full support for adding, skipping, pausing, and clearing track queues.
- **Voice Stats**: Monitor your voice connection quality in real-time with `$vcstat`.

### 📊 Advanced Server Leaderboards (Powered by Supabase)

- **Comprehensive Tracking**: Real-time activity monitoring for messages sent, voice channel duration, and bot command usage.
- **Channel Analytics**: Insights into which channels are the most active within your server.
- **Persistent Data**: High-speed data persistence using Supabase, ensuring stats are never lost during bot restarts.
- **Historical Sync**: Admin tools to scrape and import past message history into the leaderboard.

### ⚡ Smart Productivity & Server Control

- **Dynamic Reminders**: Set personal or voice-channel wide alerts (`$reminder`, `$vcreminder`) with flexible time formats.
- **Passive Economy Rewards**: Earn coins and XP automatically through chat activity and voice participation.
- **Advanced Moderation**: A full suite of tools (purge, kick, ban, warn, lock) with cross-server audit logging.
- **System Monitoring**: Keep an eye on bot performance with real-time tracking of RAM, CPU, and Uptime via `$stats`.

---

## ℹ️ Bot Information

- **Library**: `discord.py` (2.3+)
- **Language**: Python 3.12+ (Optimized for 3.14)
- **AI Engine**: Mistral AI (Small & Large models)
- **Audio Engine**: FFmpeg (Local binary supported)

---

## 🛠️ Commands

All commands use the `$` prefix.

### 🤖 AI Assistant & Insights

- `$chat <message>`: Chat with TaskForge AI Assistant (with long-term memory).
- `$talk <message>`: Get a witty, sassy, or funny AI reply (short & sassy).
- `$roast [target or message]`: Roast someone or yourself with a savage AI reply.
- `$resetchat`: Clear your AI conversation history.
- `$explain <level> <topic>`: AI explains a topic. Levels: `1`, `5`, `10`, `engineer`.
- `$obsessions`: Analyze recent chat history to find trending server topics.
- `$hello`: Get a witty, AI-generated greeting.
- `$reloadidentity`: Reload bot identity from `data/identity.md` (Admin only).

> Note: Mention or reply to TaskForge in chat to trigger the AI assistant outside of commands.

### 🎧 Music & AI DJ

- `$dj <request>`: TaskForge AI generates and queues a themed playlist based on your prompt.
- `$play <search/url>`: Play a song from YouTube or add it to the queue.
- `$pause` / `$resume`: Control playback.
- `$skip`: Skip the current track.
- `$queue`: View the upcoming tracklist.
- `$clear` / `$stop`: Clear the queue and stop playback.

### 💰 Economy

- `$balance [member]` (alias: `$bal`): View wallet, bank, level, and XP.
- `$deposit <amount>` (alias: `$dep`): Deposit coins into your bank.
- `$withdraw <amount>` (alias: `$with`): Withdraw coins from your bank.
- `$inventory [member]` (alias: `$inv`): View a user's inventory.
- `$shop [item_id]`: Browse available shop items or view a specific item.
- `$buy <item_id> [quantity]`: Purchase items from the shop.
- `$sell <item_id> [quantity]`: Sell items from your inventory.
- `$daily`: Claim your daily reward and streak bonuses.
- `$reset_economy economy` (Admin only): Reset the economy database.

> Economy rewards are also earned passively by sending messages and spending time in voice channels.

### 🛡️ Moderation (Admin Only)

- `$purge <amount>`: Fast message cleanup (max 100).
- `$kick <member> [reason]`: Kick a member.
- `$ban <member> [reason]`: Ban a member.
- `$warn <member> [reason]`: Warn a member and log the warning.
- `$lock`: Lock the current channel.
- `$unlock`: Unlock the current channel.
- `$maintenance on [message]`: Enable maintenance mode with an optional notice.
- `$maintenance off`: Disable maintenance mode.
- `$maintenance status`: Show current maintenance mode status.

### 📣 Announcements

- `$announce <version> <type> <message>`: Create and post an announcement in the configured announcement channel (Owner only).
- `$latest`: Display the latest saved release announcement.

### ⏰ Reminders & Productivity

- `$reminder <time> <message>`: Personal reminder (e.g., `$reminder 30m Take a break`).
- `$vcreminder <time> <message>`: Alert everyone in your current voice channel.
- `$vcmembers`: List members in your current voice channel.

### 🛠️ Utilities & Voice

- `$ping`: Check API & WebSocket latency with humorous diagnostics.
- `$stats`: View technical environment stats (RAM, CPU, Uptime).
- `$roll`: Roll a standard 6-sided dice.
- `$vcstat`: Show connection and voice channel stats.
- `$setupguide`: Display setup instructions and environment tips.
- `$help`: Show available commands and usage information.

### 📊 Activity Leaderboards

- `$leaderboard messages` (alias: `$lb msg`): View the top 10 most active chatters.
- `$leaderboard vc`: See who has spent the most time in voice channels.
- `$leaderboard commands` (alias: `$lb cmds`): Track the most active bot command users.
- `$leaderboard channels`: Rank your server's channels by total message volume.
- `$leaderboard sync [limit]`: (Admin only) Scrape message history to populate stats. Use `0` for full history.

### 📩 Social & Fun

- `$confession <message>` (alias: `$confess`): Send an anonymous confession to the designated confession channel.

### ℹ️ Information

- `$about` (aliases: `bot`, `botinfo`): Comprehensive breakdown of TaskForge's mission and stats.
- `$me` (aliases: `profile`, `whoami`): Your detailed Discord profile with role listing and timestamps.
- `$server` (aliases: `serverinfo`, `guild`): Full server statistics, including member counts and channel breakdowns.
- `$credits` (aliases: `dev`, `whomadeyou`): Recognition of the bot's developers and project links.

---

## ⚙️ Installation & Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Mohit-Mano06/TaskForge-Bot.git
   ```

2. **Install dependencies**:

   TaskForge-Bot uses `uv` for lightning-fast dependency management.

   ```bash
   uv sync
   ```

   _Alternatively, if you don't have `uv`:_

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:

   Create a `.env` file in the root directory:

   ```env
   TOKEN=your_discord_bot_token
   MISTRAL_TOKEN=your_mistral_api_key
   USE_SUPABASE=True
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_key
   ```

4. **FFmpeg Setup**:

   Ensure `ffmpeg.exe` is in your system PATH or located in `cogs/music/ffmpeg/`.

5. **Run the Bot**:

   ```bash
   ./start.bat
   ```

---

_Developed with ❤️ by [Mohit](https://github.com/Mohit-Mano06)_
