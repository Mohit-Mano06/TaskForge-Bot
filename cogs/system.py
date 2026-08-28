import asyncio
import json
import os
from pathlib import Path
from discord.ext import commands
import discord

from cogs.monitoring.metrics import collect_health_snapshot



class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watch_tasks = {}
        self.watch_state_path = Path("data/health_watch.json")

    async def cog_load(self):
        for guild_id, watch in self._load_watch_state().items():
            self.watch_tasks[int(guild_id)] = asyncio.create_task(
                self._watch_loop(int(guild_id), int(watch["channel_id"]), int(watch["message_id"]))
            )

    async def cog_unload(self):
        for task in self.watch_tasks.values():
            task.cancel()
        self.watch_tasks.clear()

    async def _is_admin_or_owner(self, ctx):
        return bool(ctx.author.guild_permissions.administrator or await self.bot.is_owner(ctx.author))

    @staticmethod
    def _format_uptime(seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    async def _health_embed(self):
        snapshot = await collect_health_snapshot(self.bot)
        colors = {"healthy": discord.Color.green(), "degraded": discord.Color.orange(), "unhealthy": discord.Color.red()}
        embed = discord.Embed(title="TaskForge Health", color=colors[snapshot.overall_status], timestamp=snapshot.checked_at)
        embed.add_field(name="Discord", value=f"{'Connected' if snapshot.discord_ready else 'Disconnected'}\n{snapshot.discord_latency_ms:.0f} ms", inline=True)
        embed.add_field(name="PostgreSQL", value=snapshot.database_status, inline=True)
        embed.add_field(name="Supabase", value=snapshot.supabase_status, inline=True)
        embed.add_field(name="Mistral", value="Configured" if snapshot.mistral_configured else "Not configured", inline=True)
        embed.add_field(name="CPU", value=f"{snapshot.cpu_percent:.1f}%", inline=True)
        embed.add_field(name="Memory", value=f"{snapshot.memory_mb:.1f} MB", inline=True)
        embed.add_field(name="Disk", value=f"{snapshot.disk_percent:.1f}%", inline=True)
        embed.add_field(name="Uptime", value=self._format_uptime(snapshot.uptime_seconds), inline=True)
        embed.set_footer(text=f"Last checked: {snapshot.checked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        return embed

    def _load_watch_state(self):
        try:
            return json.loads(self.watch_state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_watch_state(self, state):
        self.watch_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.watch_state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    async def _watch_loop(self, guild_id, channel_id, message_id):
        try:
            while True:
                await asyncio.sleep(int(os.getenv("HEALTH_WATCH_INTERVAL", "60")))
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    continue
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=await self._health_embed())
                except discord.NotFound:
                    message = await channel.send(embed=await self._health_embed())
                    state = self._load_watch_state()
                    state[str(guild_id)] = {"channel_id": channel_id, "message_id": message.id}
                    self._save_watch_state(state)
                    message_id = message.id
        except asyncio.CancelledError:
            return


    @commands.command(help="Show a full TaskForge health report")
    async def health(self, ctx, action=None):
        """Show health status for the bot and its dependencies."""
        if action in {"watch", "stop"} and ctx.guild is None:
            await ctx.send("Health monitoring can only be managed inside a server.")
            return
        if action in {"watch", "stop"} and not await self._is_admin_or_owner(ctx):
            await ctx.send("You need administrator permissions to manage health monitoring.")
            return
        if action == "stop":
            task = self.watch_tasks.pop(ctx.guild.id, None)
            if task:
                task.cancel()
            state = self._load_watch_state()
            state.pop(str(ctx.guild.id), None)
            self._save_watch_state(state)
            await ctx.send("Health monitoring stopped.")
            return
        embed = await self._health_embed()
        if action != "watch":
            await ctx.send(embed=embed)
            return
        state = self._load_watch_state()
        existing = state.get(str(ctx.guild.id), {})
        message = None
        if existing.get("channel_id") == ctx.channel.id:
            try:
                message = await ctx.channel.fetch_message(existing["message_id"])
                await message.edit(embed=embed)
            except discord.NotFound:
                message = None
        if message is None:
            message = await ctx.send(embed=embed)
        state[str(ctx.guild.id)] = {"channel_id": ctx.channel.id, "message_id": message.id}
        self._save_watch_state(state)
        old_task = self.watch_tasks.pop(ctx.guild.id, None)
        if old_task:
            old_task.cancel()
        self.watch_tasks[ctx.guild.id] = asyncio.create_task(self._watch_loop(ctx.guild.id, ctx.channel.id, message.id))
        await ctx.send("Health watch enabled.", delete_after=5)

async def setup(bot):
    await bot.add_cog(System(bot))