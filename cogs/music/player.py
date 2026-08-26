import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
import json
import wavelink


# FFmpeg: auto-detect system binary (Linux/Ubuntu) or local exe (Windows)
current_dir = os.path.dirname(os.path.abspath(__file__))
_local_ffmpeg = os.path.join(current_dir, "ffmpeg", "ffmpeg.exe")
FFMPEG_EXE_PATH = _local_ffmpeg if os.path.isfile(_local_ffmpeg) else "ffmpeg"

# cookies.txt: check project root first, then cogs/music/, skip if neither found
_project_root = os.path.dirname(os.path.dirname(current_dir))
_root_cookies = os.path.join(_project_root, "cookies.txt")
_local_cookies = os.path.join(current_dir, "cookies.txt")
if os.path.isfile(_root_cookies):
    COOKIES_PATH = _root_cookies
elif os.path.isfile(_local_cookies):
    COOKIES_PATH = _local_cookies
else:
    COOKIES_PATH = None

# YTDL Configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'default_search': 'auto',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
}

if COOKIES_PATH:
    ytdl_format_options['cookiefile'] = COOKIES_PATH

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2',
}


ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        # Use lambda to ensure extract_info is run in the executor thread
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist or search result
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        
        return cls(
            discord.FFmpegPCMAudio(
                filename, 
                executable=FFMPEG_EXE_PATH, 
                **ffmpeg_options
            ), 
            data=data
        )
    
