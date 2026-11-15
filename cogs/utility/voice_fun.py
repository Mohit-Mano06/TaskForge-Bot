import random 
import re

import discord
from discord.ext import commands

from cogs.admin.config import user_is_owner 


class VoiceFun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @staticmethod
    def parse_channels(guild, arguments):
        channel_ids = re.findall(r"<#(\d+)>", arguments)
        remaining = re.sub(r"<#\d+>", "", arguments).strip()

        channels = []

        for channel_id in channel_ids:
            channel = guild.get_channel(int(channel_id))

            if not isinstance(channel, discord.VoiceChannel):
                return None, None, "Invalid voice channel."

            channels.append

        if len(channels) > 2:
            return None, None, "You can only specify up to 2 voice channels."

        source = channels[0] if len(channels) == 2 else None
        destination = channels[-1] if channels else None

        return source, destination, remaining 

## Find member by ID or name 
    @staticmethod
    async def find_member(guild, query):

        if query.isdecimal():
            member = guild.get_member(int(query))
            if member:
                return member, None

            try: 
                return await guild.fetch_member(int(query)), None
            except discord.NotFound:
                return None, "Member not found."

        query = query.casefold()

        members = list(guild.members)

        exact_matches = [
            m for m in members 
            if query in {
                m.name.casefold(),
                m.display_name.casefold(),
                (m.global_name or "").casefold()
            }
        ]

        if len(exact_matches) == 1:
            return exact_matches[0], None

        if len(exact_matches) > 1:
            return None, exact_matches

        partial_matches = [
            m for m in members 
            if query in m.name.casefold() or query in m.display_name.casefold()
        ]

        if len(partial_matches) == 1:
            return partial_matches[0], None

        if len(partial_matches) > 1:
            return None, partial_matches

        return None, None

    @staticmethod
    def random_member(guild, source=None, exclude=None):

        channels = [source] if source else guild.voice_channels
        candidates = [
            member
            for channel in channels
            if channel for member in channel.members
            if not member.bot and member != exclude
        ]

        return random.choice(candidates) if candidates else None

    ## Find a random vc destination 
    @staticmethod
    def random_destination(guild, member, source):
        bot_member = guild.me

        if not bot_member:
            return None

        candidates = [
            channel
            for channel in guild.voice_channels
            if channel != source and channel != guild.afk_channel 
            and channel.permissions_for(bot_member).view_channel and channel.permissions_for(bot_member).move_members and channel.permissions_for(bot_member).connect
            and (
                channel.user_limit == 0 or len(channel.members) < channel.user_limit
            )
        ]

        return random.choice(candidates) if candidates else None

    ## Main movement function 

    async def move_member(self, ctx, member, destination=None):
        if member.bot:
            return await ctx.send("❌ You cannot move bots.")

        if member.voice is None:
            return await ctx.send(f"❌ {discord.utils.escape_markdown(member.display_name)} is not in a voice channel.")

        source = member.voice.channel
        bot_member = ctx.guild.me

        if not bot_member:
            return await ctx.send("❌ Could not resolve bot permissions.")

        source_perms = source.permissions_for(bot_member)

        if not source_perms.view_channel or not source_perms.move_members:
            return await ctx.send("❌ I do not have permission to View Channel and Move Members from the source channel.")

        # Random destination if not provided 
        if destination is None:
            destination = self.random_destination(ctx.guild, member, source)

        if destination is None:
            return await ctx.send("❌ No valid destination channel found.")

        if destination == source:
            return await ctx.send("❌ The destination channel is the same as the source channel.")

        # Validate destination 

        destination_perms = destination.permissions_for(bot_member)
        member_perms = destination.permissions_for(member)

        if not destination_perms.view_channel or not destination_perms.move_members or not destination_perms.connect:
            return await ctx.send("❌ I do not have permission to View Channel, Move Members, and Connect to the destination channel.")

        if (destination.user_limit > 0 and len(destination.members) >= destination.user_limit):
            return await ctx.send("❌ The destination channel is full.")

        try: 
            await member.move_to(destination, reason=f"TaskForge Yeet command by {ctx.author} ({ctx.author.id})")

            member_name = discord.utils.escape_markdown(member.display_name)

            channel_name = discord.utils.escape_markdown(destination.name)

            await ctx.send(f"✅ Yeeted **{member_name}** to **{channel_name}**." allowed_mentions=discord.AllowedMentions.none())

        except discord.Forbidden:
            return await ctx.send("❌ Discord denied voice channel movement.", allowed_mentions=discord.AllowedMentions.none())

        except discord.HTTPException:
            return await ctx.send("❌ Failed to move the member due to an unexpected error.", allowed_mentions=discord.AllowedMentions.none())


    # YEET COMMAND

    @commands.command(
        name="yeet",
        help="Randomly or manually move a member between voice channels",
        usage="$yeet <member|random> [destination_channel]",
    )

    @commands.check(lambda ctx: user_is_owner(ctx.author))
    @commands.guild_only()
    async def yeet(self, ctx, *, arguments: str):

        source, destination, target_query = self.parse_channels(ctx.guild, arguments)
        if source is None and destination is None and not target_query:
            return await ctx.send("❌ You must specify at least a member or a destination channel.")
        
        if destination is not None and source is None and not target_query:
            source = destination 
            destination = None

        if not target_query or target_query.casefold() == "random":
            member = self.random_member(
                ctx.guild,
                source=source,
                exclude=ctx.author
            )

            if member is None:
                return await ctx.send("❌ No valid member found to move.")

        else: 
            member, error = await self.find_member(ctx.guild, target_query)

            if isinstance(error, list):
                choices = "\n".join(
                    f"• {discord.utils.escape_markdown(m.display_name)} "
                    f"(`{m.id}`)"
                    for m in error[:10]
                )

                return await ctx.send(
                    f"⚠️ Multiple members match. Use their ID:\n{choices}",
                    allowed_mentions=discord.AllowedMentions.none()
                )

            if error:
                return await ctx.send(f"❌ {error}")

            if member is None:
                return await ctx.send(
                    "❌ Member not found. Try their username or Discord ID."
                )

        await self.move_member(ctx, member, destination)

    # Error handler    
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return await ctx.send("❌ You do not have permission to use this command.")
        raise error

async def setup(bot):
    await bot.add_cog(VoiceFun(bot))