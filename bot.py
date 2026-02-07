import discord
from discord.ext import commands
import random 
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix="$", intents=intents,help_command=None)


@bot.event 
async def on_ready():
    print("Bot is online Mothafuckars")

@bot.command(help = "Greets you")
async def hello(ctx):
    print("hello command received")  # Debug
    await ctx.send("Hello 👋")

@bot.command(help = "Roll a dice")
async def roll(ctx):
    await ctx.send(f"You rolled {random.randint(1,6)} 🎲")

@bot.command(help = "Shows info about you")
async def me(ctx):
    user = ctx.author


    msg = (
        f"Username: {user.name}\n"
        f"ID: {user.id}\n"
        f"Joined at: {user.joined_at}\n"
        f"Avatar URL: {user.display_avatar.url}\n"
    )

    await ctx.send(msg)

@bot.command(help = "Shows creator of the bot")
async def whomadeyou(ctx):
    await ctx.send("I was made by Momo ;) ")

@bot.command(help = "Shows info about the bot")
async def whoareyou(ctx):
    await ctx.send("Am a simple discord bot created by Momo")

@bot.command(help = "Shows Github Repo link for development")
async def botinfo(ctx):
    await ctx.send("Github Repo link for development : https://github.com/Mohit-Mano06/NewBot.git")

@bot.command(help = "Tells your ping")
async def ping(ctx):

    ping = round(bot.latency *1000)

    if ping > 250:
        msg = "Just switch to 2g atp 😭"
    elif ping > 200: 
        msg = "You have shit ping 💀"
    elif ping < 100:
        msg = "Bro lives in the Wifi Router ⚡"
    else: 
        msg = "Ping is good stop whining "

    await ctx.send(f"{ping}ms - {msg}")

@bot.command(help="Shows list of available commands")
async def help(ctx):
    embed = discord.Embed(
        title="Bot Help",
        description="List of available commands",
        color=0x3498db
    )

    for command in bot.commands:
        embed.add_field(name=command.name, value=command.help or "No description", inline=False)
    await ctx.send(embed=embed)

bot.run(TOKEN)