class GuildPlayer:
    """A class which is assigned to each guild using the bot for Music."""
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'vc')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.vc = None
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Main player loop."""
        await self.bot.wait_until_ready()

        try:
            while not self.bot.is_closed():
                self.next.clear()

                try:
                    # Wait for the next song. If we timeout cancel the player and leave...
                    source = await asyncio.wait_for(self.queue.get(), timeout=300)  # 5 minutes idle timeout
                except asyncio.TimeoutError:
                    return self.destroy(self._guild)

                self.current = source
                print(f"[Player] Got source: {source.title}")

                # Wait up to 300 seconds (5 minutes) for the VC connection to finalize/reconnect
                wait_time = 0
                while wait_time < 300 and self.vc and not self.vc.is_connected():
                    if wait_time == 5:
                        print("[Player] Connection dropped natively. Waiting for discord.py to reconnect...")
                    await asyncio.sleep(1)
                    wait_time += 1

                if not self.vc or not self.vc.is_connected():
                    print("[Player] Not connected to VC after 5 minutes, destroying player.")
                    return self.destroy(self._guild)

                try:
                    def after_play(error):
                        if error:
                            print(f"[Player Error] Playback error: {error}")
                        # Always unblock the loop — even on error, or queue hangs forever
                        self.bot.loop.call_soon_threadsafe(self.next.set)

                    self.vc.play(source, after=after_play)
                except Exception as e:
                    import traceback
                    print(f"[Player Exception when calling play()] {e}")
                    traceback.print_exc()
                    self.next.set()  # unblock even on exception

                await self._channel.send(f"🎵 **Now playing:** `{source.title}`")

                await self.next.wait()

                source.cleanup()
                self.current = None
        except Exception as e:
            import traceback
            print(f"[Player Fatal Error] {e}")
            traceback.print_exc()
            self.destroy(self._guild)

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup_player(guild))


class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = GuildPlayer(ctx)
            player._cog = self  # Ensure it always belongs to MusicPlayer, even if invoked by AI DJ
            self.players[ctx.guild.id] = player
        return player

    @staticmethod
    def _lavalink_enabled():
        configured_backend = os.getenv("MUSIC_BACKEND")
        if not configured_backend:
            try:
                with open("data/music_config.json", "r", encoding="utf-8") as file:
                    configured_backend = json.load(file).get("backend", "ytdlp")
            except (OSError, json.JSONDecodeError):
                configured_backend = "ytdlp"
        return configured_backend.strip().lower() == "lavalink"

    async def _play_lavalink(self, ctx, search):
        if not getattr(self.bot, "lavalink_connected", False):
            return await ctx.send("❌ Lavalink is not connected. Set `MUSIC_BACKEND=ytdlp` or start Lavalink.")

        channel = ctx.author.voice.channel
        voice_client = ctx.voice_client
        if voice_client and not isinstance(voice_client, wavelink.Player):
            await voice_client.disconnect(force=True)
            voice_client = None
        if voice_client is None:
            voice_client = await channel.connect(cls=wavelink.Player)
        elif not voice_client.connected:
            await voice_client.connect(channel)
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        async with ctx.typing():
            tracks = await wavelink.Playable.search(search, source=wavelink.TrackSource.YouTube)
            if not tracks:
                return await ctx.send("❌ Lavalink could not find a playable track for that query.")
            track = tracks[0]
            await voice_client.play(track)

        await ctx.send(f"✅ Now playing: `{track.title}`")

    async def cleanup_player(self, guild):
        """Cleanup a single guild's player."""
        try:
            player = self.players.pop(guild.id)
            if player.vc:
                await player.vc.disconnect()
        except KeyError:
            pass

    @commands.command(name='play', help='Plays a song from YouTube')
    async def play(self, ctx, *, search: str):
        """Streams from a query (YouTube search or URL)."""
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel to play music!")

        if self._lavalink_enabled():
            try:
                return await self._play_lavalink(ctx, search)
            except Exception as e:
                print(f"[Lavalink Error] Play failed: {e}")
                return await ctx.send(f"❌ Lavalink could not play that track: `{e}`")

        player = self.get_player(ctx)

        try:
            if ctx.voice_client:
                if not ctx.voice_client.is_connected():
                    # Zombie connection detected, force disconnect first
                    await ctx.voice_client.disconnect(force=True)
                    player.vc = await ctx.author.voice.channel.connect(timeout=60.0)
                else:
                    player.vc = ctx.voice_client
            else:
                player.vc = await ctx.author.voice.channel.connect(timeout=60.0)
        except Exception as e:
            # Catches discord.errors.ClientException and TimeoutError
            print(f"[Player Error] VC Connect Exception: {e}")
            return await ctx.send(f"❌ Failed to join the voice channel: `{str(e)}`")

        async with ctx.typing():
            try:
                source = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
                await player.queue.put(source)
            except Exception as e:
                return await ctx.send(f"❌ An error occurred: {str(e)}")

        if player.vc.is_playing() or not player.queue.empty():
            if player.current != source:
                await ctx.send(f"✅ Added to queue: `{source.title}`")

    @commands.command(name='pause', help='Pauses the current song')
    async def pause(self, ctx):
        player = self.get_player(ctx)
        if player.vc and player.vc.is_playing():
            player.vc.pause()
            await ctx.send("⏸️ Paused.")

    @commands.command(name='resume', help='Resumes the current song')
    async def resume(self, ctx):
        player = self.get_player(ctx)
        if player.vc and player.vc.is_paused():
            player.vc.resume()
            await ctx.send("▶️ Resumed.")

    @commands.command(name='skip', help='Skips the current song')
    async def skip(self, ctx):
        player = self.get_player(ctx)
        if player.vc and player.vc.is_playing():
            player.vc.stop()
            await ctx.send("⏭️ Skipped.")

    @commands.command(name='stop', help='Stops music and leaves the VC')
    async def stop(self, ctx):
        if self._lavalink_enabled() and isinstance(ctx.voice_client, wavelink.Player):
            await ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            return await ctx.send("⏹️ Stopped and disconnected.")
        player = self.get_player(ctx)
        if player.vc:
            await self.cleanup_player(ctx.guild)
            await ctx.send("⏹️ Stopped and disconnected.")

    @commands.command(name='disconnect', aliases=['leave'], help='Leaves the voice channel')
    async def disconnect(self, ctx):
        if isinstance(ctx.voice_client, wavelink.Player):
            await ctx.voice_client.disconnect()
            return await ctx.send("👋 Disconnected from the voice channel.")
        if ctx.voice_client:
            await self.cleanup_player(ctx.guild)
            await ctx.send("👋 Disconnected from the voice channel.")

    @commands.command(name='queue', help='Shows the current music queue')
    async def queue_info(self, ctx):
        player = self.get_player(ctx)

        if not player.current and player.queue.empty():
            return await ctx.send("🎧 The queue is currently empty.")

        upcoming = list(player.queue._queue)

        msg = "╭─ 🎵 MUSIC QUEUE\n"
        msg += f"│ Now Playing: {player.current.title}\n" if player.current else "│ Now Playing: Nothing\n"
        msg += "│\n"

        if not upcoming:
            msg += "│ No upcoming songs.\n"
        else:
            msg += "│ Upcoming:\n"
            for i, song in enumerate(upcoming, 1):
                msg += f"│ {i}. {song.title}\n"

        msg += "╰────────────────────"
        await ctx.send(f"```\n{msg}\n```")

    @commands.command(name="clear", help="Clears the music queue")
    async def clear(self, ctx):
        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("Queue is already empty.")
        player.queue = asyncio.Queue()
        await ctx.send("🧹 Queue cleared.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates to cleanup players if bot is disconnected."""
        if member == self.bot.user and after.channel is None:
            if member.guild.id in self.players:
                await self.cleanup_player(member.guild)


async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))
