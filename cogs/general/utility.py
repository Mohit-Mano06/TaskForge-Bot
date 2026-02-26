import random
import datetime
import time
import discord
from discord.ext import commands

class Utility (commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(help = "Roll a dice")
    async def roll(self,ctx):
        await ctx.send(f"You rolled {random.randint(1,6)} 🎲")

    @commands.command(help="Tells your ping and runtime")
    async def ping(self, ctx): #Measure API ping-time
        start_time = time.monotonic()
        message = await ctx.send("🏓 Pinging...")
        api_latency = (time.monotonic() - start_time) * 1000
        websocket_latency = self.bot.latency * 1000

        if websocket_latency > 250:
            msg = "Just switch to 2g atp 😭"
        elif websocket_latency > 200: 
            msg = "You have shit ping 💀"
        elif websocket_latency < 100:
            msg = "Bro lives in the Wifi Router ⚡"
        else: 
            msg = "Ping is good stop whining"

        await message.edit(content=f"**API Latency:** {api_latency:.2f}ms\n**WebSocket Latency:** {websocket_latency:.2f}ms\n{msg}")

    @commands.command(help = "Shows bot uptime")
    async def uptime(self, ctx):
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time
        uptime = str(uptime).split('.')[0]
        await ctx.send(f"Current Uptime: {uptime}")

async def setup(bot):
    # Initialize start_time with timezone-aware datetime
    if not hasattr(bot, 'start_time'):
        bot.start_time = datetime.datetime.now(datetime.timezone.utc)
    await bot.add_cog(Utility(bot))
