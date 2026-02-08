import discord
from discord.ext import commands
import datetime

#Logging bot commands
from logger import send_log 

import os

# Load environment variables & error handling for token/env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded .env file")
    print(f"Current directory: {os.getcwd()}")
    print(f".env file exists: {os.path.exists('.env')}")
except ImportError:
    print("TRY AGAIN PLEASE.")

TOKEN = os.getenv("TOKEN")
print(f"Token retrieved: {'Yes' if TOKEN else 'No'}")
print(f"Token length: {len(TOKEN) if TOKEN else 'N/A'}")
print("Loading virtual environment for hosting the bot locally.")
print("Token may have been received, but the venv might've not loaded in yet. Try again!")

# Check if TOKEN exists
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found! Check your .env file or environment variables")

intents = discord.Intents.default()
intents.message_content = True

#Anime Server channel id (#custom-bot)
ALLOWED_CHANNEL_ID = 1469612261827022949

bot = commands.Bot(
    command_prefix="$", 
    intents=intents,
    help_command=None
)

## ===== STARTUP ===== ##

@bot.event
async def on_ready():
    if not hasattr(bot, 'start_time'):
        bot.start_time = datetime.datetime.now(datetime.timezone.utc)
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(ALLOWED_CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=10):
            if message.author == bot.user and "Bot is online" in message.content:
                await message.delete()

        await channel.send("🟢 **Bot is online**")

    await send_log(bot, "🟢 **Bot is online** (Log Channel Message)")

@bot.event
async def setup_hook():
    await bot.load_extension("cogs.social")
    await bot.load_extension("cogs.utility")
    await bot.load_extension("cogs.info")
    await bot.load_extension("cogs.hidden")
    await bot.load_extension("cogs.reminder.reminder")

## ===== HELP ===== ##

@bot.command(help="Shows list of available commands")
async def help(ctx):
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return  # 🔕 silent outside channel

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

## ===== ERROR HANDLING ===== ##

@bot.event
async def on_command_error(ctx, error):
    # 🔕 stay silent everywhere except allowed channel
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return

    # ignore unknown commands
    if isinstance(error, commands.CommandNotFound):
        return

    # ignore permission errors
    if isinstance(error, commands.CheckFailure):
        return

    raise error  # real bugs only

## ==== TOKEN ==== ##
bot.run(TOKEN)
