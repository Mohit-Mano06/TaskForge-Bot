import random
import datetime
import time
from discord.ext import commands

class Utility (commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(help = "Roll a dice")
    async def roll(self,ctx):
        await ctx.send(f"You rolled {random.randint(1,6)} 🎲")

    @commands.command(help = "Tells your ping and runtime")
    async def ping(self,ctx):
        start_time = time.perf_counter()
        message = await ctx.send("Testing Ping...")
        end_time = time.perf_counter()
        
        runtime = (end_time - start_time) * 1000
        latency = round(self.bot.latency *1000)

        if latency > 250:
            msg = "Just switch to 2g atp 😭"
        elif latency > 200: 
            msg = "You have shit ping 💀"
        elif latency < 100:
            msg = "Bro lives in the Wifi Router ⚡"
        else: 
            msg = "Ping is good stop whining "

        await message.edit(content=f"**Server Runtime:** {runtime:.2f}ms\n**Bot Ping:** {latency}ms\n{msg}")

    @commands.command(help = "Shows bot uptime")
    async def uptime(self, ctx):
        uptime = datetime.datetime.utcnow() - self.bot.start_time
        uptime = str(uptime).split('.')[0]
        await ctx.send(f"Current Uptime: {uptime}")

async def setup(bot):
    await bot.add_cog(Utility(bot))
