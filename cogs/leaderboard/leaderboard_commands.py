import discord
from discord.ext import commands
import database

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_vc_time(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    async def get_username(self, guild, user_id):
        member = guild.get_member(int(user_id))
        if member:
            return member.display_name
        try:
            user = await self.bot.fetch_user(int(user_id))
            return user.display_name
        except:
            return f"Unknown User ({user_id})"

    async def generate_leaderboard_embed(self, ctx: commands.Context, stat_type: str, title: str, emoji: str, format_func=str):
        async with ctx.typing():
            guild_id = str(ctx.guild.id)
            top_users = await database.get_top_leaderboard(self.bot.db_pool, guild_id, stat_type, limit=10)
            
            if not top_users:
                await ctx.send(f"No data available for the {title} leaderboard yet.")
                return

            embed = discord.Embed(title=f"{emoji} {ctx.guild.name} {title} Leaderboard", color=discord.Color.gold())
            
            description = ""
            for i, user_data in enumerate(top_users):
                user_id = user_data["user_id"]
                stat_value = user_data.get(stat_type, 0)
                
                # Skip users with 0 score
                if stat_value == 0:
                    continue
                    
                username = await self.get_username(ctx.guild, user_id)
                formatted_value = format_func(stat_value)
                
                medals = ["🥇", "🥈", "🥉"]
                rank_display = medals[i] if i < 3 else f"`#{i+1}`"
                
                description += f"{rank_display} **{username}** - {formatted_value}\n"
                
            if not description:
                description = "No activity recorded yet."
                
            embed.description = description
            await ctx.send(embed=embed)

    @commands.group(name="leaderboard", aliases=["lb"], invoke_without_command=True)
    async def leaderboard_group(self, ctx):
        """View server activity leaderboards"""
        await ctx.send("Please specify a leaderboard: `messages`, `vc`, or `commands`.\nExample: `?leaderboard messages` (or `?lb msg`)")

    @leaderboard_group.command(name="messages", aliases=["msg"])
    async def lb_messages(self, ctx):
        """View the most active chatters"""
        await self.generate_leaderboard_embed(ctx, "messages_count", "Messages", "💬")

    @leaderboard_group.command(name="vc")
    async def lb_vc(self, ctx):
        """View the most active voice chatters"""
        await self.generate_leaderboard_embed(ctx, "vc_time", "Voice Time", "🎙️", self.format_vc_time)

    @leaderboard_group.command(name="commands", aliases=["cmds"])
    async def lb_commands(self, ctx):
        """View the most active command users"""
        await self.generate_leaderboard_embed(ctx, "commands_used", "Commands", "🤖")

    @leaderboard_group.command(name="channels")
    async def lb_channels(self, ctx):
        """View the most active channels in the server"""
        async with ctx.typing():
            guild_id = str(ctx.guild.id)
            top_channels = await database.get_top_channels(self.bot.db_pool, guild_id, limit=54)
            
            if not top_channels:
                await ctx.send("No channel data available yet.")
                return

            embed = discord.Embed(title=f"📊 {ctx.guild.name} Channel Activity", color=discord.Color.blue())
            
            description = ""
            for i, ch_data in enumerate(top_channels):
                channel_id = ch_data["channel_id"]
                count = ch_data["messages_count"]
                
                channel = ctx.guild.get_channel(int(channel_id))
                channel_name = channel.mention if channel else f"Deleted Channel ({channel_id})"
                
                medals = ["🥇", "🥈", "🥉"]
                rank_display = medals[i] if i < 3 else f"`#{i+1}`"
                
                description += f"{rank_display} {channel_name} - **{count}** messages\n"
                
            embed.description = description
            await ctx.send(embed=embed)

    @leaderboard_group.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def lb_sync(self, ctx, limit: int = 1000):
        """Admin only: Sync past messages. Pass 0 for full history."""
        history_limit = None if limit == 0 else limit
        msg = await ctx.send(f"🔄 Starting full sync (Limit: {'Unlimited' if history_limit is None else history_limit})...")
        
        guild_id = str(ctx.guild.id)
        user_stats = {}
        chan_stats = {}
        
        text_channels = ctx.guild.text_channels
        total_channels = len(text_channels)
        processed = 0
        
        try:
            for channel in text_channels:
                processed += 1
                chan_id = str(channel.id)
                chan_stats[chan_id] = 0
                
                # Update progress bar BEFORE reading the history so it feels responsive
                percent = int((processed / total_channels) * 10)
                bar = "█" * percent + "░" * (10 - percent)
                try: 
                    await msg.edit(content=f"🔄 Syncing...\n`[{bar}]` {processed}/{total_channels} channels\n*(Currently reading: #{channel.name})*")
                except: 
                    pass
                        
                try:
                    async for message in channel.history(limit=history_limit):
                        if not message.author.bot:
                            uid = str(message.author.id)
                            if uid not in user_stats:
                                user_stats[uid] = {"messages_count": 0}
                            user_stats[uid]["messages_count"] += 1
                            chan_stats[chan_id] += 1
                except discord.Forbidden: continue
                except Exception as e: print(f"Error: {e}")
            
            try:
                caller_count = user_stats.get(str(ctx.author.id), {}).get("messages_count", 0)
                await msg.edit(content=f"⏳ Saving data to database... (Found {caller_count} messages for you)")
            except: pass
                
            await database.bulk_update_leaderboard_stats(self.bot.db_pool, guild_id, user_stats, chan_stats)
            
            try:
                await msg.edit(content=f"✅ Sync complete! (Found {caller_count} messages for you)")
            except discord.NotFound:
                await ctx.send(f"{ctx.author.mention} ✅ Sync complete!")
        except Exception as e:
            try: await msg.edit(content=f"❌ Error: {str(e)}")
            except: await ctx.send(f"❌ Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(LeaderboardCommands(bot))
