import random
import time
import json

import discord
from discord.ext import commands

from cogs.economy import db


class AdvancedEconomy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_cooldown = 0.0
        self.work_cooldowns = {}
        self.config = self._load_config()

    def _load_config(self):
        defaults = {
            "work_cooldown_seconds": 3600,
            "work_min": 100,
            "work_max": 400,
            "work_xp": 20,
            "event_cooldown_seconds": 7200,
            "prestige_level": 50,
            "prestige_reward": 5000,
        }
        try:
            with open("data/economy_config.json", "r", encoding="utf-8") as file:
                return {**defaults, **json.load(file).get("advanced_economy", {})}
        except (OSError, json.JSONDecodeError):
            return defaults

    def _ready(self):
        return getattr(self.bot, "db_pool", None) is not None

    async def _profile(self, ctx):
        return await db.get_or_create_user(self.bot.db_pool, ctx.author.id, ctx.guild.id)

    @commands.command(name="gift")
    async def gift(self, ctx, recipient: discord.Member, amount_or_item: str, quantity: int | None = None):
        """Gift wallet coins or inventory items to another member."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        if recipient.bot or recipient.id == ctx.author.id:
            await ctx.send("❌ Choose another human member as the recipient.")
            return

        if quantity is None:
            try:
                amount = int(amount_or_item)
            except ValueError:
                await ctx.send("❌ Use `$gift @user <coins>` or `$gift @user <item> <quantity>`.")
                return
            try:
                await db.get_or_create_user(self.bot.db_pool, recipient.id, ctx.guild.id)
                await db.gift_currency(self.bot.db_pool, ctx.author.id, recipient.id, ctx.guild.id, amount)
                await ctx.send(f"✅ Gifted 🪙 `{amount:,}` to {recipient.mention}.")
            except ValueError as error:
                await ctx.send(f"❌ {error}")
            return

        item_id = amount_or_item
        if quantity <= 0:
            await ctx.send("❌ Quantity must be at least 1.")
            return
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog is None:
            await ctx.send("❌ The item catalogue is unavailable.")
            return
        item_id = economy_cog._resolve_item_id(item_id)
        item = economy_cog._get_item(item_id)
        if not item:
            await ctx.send("❌ That item does not exist.")
            return
        try:
            await db.gift_item(self.bot.db_pool, ctx.author.id, recipient.id, ctx.guild.id, item_id, quantity)
            await ctx.send(f"✅ Gifted {quantity}x {item['name']} to {recipient.mention}.")
        except ValueError as error:
            await ctx.send(f"❌ {error}")

    @commands.command(name="achievements", aliases=["ach"])
    async def achievements(self, ctx, member: discord.Member | None = None):
        """Show achievements earned by a member."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        member = member or ctx.author
        achievements = await db.get_achievements(self.bot.db_pool, member.id, ctx.guild.id)
        names = [f"🏆 {entry['name']}" for entry in achievements]
        await ctx.send(embed=discord.Embed(
            title=f"🏆 {member.display_name}'s Achievements",
            description="\n".join(names) if names else "No achievements earned yet.",
            color=discord.Color.gold(),
        ))

    @commands.command(name="economy_leaderboard", aliases=["econlb"])
    async def economy_leaderboard(self, ctx):
        """Show the wealth leaderboard for this server."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        rows = await db.get_economy_leaderboard(self.bot.db_pool, ctx.guild.id)
        lines = []
        for index, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(int(row["user_id"]))
            name = member.display_name if member else row["user_id"]
            total = row["wallet"] + row["bank"]
            lines.append(f"`#{index}` **{name}**: 🪙 `{total:,}` | Prestige {row['prestige']}")
        await ctx.send(embed=discord.Embed(
            title=f"🏆 {ctx.guild.name} Economy Leaderboard",
            description="\n".join(lines) if lines else "No economy profiles yet.",
            color=discord.Color.gold(),
        ))

    @commands.command(name="work")
    async def work(self, ctx):
        """Complete a cooldowned job for coins and XP."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        now = time.time()
        remaining = self.work_cooldowns.get((ctx.guild.id, ctx.author.id), 0) - now
        if remaining > 0:
            await ctx.send(f"⏳ You can work again in {int(remaining // 60) + 1} minutes.")
            return
        await self._profile(ctx)
        reward = random.randint(self.config["work_min"], self.config["work_max"])
        await db.update_balances(self.bot.db_pool, ctx.author.id, ctx.guild.id, reward, 0, "WORK", "Completed a job")
        await db.update_xp(self.bot.db_pool, ctx.author.id, ctx.guild.id, self.config["work_xp"])
        self.work_cooldowns[(ctx.guild.id, ctx.author.id)] = now + self.config["work_cooldown_seconds"]
        await ctx.send(f"💼 You completed a job and earned 🪙 `{reward:,}` plus ✨ `{self.config['work_xp']}` XP.")

    @commands.command(name="event")
    async def event(self, ctx):
        """Trigger a cooldowned server-wide bonus event."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        remaining = self.event_cooldown - time.time()
        if remaining > 0:
            await ctx.send("⏳ No event is ready yet. Try again later.")
            return
        reward = random.randint(100, 500)
        self.event_cooldown = time.time() + self.config["event_cooldown_seconds"]
        await self._profile(ctx)
        await db.update_balances(self.bot.db_pool, ctx.author.id, ctx.guild.id, reward, 0, "RANDOM_EVENT", "Found a random server event")
        await ctx.send(f"🚨 **TREASURE EVENT!** {ctx.author.mention} found 🪙 `{reward:,}`.")

    @commands.command(name="prestige")
    async def prestige(self, ctx):
        """Reset level progress in exchange for a permanent prestige rank."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        await self._profile(ctx)
        try:
            profile = await db.prestige_user(
                self.bot.db_pool, ctx.author.id, ctx.guild.id,
                self.config["prestige_level"], self.config["prestige_reward"]
            )
            await ctx.send(f"👑 Prestige `{profile['prestige']}` unlocked. Level reset to 1 with 🪙 `{self.config['prestige_reward']:,}`.")
        except ValueError as error:
            await ctx.send(f"❌ {error}")


async def setup(bot):
    await bot.add_cog(AdvancedEconomy(bot))
