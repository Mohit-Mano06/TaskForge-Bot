from discord.ext import commands

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(help = "Greets you")
    async def hello(self,ctx):
        print("hello command received")  # Debug
        await ctx.send("Hello 👋")


async def setup(bot):
    await bot.add_cog(Social(bot))