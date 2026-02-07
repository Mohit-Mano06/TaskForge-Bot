import discord
from discord.ext import commands
import random 

import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TOKEN")




intents = discord.Intents.default()
intents.message_content = True


ALLOWED_CHANNEL_ID = 1469612261827022949

bot = commands.Bot(
    command_prefix="$", 
    intents=intents,
    help_command=None
    )
    

## ===== STARTUP ===== ##



@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(ALLOWED_CHANNEL_ID)
    if channel:
        await channel.send("🟢 **Bot is online**")

@bot.event
async def setup_hook():
    await bot.load_extension("cogs.social")
    await bot.load_extension("cogs.utility")
    await bot.load_extension("cogs.info")
    await bot.load_extension("cogs.hidden")





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

#===== ERROR HANDLING =====##

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