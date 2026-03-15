## commands - purge, kick, ban, lock 

import discord 
from discord.ext import commands
from datetime import datetime, timezone
import json
import os
from .logging import send_log

ALLOWED_ROLE_IDS = [1471835077787783270, 1470002009812766751]

async def is_bot_admin_check(ctx):
    # Check if any of the user's roles match the allowed admin roles
    return any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles)

is_bot_admin = commands.check(is_bot_admin_check)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings_path = os.path.join(os.path.dirname(__file__), "warnings.json")
    
    def load_warnings(self):
        if not os.path.exists(self.warnings_path):
            return {}
        try:
            with open(self.warnings_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
        
    def save_warnings(self, data):
        with open(self.warnings_path, "w") as f:
            json.dump(data, f, indent=4)

## PURGE COMMAND 
    @commands.command()
    @is_bot_admin
    async def purge(self, ctx, amount: int):
        if amount <= 0 or amount > 100:
            return await ctx.send("⚠ Amount must be between 1 and 100")
        
        deleted = await ctx.channel.purge(limit=amount+1)

        confirmation = await ctx.send(
            f"🧹 Deleted {len(deleted)-1} messages.",
            delete_after=5
        )

        embed = discord.Embed(
            title = "🧹 Messages Purged",
            color = discord.Color.red(),
            timestamp = datetime.now(timezone.utc)
        )

        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        embed.add_field(name="Amount", value=len(deleted)-1, inline=False)

        await send_log(self.bot, ctx.guild, embed)

## Kick Command
    @commands.command()
    @is_bot_admin
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send("You can't kick yourself!")
        if member == ctx.guild.owner:
            return await ctx.send("You can't kick the owner!")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You can't kick someone with a higher or equal role!")
        if member == self.bot.user:
            return await ctx.send("You can't kick me!")
        
        try:
            await member.send(f"You were kicked from {ctx.guild.name}\nReason: {reason}")
        except:
            pass

        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 {member.mention} has been kicked.")
        except discord.Forbidden:
            return await ctx.send("❌ **Error:** I don't have permission to kick this member. Make sure my role is **above** theirs in the server settings!")
        except Exception as e:
            return await ctx.send(f"❌ **Error:** {str(e)}")

        embed = discord.Embed(
            title = "👢 Member Kicked",
            color = discord.Color.orange(),
            timestamp = datetime.now(timezone.utc)
        )

        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await send_log(self.bot, ctx.guild, embed)

## Ban Command
    @commands.command()
    @is_bot_admin
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send("You can't ban yourself!")
        if member == ctx.guild.owner:
            return await ctx.send("You can't ban the owner!")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You can't ban someone with a higher or equal role!")
        
        try:
            await member.send(f"You were BANNED from {ctx.guild.name}\nReason: {reason}")
        except:
            pass

        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 {member.mention} has been banned.")
        except discord.Forbidden:
            return await ctx.send("❌ **Error:** I don't have permission to ban this member. Make sure my role is **above** theirs in the server settings!")
        except Exception as e:
            return await ctx.send(f"❌ **Error:** {str(e)}")

        embed = discord.Embed(
            title = "🔨 Member Banned",
            color = discord.Color.dark_red(),
            timestamp = datetime.now(timezone.utc)
        )

        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await send_log(self.bot, ctx.guild, embed)

## Warn Command
    @commands.command()
    @is_bot_admin
    async def warn(self, ctx, member: discord.Member, *, reason = "No Reason Provided"):
        if await self.bot.is_owner(ctx.author):
            pass # Owner can warn anyone
        else:
            if member == ctx.author:
                return await ctx.send("You can't warn yourself!")
            if member.top_role >= ctx.author.top_role:
                return await ctx.send("You can't warn someone with a higher or equal role!")
        if member == self.bot.user:
            return await ctx.send("You can't warn me!")
        
        warnings = self.load_warnings()
        if str(member.id) not in warnings:
            warnings[str(member.id)] = []
        
        warnings[str(member.id)].append({
            "moderator": ctx.author.id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        self.save_warnings(warnings)
        
        try:
            dm_embed = discord.Embed(
                title="⚠️ You received a warning",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
    
            dm_embed.add_field(name="Server", value=ctx.guild.name, inline=False)
            dm_embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
            dm_embed.add_field(name="Reason", value=reason, inline=False)

            await member.send(embed=dm_embed)

        except discord.Forbidden:
            await ctx.send(f"⚠️ Couldn't DM {member.mention}, they may have DMs disabled.")

        await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason}")
        
        embed = discord.Embed(
            title = "⚠️ Member Warned",
            color = discord.Color.orange(),
            timestamp = datetime.now(timezone.utc)
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await send_log(self.bot, ctx.guild, embed)

## Lock Command
    @commands.command()
    @is_bot_admin
    async def lock(self, ctx):
        """Locks the current channel."""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Channel locked.")

        embed = discord.Embed(
            title = "🔒 Channel Locked",
            color = discord.Color.greyple(),
            timestamp = datetime.now(timezone.utc)
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        await send_log(self.bot, ctx.guild, embed)

## Unlock Command
    @commands.command()
    @is_bot_admin
    async def unlock(self, ctx):
        """Unlocks the current channel."""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Channel unlocked.")

        embed = discord.Embed(
            title = "🔓 Channel Unlocked",
            color = discord.Color.green(),
            timestamp = datetime.now(timezone.utc)
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        await send_log(self.bot, ctx.guild, embed)

    
async def setup(bot):
    await bot.add_cog(Moderation(bot))
