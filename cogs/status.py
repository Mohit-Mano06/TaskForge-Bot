import discord
import random
import asyncio
from discord.ext import commands


class Status(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.status_cycle())

    async def status_cycle(self):
        await self.bot.wait_until_ready()

        statuses = [
            "Watching you type.....",
            "Stealing your RAM 💻",
            "Released before GTA VI 🎮",
            "Listening to your conversation 🤫",
            "Running on Python and Caffeine ☕",
            "Definetly not spying on you 👀",
            "Error 404: Code Not Found",
            "Trying to be Productive"
        ]

        while not self.bot.is_closed():
            status = random.choice(statuses)
            await self.bot.change_presence(activity=discord.Game(name=status))
            await asyncio.sleep(30)

async def setup(bot):
    await bot.add_cog(Status(bot))