import random
from discord.ext import commands

class Utility (commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(help = "Roll a dice")
    async def roll(ctx):
        await ctx.send(f"You rolled {random.randint(1,6)} 🎲")


    @commands.command(help = "Tells your ping")
async def ping(ctx):

    ping = round(bot.latency *1000)

    if ping > 250:
        msg = "Just switch to 2g atp 😭"
    elif ping > 200: 
        msg = "You have shit ping 💀"
    elif ping < 100:
        msg = "Bro lives in the Wifi Router ⚡"
    else: 
        msg = "Ping is good stop whining "

    await ctx.send(f"{ping}ms - {msg}")

async def setup(bot):
    await bot.add_cog(Utility(bot))
