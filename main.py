import discord
from discord.ext import commands
import random 
from config import TOKEN

import os

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix="$", intents=intents,help_command=None)

@bot.event 
async def on_ready():
    print("Bot is online Mothafuckars")

## hidden.py LOADING ##
async def load_cogs():
    await bot.load_extension("cogs.hidden")

@bot.event
async def setup_hook():
    await load_cogs()

## === BOT ONLINE === ## 
@bot.event
async def on_ready():
    channel_id = 1469612261827022949
    channel = bot.get_channel(channel_id)

    if channel:
        await channel.send("🟢 **Bot is online**")
    print(f"Logged in as {bot.user}")





## === GENERAL COMMANDS === ##
## Hooks to other files in cogs ## 

@bot.event 
async def setup_hook():
    await bot.load_extension("cogs.social")
    await bot.load_extension("cogs.utility")
    await bot.load_extension("cogs.info")
    await bot.load_extension("cogs.hidden")


@bot.command(help="Shows list of available commands")
async def help(ctx):
    embed = discord.Embed(
        title="Bot Help",
        description="List of available commands",
        color=0x3498db
    )

    for command in bot.commands:

        if command.hidden: 
            continue

        embed.add_field(
            name=command.name,
            value=command.help or "No description",
            inline=False
            )
            
    await ctx.send(embed=embed)





# ==== TOKEN ==== #
bot.run(TOKEN)
TOKEN = os.getenv("DISCORD_TOKEN")