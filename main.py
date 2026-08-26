# TaskForge-Bot - Developed by Mohit
# GitHub: https://github.com/Mohit-Mano06/TaskForge-Bot
# License: MIT

import os
import sys
import time
import datetime
import asyncio
import traceback
import discord
from discord.ext import commands
from mistralai.client import Mistral

import database
import asyncpg
from logger import send_log
from bot_logger import log_print, RICH_ENABLED, rich_terminal
from cogs.admin.config import OWNER_IDS, DEV_GUILD_ID
from cogs.economy import db as economy_db

class MaintenanceModeActive(commands.CheckFailure):
    def __init__(self, message=None):
        super().__init__(message or "TaskForge is currently undergoing testing/maintenance.")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    log_print("Loaded .env file")
except ImportError:
    log_print("dotenv library not found. Ensure it is installed.", "warning")

TOKEN = os.getenv("TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_TOKEN")

# Diagnostic logging
log_print(f"Token retrieved: {'Yes' if TOKEN else 'No'}")
log_print(f"Mistral Token retrieved: {'Yes' if MISTRAL_API_KEY else 'No'}")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found! Check your .env file or environment variables")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
log_print("Intents configured.")

ALLOWED_CHANNEL_ID = 1469612261827022949

class TaskForgeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="$",
            intents=intents,
            help_command=None
        )
        self.mistral_client = Mistral(api_key=MISTRAL_API_KEY)

    async def close(self):
        log_print("Shutting down bot...")
        channel = self.get_channel(ALLOWED_CHANNEL_ID)
        if channel:
            try:
                async for message in channel.history(limit=10):
                    if message.author == self.user and "Bot is offline" in message.content:
                        await message.delete()
                await channel.send("🔴 **Bot is offline**")
            except Exception as e:
                log_print(f"Error sending shutdown message: {e}", "error")
        
        try:
            await send_log(self, "🔴 **Bot is offline** (Log Channel Message)")
        except Exception as e:
            log_print(f"Error sending shutdown log: {e}", "error")

        if hasattr(self, 'db_pool') and self.db_pool:
            log_print("Closing database pool...")
            await self.db_pool.close()

        await super().close()

bot = TaskForgeBot()

@bot.event
async def on_ready():
    # Only run this once to avoid rate limits on reconnection
    if hasattr(bot, 'init_done'):
        log_print(f"Bot reconnected: {bot.user}")
        return
    
    bot.init_done = True
    if not hasattr(bot, 'start_time'):
        bot.start_time = datetime.datetime.now(datetime.timezone.utc)
    
    log_print(f"Logged in as {bot.user} (Initial Setup)", "success")

    channel = bot.get_channel(ALLOWED_CHANNEL_ID)
    if channel:
        try:
            async for message in channel.history(limit=10):
                if message.author == bot.user and "Bot is online" in message.content:
                    await message.delete()

            await channel.send("🟢 **Bot is online**")
        except Exception as e:
            log_print(f"Warning: Could not send startup message: {e}", "warning")

    try:
        await send_log(bot, "🟢 **Bot is online** (Log Channel Message)")
    except Exception as e:
        log_print(f"Warning: Could not send log message: {e}", "warning")
        
    if database.USE_SUPABASE:
        try:
            connected = await database.check_supabase_connection()
            if connected:
                log_print("✅ Supabase REST API connected", "success")
            else:
                log_print("❌ Supabase REST API failed to connect", "error")
        except Exception as e:
            log_print(f"❌ Supabase error: {e}", "error")

    # Set maintenance presence if enabled
    if getattr(bot, 'maintenance_enabled', False):
        await bot.change_presence(activity=discord.Game(name="🛠️ Testing TaskForge"))
        log_print("Applied maintenance presence.")

