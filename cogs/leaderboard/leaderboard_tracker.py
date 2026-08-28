import discord
from discord.ext import commands
import database
import time
from cogs.monitoring.metrics import taskforge_messages_seen_total, taskforge_vc_active_sessions

class LeaderboardTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_sessions = {}  # (guild_id, user_id): join_timestamp_seconds

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        taskforge_messages_seen_total.inc()
            
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        channel_id = str(message.channel.id)
        
        await database.update_leaderboard_stat(guild_id, user_id, "messages_count", 1)
        await database.update_channel_stat(guild_id, channel_id, 1)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return
            
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        session_key = (guild_id, user_id)
        
        # Joined a channel (was not in one before)
        if before.channel is None and after.channel is not None:
            self.vc_sessions[session_key] = time.time()
            taskforge_vc_active_sessions.set(len(self.vc_sessions))
            
        # Left all channels
        elif before.channel is not None and after.channel is None:
            if session_key in self.vc_sessions:
                join_time = self.vc_sessions.pop(session_key)
                taskforge_vc_active_sessions.set(len(self.vc_sessions))
                duration = int(time.time() - join_time)
                if duration > 0:
                    await database.update_leaderboard_stat(guild_id, user_id, "vc_time", duration)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        if interaction.user.bot or not interaction.guild_id:
            return
            
        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)
        
        await database.update_leaderboard_stat(guild_id, user_id, "commands_used", 1)

async def setup(bot):
    await bot.add_cog(LeaderboardTracker(bot))
