# TaskForge-Bot🤖

A high-performance Discord bot built with Python and `discord.py`, developed by **Momo** (Mohit & Anis). This bot handles everything from server utilities to high-quality music playback.

## Features ✨

- **Music Player**: High-fidelity YouTube streaming with queue support and local FFmpeg processing.
- **Reminders**: Set personal or voice channel-wide reminders with natural time formats.
- **Utilities**: Advanced latency monitoring, dice rolling, and uptime tracking.
- **Information**: Detailed bot statistics and user profile lookups.
- **Voice Tools**: Connect to voice channels and monitor connection stats.

## Bot Information ℹ️

- **Developers**: Momo ([Mohit](https://github.com/Mohit-Mano06) & [Anis](https://github.com/atshayk))
- **Library**: discord.py
- **Language**: Python 3.12+
- **Audio Engine**: FFmpeg (Local binary supported)

## Commands 🛠️

The bot uses the `$` prefix for all commands.

### 🎵 Music (New!)

- `$play <search/url>`: Plays a song from YouTube or adds it to the queue.
- `$pause`: Pauses the current track.
- `$resume`: Resumes the paused track.
- `$skip`: Skips to the next song in the queue.
- `$stop`: Stops the music and clears the queue.
- `$queue`: Shows the current upcoming tracks.

### ⏰ Reminders

- `$reminder <time> <message>`: Set a personal reminder (e.g., `$reminder 10m Coffee break`).
- `$vcreminder <time> <message>`: Remind everyone in your current voice channel.
- `$vcmembers`: Quick list of everyone currently in your voice channel.

### 🛠️ Utilities

- `$ping`: Advanced latency check (API & WebSocket response times).
- `$uptime`: Check how long the bot has been live.
- `$roll`: Roll a standard 6-sided dice.

### ℹ️ Information

- `$botinfo`: Technical stats about the bot's environment and command count.
- `$whoami`: Display your Discord profile details (ID, Join Date, Avatar).
- `$whomadeyou`: Credits for the bot's creators.
- `$whoareyou`: A brief intro to the bot's purpose.

### 🔊 Voice

- `$connect`: Bring the bot into your voice channel.
- `$disconnect`: Make the bot leave voice.
- `$vcstat`: Check voice connection quality and member stats.

## Installation & Setup ⚙️

1. **Clone the repo**:

   ```bash
   git clone https://github.com/Mohit-Mano06/TaskForge-Bot.git
   ```

2. **Install requirements**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure FFmpeg**:

   Place your `ffmpeg.exe` in `cogs/music/ffmpeg/` or ensure it's in your system PATH.

4. **Environment Variables**:

   Create a `.env` file with your `TOKEN`.

5. **Run the bot**:

   ```bash
   ./start.bat
   ```

