import discord
import os
from discord.ext import commands
from mistralai.client import Mistral

TAMABOT_ID = 870295323401125948


class AIBattle(commands.Cog):

    def __init__(self, bot, mistral_client):
        self.bot = bot
        self.mistral = mistral_client

    @commands.command(name="battle")
    async def battle(self, ctx):

        # Trigger Tamabot
        await ctx.send(">ask Roast the discord bot TaskForge")

        def check(m):
            return m.author.id == TAMABOT_ID and m.channel == ctx.channel

        try:
            tamabot_reply = await self.bot.wait_for("message", check=check, timeout=20)
        except:
            return await ctx.send("Tamabot didn't respond.")

        from .roast import generate_roast

        reply = await generate_roast(self.mistral, tamabot_reply.content)

        await ctx.send(reply)


async def setup(bot):
    mistral_client = Mistral(api_key=os.getenv("MISTRAL_TOKEN"))
    await bot.add_cog(AIBattle(bot, mistral_client))