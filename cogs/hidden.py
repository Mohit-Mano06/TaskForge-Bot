import discord 
from discord.ext import commands


## === ADMIN COMMANDS FOR MAINTENANCE === ##

class Hidden(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(hidden=True)
    async def downtime(self,ctx):
        await ctx.message.delete()

        await ctx.send("🔴 **Bot is offline**")

async def setup(bot):
    await bot.add_cog(Hidden(bot))