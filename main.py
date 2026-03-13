import discord
from discord.ext import commands
import datetime
import asyncio
import sys


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
print(f"Virtual environment: {'VEnv active' if TOKEN else 'Click run again to load venv properly.'}")

MISTRAL_API_KEY = os.getenv("MISTRAL_TOKEN")
print(f"Mistral Token retrieved: {'Yes' if MISTRAL_API_KEY else 'No'}")
print(f"Token length: {len(MISTRAL_API_KEY) if MISTRAL_API_KEY else 'N/A'}")
print(f"Virtual environment: {'VEnv active' if MISTRAL_API_KEY else 'Click run again to load venv properly.'}")


# Check if TOKEN exists
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found! Check your .env file or environment variables")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

#Anime Server channel id (#custom-bot)
ALLOWED_CHANNEL_ID = 1469612261827022949

class TaskForgeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="$",
            intents=intents,
            help_command=None
        )

    async def close(self):
        print("Shutting down bot...")
        channel = self.get_channel(ALLOWED_CHANNEL_ID)
        if channel:
            try:
                await channel.send("🔴 **Bot is offline**")
            except Exception as e:
                print(f"Error sending shutdown message to channel: {e}")
        
        try:
            from logger import send_log
            await send_log(self, "🔴 **Bot is offline** (Log Channel Message)")
        except Exception as e:
            print(f"Error sending shutdown message to logs: {e}")

        await super().close()

bot = TaskForgeBot()

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


# ===== COGS ===== # (For loading cogs and commands)
@bot.event
async def setup_hook():
    await bot.load_extension("cogs.general.social")
    await bot.load_extension("cogs.general.utility")
    await bot.load_extension("cogs.general.info")
    await bot.load_extension("cogs.admin.hidden")
    await bot.load_extension("cogs.reminder.reminder")
    await bot.load_extension("cogs.reminder.vcreminder")
    await bot.load_extension("cogs.music.music_player")
    await bot.load_extension("cogs.admin.moderation")
    await bot.load_extension("cogs.confession")
    await bot.load_extension("cogs.announcement")
    await bot.load_extension("cogs.setupguide")
    await bot.load_extension("cogs.mistral.ai")
    await bot.load_extension("cogs.mistral.bot_chat.ai_battle")
## ===== HELP ===== ##

@bot.command(help="Shows list of available commands")
async def help(ctx):
    embed = discord.Embed(
        title="Bot Help",
        description="List of available commands grouped by category",
        color=0x3498db
    )

    # Group commands by Cog
    cog_commands = {}
    for command in bot.commands:
        if command.hidden:
            continue
        
        cog_name = command.cog.qualified_name if command.cog else "General"
        if cog_name not in cog_commands:
            cog_commands[cog_name] = []
        cog_commands[cog_name].append(f"`{command.name}`")

    # Add fields to embed for each Cog
    for cog_name, commands_list in cog_commands.items():
        embed.add_field(
            name=cog_name,
            value=", ".join(commands_list),
            inline=False
        )

    await ctx.send(embed=embed)

## ===== ERROR HANDLING ===== ##

@bot.event
async def on_command_error(ctx, error):
    # Print the error to console
    import traceback
    traceback.print_exception(type(error), error, error.__traceback__)

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
    
@bot.command(name="sync", hidden=True)
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")
    except Exception as e:
        await ctx.send(f"Error syncing: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f}s", ephemeral=True)
    elif isinstance(error, discord.app_commands.CheckFailure):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        print(f"Interaction error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
        else:
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)


## ==== TOKEN ==== ##
bot.run(TOKEN)
