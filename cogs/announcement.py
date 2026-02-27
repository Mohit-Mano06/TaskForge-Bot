import discord
from discord.ext import commands
from discord import app_commands
from cogs.admin.config import DEV_GUILD_ID, ANNOUNCEMENT_CHANNEL_ID, OWNER_ID
import json
import os


class Announcement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="announce")
    @commands.is_owner()
    async def announce(self, ctx: commands.Context, version: str, release_type: str, *, message: str = None):
        if not message:
            await ctx.send("Please provide an announcement message.", delete_after=5)
            return

        if ctx.guild.id != DEV_GUILD_ID:
            return await ctx.send("You can't use this command here!", delete_after=5)

        release_types = {
            "major": "🔥 Major Release",
            "feature": "✨ New Feature",
            "patch": "🔧 Patch Update",
            "hotfix": "⚡ Hotfix"
        }
        
        if release_type not in release_types:
            return await ctx.send("Invalid release type.\n"
            "Use: major | feature | patch | hotfix", delete_after=7)

        try: 
            channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID) or await self.bot.fetch_channel(ANNOUNCEMENT_CHANNEL_ID)

            embed = discord.Embed(
                title = f"🚀 TaskForge v{version}",
                description=message,
                color = discord.Color.blurple(),
                timestamp = discord.utils.utcnow()
            )

            embed.add_field(
                name="Release Type",
                value = release_types[release_type],
                inline = False
            )

            embed.set_footer(text="TaskForge Bot")

            announcement_message = await channel.send(embed = embed)
            await announcement_message.add_reaction("🔥")


            data = {
                "version": version,
                "type": release_types[release_type],
                "message": message,
                "timestamp": str(discord.utils.utcnow())
            }

            if not os.path.exists("data/versions.json"):
                with open("data/versions.json", "w") as f:
                    json.dump({"releases": []}, f)
            
            with open("data/versions.json", "r") as f:
                file_data = json.load(f)
            
            file_data["releases"].append(data)

            with open("data/versions.json", "w") as f:
                json.dump(file_data, f, indent=4)




            await ctx.send("✅ Announcement sent successfully!", delete_after=5)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", delete_after=10)


    @commands.command()
    async def latest(self, ctx):

        if not os.path.exists("data/versions.json"):
            return await ctx.send("No releases found.", delete_after=5)

        with open("data/versions.json", "r") as f:
            file_data = json.load(f)

        latest_release = file_data["releases"][-1]

        embed = discord.Embed(
            title = f"🚀 TaskForge v{latest_release['version']}",
            description=latest_release['message'],
            color = discord.Color.green(),
            timestamp = discord.utils.utcnow()
        )

        embed.add_field(
            name="Release Type",
            value = latest_release['type'],
            inline = False
        )

        embed.add_field(
            name="Released on",
            value = latest_release['timestamp'],
            inline = False
        )


        await ctx.send(embed = embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Announcement(bot))
    