@bot.event
async def setup_hook():
    # Initialize database pool
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            bot.db_pool = await asyncpg.create_pool(dsn=db_url)
            await economy_db.ensure_economy_schema(bot.db_pool)
            log_print("✅ Connected to PostgreSQL database pool", "success")
        except Exception as e:
            log_print(f"❌ Failed to connect or migrate PostgreSQL database: {e}", "error")
            if not getattr(bot, 'db_pool', None):
                bot.db_pool = None
    else:
        log_print("⚠️ DATABASE_URL not found in environment. Economy commands will be disabled.", "warning")
        bot.db_pool = None

    # Load maintenance state
    try:
        maintenance_state = await database.load_maintenance()
        bot.maintenance_enabled = maintenance_state.get("enabled", False)
        bot.maintenance_message = maintenance_state.get("message", "TaskForge is currently undergoing testing/maintenance.")
        log_print(f"Loaded maintenance state: enabled={bot.maintenance_enabled}")
    except Exception as e:
        log_print(f"Error loading maintenance state in setup_hook: {e}", "error")
        bot.maintenance_enabled = False
        bot.maintenance_message = "TaskForge is currently undergoing testing/maintenance."

    extensions = [
        "cogs.utility.tools", "cogs.general.help", "cogs.general.info", "cogs.utility.reminder",
        "cogs.music.player", "cogs.admin.moderation",
        "cogs.admin.maintenance",
        "cogs.social.confession", "cogs.general.announcement", "cogs.general.guide",
        "cogs.music.dj", "cogs.ai.assistant", "cogs.ai.insights", "cogs.system", "cogs.general.status",
        "cogs.leaderboard.leaderboard_tracker",
        "cogs.leaderboard.leaderboard_commands",
        "cogs.economy.economy_cog",
        "cogs.economy.advanced",
        "cogs.economy.giveaway"
    ]
    
    if RICH_ENABLED:
        await rich_terminal.load_extensions_with_ui(bot, extensions)
    else:
        print("Starting setup_hook (loading extensions)...")
        for ext in extensions:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
        print("setup_hook complete.")



@bot.check
async def check_maintenance(ctx):
    if getattr(ctx.bot, 'maintenance_enabled', False):
        is_owner = (ctx.author.id in OWNER_IDS) or await ctx.bot.is_owner(ctx.author)
        if is_owner:
            return True
        if ctx.guild and ctx.guild.id == DEV_GUILD_ID:
            return True
        raise MaintenanceModeActive(getattr(ctx.bot, 'maintenance_message', None))
    return True

@bot.event
async def on_command_error(ctx, error):
    original = getattr(error, "original", error)
    if isinstance(original, MaintenanceModeActive):
        msg = str(original)
        await ctx.send(f"🛠️ **{msg}**\nSome features may be temporarily unavailable. Please try again later.")
        return
    if isinstance(original, commands.CommandNotFound):
        return
    if isinstance(original, commands.MissingRequiredArgument):
        command = ctx.command
        if command is None:
            return
        usage = command.usage or f"{ctx.prefix}{command.qualified_name} {command.signature}".strip()
        await ctx.send(
            f"❌ Missing `{original.param.name}`.\n"
            f"Try: `{usage}`\n"
            f"Type `{ctx.prefix}help {command.qualified_name}` for more examples."
        )
        return
    if isinstance(original, commands.BadArgument):
        command = ctx.command
        if command is None:
            return
        usage = command.usage or f"{ctx.prefix}{command.qualified_name} {command.signature}".strip()
        await ctx.send(
            f"❌ I could not understand that argument.\n"
            f"Try: `{usage}`\n"
            f"Type `{ctx.prefix}help {command.qualified_name}` for more details."
        )
        return
    if isinstance(original, commands.TooManyArguments):
        command = ctx.command
        if command is None:
            return
        usage = command.usage or f"{ctx.prefix}{command.qualified_name} {command.signature}".strip()
        await ctx.send(
            f"❌ Too many arguments were provided.\n"
            f"Try: `{usage}`\n"
            f"Type `{ctx.prefix}help {command.qualified_name}` for more details."
        )
        return
    if isinstance(error, commands.CheckFailure):
        return
    traceback.print_exception(type(error), error, error.__traceback__)
    raise error

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
        log_print(f"Interaction error: {error}", "error")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)


log_print("Waiting 3 seconds for system to settle...")
time.sleep(3)

log_print("Attempting to start bot.run()...")
try:
    bot.run(TOKEN)
except KeyboardInterrupt:
    log_print("\n[!] Manual shutdown detected.", "warning")
except Exception as e:
    log_print(f"FATAL ERROR during bot.run(): {e}", "error")
    if "1015" in str(e):
        log_print("💡 TIP: You are being rate limited by Cloudflare/Discord. Try restarting the service or waiting for sometime", "warning")
