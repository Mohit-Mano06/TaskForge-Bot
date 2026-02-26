import discord
import random
from discord.ext import commands

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help = "Shows creator of the bot")
    async def whomadeyou(self, ctx):
        await ctx.send("I was made by Momo ;) ")

    @commands.command(help = "Shows info about the bot")
    async def whoareyou(self, ctx):
        await ctx.send("Am a simple discord bot created by Momo")

    @commands.command(help = "Shows information about bot")
    async def botinfo(self, ctx):
        embed = discord.Embed(
            title="Bot Info",
            color=discord.Color.blue()
        )
        embed.add_field(name="Library", value="discord.py", inline=True)
        embed.add_field(name="Total Commands", value=len(self.bot.commands), inline=True)

        await ctx.send(embed=embed)
    @commands.command(help = "Shows info about you")
    async def whoami(self,ctx):
        user = ctx.author


        msg = (
            f"Username: {user.name}\n"
            f"ID: {user.id}\n"
            f"Joined at: {user.joined_at}\n"
            f"Avatar URL: {user.display_avatar.url}\n"
            )

        await ctx.send(msg)

        
async def setup(bot):
    await bot.add_cog(Info(bot))
