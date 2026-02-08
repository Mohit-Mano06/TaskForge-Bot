import discord 
from discord.ext import commands, tasks
import json
import os 
import time

#TODO: FIX THE TIME DELAY OF ~2 SECONDS by reducing calculation time here somehow idk

REMINDER_FILE = "data/reminder.json"


# Checking for json file and reading reminders file 
def load_reminders():
    if not os.path.exists(REMINDER_FILE):
        return {"reminders": []}
    
    with open(REMINDER_FILE, "r") as f:
        return json.load(f)


# Saving reminders in json file
def save_reminders(data):
    with open(REMINDER_FILE, "w") as f:json.dump(data, f, indent=4)


def parse_time(time_str):
    try: 
        amount = int(time_str[:-1])
        unit = time_str[-1]

        if unit == "s" or "S": return amount 
        elif unit == "m" or "M": return amount * 60
        elif unit == "h" or "H": return amount * 3600
        elif unit == "d" or "D": return amount * 86400
        else: return None
    except: 
        return None 

# Creating Reminder COG 

class Reminder(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.check_reminders.start()

    @commands.command()
    async def reminder(self,ctx, time_input: str, *, message: str):
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
            "message":message,
            "trigger_time":trigger_time,
            "status": "pending"
        }

        data["reminders"].append(reminder)
        save_reminders(data)

        await ctx.send(f"⏰ Reminder set for `{time_input}`: **{message}**")
    


    @tasks.loop(seconds = 1)
    async def check_reminders(self):
        data = load_reminders()
        now = int(time.time())
        updated = False


        for reminder in data["reminders"]:
            if reminder["status"] == "pending" and reminder["trigger_time"] <= now:
                channel = self.bot.get_channel(reminder["channel_id"])

                if channel: 
                    await channel.send( f"⏰ <@{reminder['user_id']}> Reminder:\n**{reminder['message']}**")

                reminder["status"] = "done"
                updated = True
        
        if updated:
            save_reminders(data)
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Reminder(bot))
