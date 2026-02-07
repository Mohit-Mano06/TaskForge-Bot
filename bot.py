import discord
from discord.ext import commands
import random 
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event 
async def on_ready():
    print("Bot is online Mothafuckars")

@bot.command()
async def hello(ctx):
    print("hello command received")  # Debug
    await ctx.send("Hello 👋")

@bot.command()
async def roll(ctx):
    await ctx.send(f"You rolled {random.randint(1,6)} 🎲")

@bot.command()
async def me(ctx):
    user = ctx.author


    msg = (
        f"Username: {user.name}\n"
        f"ID: {user.id}\n"
        f"Joined at: {user.joined_at}\n"
        f"Avatar URL: {user.avatar}\n"
    )

    await ctx.send(msg)

@bot.command()
async def whomadeyou(ctx):
    await ctx.send("I was made by Momo ;) ")

@bot.command()
async def whoareyou(ctx):
    await ctx.send("Am a simple discord bot created by Momo")

@bot.command()
async def botinfo(ctx):
    await ctx.send("Github Repo link for development : ")



bot.run(TOKEN)