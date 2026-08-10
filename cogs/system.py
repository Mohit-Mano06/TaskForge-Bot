import asyncio
import psutil
import os
import time
from discord.ext import commands



class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()


    @commands.command()
    async def stats(self, ctx):
        """Shows bot statistics"""
        
        process = psutil.Process(os.getpid())

        ram = process.memory_info().rss / (1024 ** 2)
        cpu = process.cpu_percent(interval = 1)
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            uptime_str = f"{hours}h {minutes}m"
        else:
            uptime_str = f"{minutes}m {seconds}s"

        await ctx.send(
            f"⚙️ **Bot Stats**\n"
            f"🧠 RAM: `{ram:.2f} MB`\n"
            f"💻 CPU: `{cpu}%`\n"
            f"⏱️ Uptime: `{uptime_str}`"
        )

    @commands.command(help="Show a full TaskForge health report")
    async def health(self, ctx):
        """Show health status for the bot and its dependencies."""
        process = psutil.Process(os.getpid())
        ram = process.memory_info().rss / (1024 ** 2)
        cpu = await asyncio.to_thread(process.cpu_percent, interval=1)
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_parts = []
        if hours:
            uptime_parts.append(f"{hours}h")
        if minutes or hours:
            uptime_parts.append(f"{minutes}m")
        uptime_parts.append(f"{seconds}s")
        uptime_str = " ".join(uptime_parts)

        discord_status = "Connected" if self.bot.is_ready() and not self.bot.is_closed() else "Disconnected"
        websocket_latency = self.bot.latency * 1000

        db_status = "Disabled"
        if getattr(self.bot, 'db_pool', None):
            db_status = "Connected"

        supabase_status = "Disabled"
        try:
            import database
            if database.USE_SUPABASE:
                supabase_ok = await database.check_supabase_connection()
                supabase_status = "Healthy" if supabase_ok else "Unreachable"
        except Exception:
            supabase_status = "Unreachable"

        mistral_status = "Configured" if getattr(self.bot, 'mistral_client', None) else "Not configured"

        disk_usage = psutil.disk_usage(os.getcwd())

        lines = [
            "🩺 **TaskForge Health Report**",
            f"Discord       {'✅' if discord_status == 'Connected' else '❌'} {discord_status}",
            f"Latency       {'✅' if websocket_latency < 250 else '⚠️'} {websocket_latency:.0f}ms",
            f"Database      {'✅' if db_status == 'Connected' else '❌'} {db_status}",
            f"Supabase      {'✅' if supabase_status == 'Healthy' else '⚠️'} {supabase_status}",
            f"Mistral API   {'✅' if mistral_status == 'Configured' else '❌'} {mistral_status}",
            f"CPU           {cpu:.0f}%",
            f"RAM           {ram:.0f} MB",
            f"Disk          {disk_usage.percent}%",
            f"Uptime        {uptime_str}",
        ]

        overall = "🟢 HEALTHY"
        if db_status != "Connected" or discord_status != "Connected" or supabase_status not in {"Disabled", "Healthy"} or mistral_status != "Configured":
            overall = "🟠 DEGRADED"
        if discord_status != "Connected" or db_status != "Connected":
            overall = "🔴 UNHEALTHY"

        await ctx.send("\n".join(lines) + f"\n\nOverall Status: {overall}")

async def setup(bot):
    await bot.add_cog(System(bot))