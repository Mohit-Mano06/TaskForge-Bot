import discord
from discord.ext import commands
import asyncio


CONFESSION_CHANNEL_ID = 1096519690068688926


class Confession(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="confession", aliases=["confess"])
    # @commands.cooldown(1, 300, commands.BucketType.user)
    async def confess(self, ctx: commands.Context, *, message=None):
        if not message: 
            await ctx.send("Please provide a confession message.", delete_after=5)
            return 
        
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            return
        
        await asyncio.sleep(3)

        channel = self.bot.get_channel(CONFESSION_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="📩 Anonymous Confession",
            description="Confession by Anonymous member\n" + message,
            color=discord.Color.dark_purple()
        )

        embed.set_footer(text="End of Confession")

        await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Confession(bot))
