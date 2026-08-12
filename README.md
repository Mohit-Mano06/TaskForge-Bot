# TaskForge-Bot 🤖 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**TaskForge** is a high-performance, AI-powered Discord bot built with `discord.py`. It blends smart automation, server management, leaderboard tracking, music, and a rich economy system into one cohesive bot experience.

---

## 🌟 Key Features

### 🧠 AI & Assistant Experience

- **AI Chat Assistant**: Talk to TaskForge with `$chat` using the built-in Mistral integration.
- **AI Roast & Personality Modes**: Add fun bot interactions with `$roast` and AI-driven conversation replies.
- **Bot Identity & Context**: Uses a stored identity profile for engaging and consistent responses.
- **Server Intelligence**: Built to analyze activity and conversation trends for future AI-driven insights.

### 🎵 High-Fidelity Music Experience

- **Crystal Clear Audio**: YouTube streaming powered by `yt-dlp` and local `FFmpeg` processing for zero-lag playback.
- **Intelligent Queueing**: Full support for adding, skipping, pausing, and clearing track queues.
- **Voice Stats**: Monitor your voice connection quality in real-time with `$vcstat`.

### 📊 Server Leaderboards

- **Message, Voice, & Command Stats**: Track engagement across the server.
- **Channel Analysis**: See which channels are most active.
- **Leaderboard Commands**: Built to support quick ranking and historical syncs.

### 💰 Economy System

- **Wallet, Bank, XP, and Leveling**: Maintain user profiles and progression.
- **Daily Rewards**: Claim streak-based rewards with `$daily`.
- **Shop Catalog**: Browse items with paging, search, and filter support.
- **Item Types**: Support for collectibles and cosmetics.
- **Inventory Management**: View inventory and buy/sell game items.
- **Passive Economy Growth**: Add coins and XP through activity-based rewards.

### 🎁 Weekly Giveaway System

- **Entry Flow via Reaction**: Users join by reacting with 🎉 to the giveaway message.
- **IST Time Handling**: Timing is managed with Asia/Kolkata timezone awareness.
- **Reminder Before Close**: A reminder is sent before the entry window ends.
- **Winner Selection**: A random winner is chosen from the current participants.
- **Reward Handling**: Coins and item bonuses are awarded to the winner.
- **Profile-Aware Reward Delivery**: If a winner does not yet have an economy profile, the reward is held until they create one.

### 🛡️ Moderation & Server Control

- **Moderation Tools**: Purge, kick, ban, warn, lock, and unlock commands.
- **Maintenance Mode**: Quickly switch the bot into testing/maintenance mode.
- **Admin Access Control**: Permission checks are centralized for consistent owner/admin behavior.

---

## ℹ️ Bot Information

- **Library**: `discord.py`
- **Language**: Python 3.12+
- **AI Provider**: Mistral AI
- **Voice Engine**: FFmpeg + YouTube streaming support
- **Database**: PostgreSQL-ready economy and leaderboard storage

---

## 🛠️ Commands

All commands use the `$` prefix.

### 🤖 AI Assistant

- `$chat <message>`: Chat with the TaskForge AI assistant.
- `$talk <message>`: Short informal chat or quick witty response.
- `$roast [target or message]`: Roast someone or yourself.
- `$resetchat`: Clear your chat memory.
- `$reloadidentity`: Reload the bot identity from `data/identity.md` (Owner/admin only).

### 🎧 Music

- `$dj <request>`: Generate and queue a themed playlist.
- `$play <search/url>`: Play or queue a track.
- `$pause` / `$resume`: Control playback.
- `$skip`: Move to the next track.
- `$queue`: Show the queue.
- `$clear` / `$stop`: Clear or stop playback.

### 💰 Economy

- `$balance [member]` / `$bal`: View wallet, bank, level, and XP.
- `$deposit <amount>` / `$dep`: Move coins from wallet to bank.
- `$withdraw <amount>` / `$with`: Move coins from bank to wallet.
- `$inventory [member]` / `$inv`: View a user's inventory.
- `$shop [page|search|category]`: Browse items with pagination and search.
- `$buy <item_id> [quantity]`: Purchase an item.
- `$sell <item_id> [quantity]`: Sell an item.
- `$daily`: Claim your daily reward.
- `$reset_economy`: (Admin only) Reset economy data.

### 🎁 Giveaway

- `$giveaway start`: Start a giveaway in the current channel.
- `$giveaway status`: View current entries and timing details.
- `$giveaway reset`: Reset the active giveaway state.

> The giveaway system is designed for weekly usage and uses IST timing by default for scheduling and reminders.

### 🛡️ Moderation

- `$purge <amount>`: Delete a number of messages.
- `$kick <member> [reason]`: Kick a member.
- `$ban <member> [reason]`: Ban a member.
- `$warn <member> [reason]`: Warn a member.
- `$lock`: Lock the current channel.
- `$unlock`: Unlock the current channel.
- `$maintenance on [message]`: Enable maintenance mode.
- `$maintenance off`: Disable maintenance mode.
- `$maintenance status`: Show the status of maintenance mode.

### 📣 Announcements

- `$announce <version> <type> <message>`: Publish a release or update announcement.
- `$latest`: View the latest saved announcement.

### ⏰ Productivity & Utilities

- `$reminder <time> <message>`: Set a reminder.
- `$vcmembers`: View members in the current voice channel.
- `$ping`: Check latency.
- `$stats`: Show system stats.
- `$roll`: Roll a die.
- `$vcstat`: Show voice connection information.
- `$setupguide`: Show setup instructions.
- `$help`: Show command help.

### 📊 Leaderboards

- `$leaderboard messages` / `$lb msg`: Top message senders.
- `$leaderboard vc`: Top voice activity users.
- `$leaderboard commands` / `$lb cmds`: Most active command users.
- `$leaderboard channels`: Most active channels.
- `$leaderboard sync [limit]`: Pull in leaderboard history.

### 📩 Social

- `$confession <message>` / `$confess`: Send an anonymous confession.

### ℹ️ Information

- `$about` / `$botinfo`: Show bot info.
- `$me` / `$profile` / `$whoami`: View user profile details.
- `$server` / `$serverinfo` / `$guild`: Show server stats.
- `$credits`: See project credits and contributors.

---

## ⚙️ Installation & Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Mohit-Mano06/TaskForge-Bot.git
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   Or with `uv`:

   ```bash
   uv sync
   ```

3. **Create a `.env` file**:

   ```env
   TOKEN=your_discord_bot_token
   MISTRAL_TOKEN=your_mistral_api_key
   DATABASE_URL=your_postgres_connection_string
   USE_SUPABASE=True
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_key
   ```

4. **Set up FFmpeg**:

   Ensure `ffmpeg.exe` is in your system PATH or inside the repo's `cogs/music/ffmpeg/` folder.

5. **Run the bot**:

   ```bash
   ./start.bat
   ```

---

## 🧩 Notes

- The economy system uses a PostgreSQL-backed profile model.
- Shop items are driven by `data/economy_config.json` and are easy to extend.
- Giveaway values and timing can be edited centrally in the giveaway module.
- Owner/admin access checks are centralized for easier maintenance.

---

_Developed with ❤️ by [Mohit](https://github.com/Mohit-Mano06)_
