import discord 
from discord.ext import commands, tasks
import time
import database

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
        self.active_reminders = []
        self.check_reminders.start()

    @commands.command(help="Set a reminder (e.g., $reminder 10m Take a break)")
    async def reminder(self,ctx, time_input: str, *, message: str):
        seconds = parse_time(time_input)
        if seconds is None:
            await ctx.send("❌ Invalid Time Format. Use '10m', '2h', '4d'.")
            return
        
        trigger_time = int(time.time()) + seconds
        
        new_id = len(self.active_reminders) + 1

        reminder = {
            "id": new_id,
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "message":message,
            "trigger_time":trigger_time,
            "status": "pending"
        }

        self.active_reminders.append(reminder)
        await database.save_reminders(self.bot.db_pool, self.active_reminders)

        await ctx.send(f"⏰ Reminder set for `{time_input}`: **{message}**")
    


    @tasks.loop(seconds = 1)
    async def check_reminders(self):
        now = int(time.time())
        updated = False

        for reminder in self.active_reminders:
            if reminder["status"] == "pending" and reminder["trigger_time"] <= now:
                channel = self.bot.get_channel(reminder["channel_id"])

                if channel: 
                    await channel.send( f"⏰ <@{reminder['user_id']}> Reminder:\n**{reminder['message']}**")

                reminder["status"] = "done"
                updated = True
        
        if updated:
            self.active_reminders = [r for r in self.active_reminders if r["status"] != "done"]
            await database.save_reminders(self.bot.db_pool, self.active_reminders)
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
        self.active_reminders = await database.load_reminders(self.bot.db_pool)


async def setup(bot):
    await bot.add_cog(Reminder(bot))
