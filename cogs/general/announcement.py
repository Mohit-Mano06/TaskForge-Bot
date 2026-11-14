import discord
from discord.ext import commands
from discord import app_commands
from cogs.admin.config import DEV_GUILD_ID, ANNOUNCEMENT_CHANNEL_ID, OWNER_ID
from mistralai.client import Mistral
import json
import os
import database


class Announcement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = Mistral(api_key=os.getenv("MISTRAL_TOKEN"))

        self.announce_prompt = """
        You are a ghost-writer for the admin of TaskForge — a custom Discord bot built and maintained by Mohit for his Discord server.

        Your job is to write the body of a bot update announcement that the admin will post in the server's announcement channel.
        The audience is the server members — regular Discord users who use TaskForge's features like music, AI chat, DJ, reminders, etc.

        The admin gives you:
        1. The update type (major / feature / patch / hotfix)
        2. A short raw developer note explaining what changed

        Your job is to turn that raw note into a clean, well-written announcement that feels personal, direct, and natural —
        like the bot owner themselves wrote it to their community, not a corporate press release.

        Tone guide based on update type:
        - major: Exciting and proud. This is a big milestone. Make the community feel the hype.
        - feature: Friendly and enthusiastic. "Hey, something new just dropped!" energy.
        - patch: Straightforward and clean. "Small improvement, here's what changed." No fluff.
        - hotfix: Calm and transparent. Acknowledge something was broken, confirm it's fixed now.

        Writing rules:
        - Use first-person plural (“We added…”, “We fixed…”)
        - Start direct, no filler
        - Expand into 1–2 short sentences max
        - Keep tone simple, not exaggerated
        - Optional light emoji (0–1)
        - Use **bold** only if needed
        - Under 60 words
        - No version/title
        - Output only announcement body
        """


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
            return await ctx.send(
                "Invalid release type.\nUse: major | feature | patch | hotfix",
                delete_after=7
            )

        try:
            # Generate AI announcement body
            async with ctx.typing():
                ai_description = message  # fallback if AI fails
                try:
                    user_prompt = (
                        f"Update type: {release_type}\n"
                        f"Developer note: {message}"
                    )
                    response = await self.client.chat.complete_async(
                        model="open-mistral-7b",
                        messages=[
                            {"role": "system", "content": self.announce_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    ai_description = response.choices[0].message.content.strip()
                except Exception as ai_err:
                    print(f"[Announce] AI generation failed, using raw message. Error: {ai_err}")

            channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL_ID) or await self.bot.fetch_channel(ANNOUNCEMENT_CHANNEL_ID)

            announcement_text = (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 **TaskForge v{version}** — {release_types[release_type]}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{ai_description}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 *AI-crafted by TaskForge*"
            )

            announcement_message = await channel.send(announcement_text)
            await announcement_message.add_reaction("🔥")

            # Save to versions.json (store both raw note and AI text)
            data = {
                "version": version,
                "type": release_types[release_type],
                "message": message,
                "ai_description": ai_description,
                "timestamp": str(discord.utils.utcnow())
            }

            await database.save_release(getattr(self.bot, "db_pool", None), data)

            await ctx.send("✅ AI Announcement sent successfully!", delete_after=5)

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", delete_after=10)


    @commands.command()
    async def latest(self, ctx):
        latest_release = await database.get_latest_release(getattr(self.bot, "db_pool", None))
        if not latest_release:
            return await ctx.send("❌ No release data found or it's corrupted.", delete_after=5)

        # Show AI description if available, else raw message
        description = latest_release.get("ai_description", latest_release["message"])

        embed = discord.Embed(
            title=f"🚀 TaskForge v{latest_release['version']}",
            description=description,
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Release Type",
            value=latest_release['type'],
            inline=False
        )

        embed.add_field(
            name="Released on",
            value=latest_release['timestamp'],
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Announcement(bot))