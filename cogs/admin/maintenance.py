import discord
from discord.ext import commands
import database
from cogs.admin.config import OWNER_ID

def is_owner_or_dev():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        return await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)

class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="maintenance", aliases=["maint"], invoke_without_command=True)
    async def maintenance(self, ctx):
        """Controls maintenance/testing mode"""
        await ctx.send("❓ Use `$maintenance on [message]`, `$maintenance off`, or `$maintenance status`.")

    @maintenance.command(name="on")
    @is_owner_or_dev()
    async def maintenance_on(self, ctx, *, message: str = None):
        """Enables maintenance mode"""
        self.bot.maintenance_enabled = True
        msg = message or "TaskForge is currently undergoing testing/maintenance."
        self.bot.maintenance_message = msg
        
        await database.save_maintenance({
            "enabled": True,
            "message": msg
        })
        
        # Change presence immediately
        await self.bot.change_presence(activity=discord.Game(name="🛠️ Testing TaskForge"))
        
        await ctx.send(f"🛠️ **TaskForge Maintenance Mode enabled.**\nMessage: `{msg}`\nNormal user commands are now disabled.")

    @maintenance.command(name="off")
    @is_owner_or_dev()
    async def maintenance_off(self, ctx):
        """Disables maintenance mode"""
        self.bot.maintenance_enabled = False
        
        await database.save_maintenance({
            "enabled": False,
            "message": self.bot.maintenance_message
        })
        
        # Restore normal presence immediately
        await self.bot.change_presence(activity=discord.Game(name="Watching you type....."))
        
        await ctx.send("✅ **TaskForge Maintenance Mode disabled.**\nTaskForge is back online.")

    @maintenance.command(name="status")
    async def maintenance_status(self, ctx):
        """Checks the current maintenance mode status"""
        enabled = getattr(self.bot, 'maintenance_enabled', False)
        msg = getattr(self.bot, 'maintenance_message', "TaskForge is currently undergoing testing/maintenance.")
        if enabled:
            await ctx.send(f"🛠️ **Maintenance Mode: ENABLED**\nMode: Testing\nMessage: `{msg}`")
        else:
            await ctx.send("🟢 **Maintenance Mode: DISABLED**\nMode: Online")

async def setup(bot):
    await bot.add_cog(Maintenance(bot))
