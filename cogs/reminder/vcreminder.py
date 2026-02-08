import discord 
from discord.ext import commands
import json
import os 
import time
from .reminder import load_reminders, save_reminders, parse_time

REMINDER_FILE = "data/reminder.json"

class VCReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Set a voice channel reminder")
    async def vcreminder(self, ctx, time_input: str, *, message: str):
        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.send("❌ You must be in a voice channel to set a VC reminder!")
            return

        seconds = parse_time(time_input)
        if seconds is None:
            await ctx.send("❌ Invalid Time Format. Use '10m', '2h', '4d'.")
            return
        
        trigger_time = int(time.time()) + seconds
        data = load_reminders()
        new_id = len(data["reminders"]) + 1

        reminder = {
            "id": new_id,
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "voice_channel_id": ctx.author.voice.channel.id,
            "message": message,
            "trigger_time": trigger_time,
            "status": "pending",
            "type": "voice"
        }

        data["reminders"].append(reminder)
        save_reminders(data)
        await ctx.send(f"⏰ VC Reminder set for `{time_input}` in {ctx.author.voice.channel.name}: **{message}**")

    @commands.command(help="List voice channel members")
    async def vcmembers(self, ctx):            
        vc_channel = ctx.author.voice.channel
        members = [member.display_name for member in vc_channel.members if not member.bot]
        
        if members:
            member_list = "\n".join(members)
            await ctx.send(f"👥 Members in {vc_channel.name}:\n{member_list}")
        else:
            await ctx.send(f"🔇 No members in {vc_channel.name}")

async def setup(bot):
    await bot.add_cog(VCReminder(bot))
