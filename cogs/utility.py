import random
from discord.ext import commands

class Utility (commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(help = "Roll a dice")
    async def roll(self,ctx):
        await ctx.send(f"You rolled {random.randint(1,6)} 🎲")

    @commands.command(help = "Tells your ping")
    async def ping(self,ctx):

        latency = round(self.bot.latency *1000)

        if latency > 250:
            msg = "Just switch to 2g atp 😭"
        elif latency > 200: 
            msg = "You have shit ping 💀"
        elif latency < 100:
            msg = "Bro lives in the Wifi Router ⚡"
        else: 
            msg = "Ping is good stop whining "

        await ctx.send(f"{latency}ms - {msg}")

async def setup(bot):
    await bot.add_cog(Utility(bot))
