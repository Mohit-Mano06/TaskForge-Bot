import random
import time
import json
import re

import discord
from discord.ext import commands

from cogs.economy import db


class AdvancedEconomy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_cooldown = 0.0
        self.gamble_cooldowns = {}
        self.rob_cooldowns = {}
        self.config = self._load_config()

    def _load_config(self):
        defaults = {
            "work_cooldown_seconds": 3600,
            "work_min": 100,
            "work_max": 400,
            "work_xp": 20,
            "event_cooldown_seconds": 7200,
            "event_rewards": {
                "treasure": {"label": "A treasure chest appeared", "min": 100, "max": 500},
                "meteor": {"label": "A meteor shower scattered star coins", "min": 150, "max": 700},
                "bounty": {"label": "A server bounty was posted", "min": 75, "max": 350},
                "jackpot": {"label": "The TaskForge jackpot opened", "min": 250, "max": 1000},
            },
            "gamble_cooldown_seconds": 30,
            "rob_cooldown_seconds": 3600,
            "rob_success_chance": 0.45,
            "rob_max_percent": 0.25,
            "rob_penalty_percent": 0.10,
            "pets": {
                "cat": {"name": "Cat", "emoji": "🐱", "description": "A curious companion.", "cost": 2500},
                "dog": {"name": "Dog", "emoji": "🐶", "description": "A loyal companion.", "cost": 3000},
                "fox": {"name": "Fox", "emoji": "🦊", "description": "A clever companion.", "cost": 5000},
                "dragon": {"name": "Dragon", "emoji": "🐉", "description": "A legendary companion.", "cost": 25000},
            },
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
    async def gift(self, ctx, *arguments):
        """Gift coins or items using either item-first or user-first syntax."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        if len(arguments) < 2:
            await ctx.send("❌ Use `$gift @user <coins>` or `$gift <item> @user [quantity]`.")
            return

        recipient = None
        recipient_index = None
        member_converter = commands.MemberConverter()
        for index, argument in enumerate(arguments):
            try:
                recipient = await member_converter.convert(ctx, argument)
                recipient_index = index
                break
            except commands.MemberNotFound:
                continue

        if recipient is None:
            await ctx.send("❌ I could not find that Discord member.")
            return
        if recipient.bot or recipient.id == ctx.author.id:
            await ctx.send("❌ Choose another human member as the recipient.")
            return

        gift_arguments = [argument for index, argument in enumerate(arguments) if index != recipient_index]
        if len(gift_arguments) == 1:
            try:
                amount = int(gift_arguments[0])
            except ValueError:
                amount = None
            if amount is not None:
                try:
                    await db.get_or_create_user(self.bot.db_pool, recipient.id, ctx.guild.id)
                    await db.gift_currency(self.bot.db_pool, ctx.author.id, recipient.id, ctx.guild.id, amount)
                    await ctx.send(f"✅ Gifted 🪙 `{amount:,}` to {recipient.mention}.")
                except ValueError as error:
                    await ctx.send(f"❌ {error}")
                return

        item_id = gift_arguments[0]
        quantity = int(gift_arguments[1]) if len(gift_arguments) > 1 and gift_arguments[1].isdigit() else 1
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
        reward = random.randint(self.config["work_min"], self.config["work_max"])
        await self._profile(ctx)
        await db.update_balances(self.bot.db_pool, ctx.author.id, ctx.guild.id, reward, 0, "WORK", "Completed a job")
        await db.update_xp(self.bot.db_pool, ctx.author.id, ctx.guild.id, self.config["work_xp"])
        await ctx.send(f"💼 You completed a job and earned 🪙 `{reward:,}` plus ✨ `{self.config['work_xp']}` XP.")

    @commands.command(name="gamble", aliases=["bet"])
    async def gamble(self, ctx, amount: int):
        """Risk wallet coins on a 50/50 double-or-lose bet."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        if amount <= 0:
            await ctx.send("❌ Your bet must be at least 1 coin.")
            return
        key = (ctx.guild.id, ctx.author.id)
        remaining = self.gamble_cooldowns.get(key, 0) - time.time()
        if remaining > 0:
            await ctx.send(f"⏳ Try gambling again in {int(remaining) + 1} seconds.")
            return
        await self._profile(ctx)
        won = random.random() < 0.5
        try:
            _, change = await db.gamble(self.bot.db_pool, ctx.author.id, ctx.guild.id, amount, won, 2 if won else 0)
        except ValueError as error:
            await ctx.send(f"❌ {error}")
            return
        self.gamble_cooldowns[key] = time.time() + self.config["gamble_cooldown_seconds"]
        if won:
            await ctx.send(f"🎰 You won! Your wallet gained 🪙 `{change:,}`.")
        else:
            await ctx.send(f"🎰 You lost 🪙 `{amount:,}`. Better luck next time.")

    @commands.command(name="rob")
    async def rob(self, ctx, target: discord.Member):
        """Attempt to steal a limited amount from another user's wallet."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        if target.bot or target.id == ctx.author.id:
            await ctx.send("❌ Choose another human member to rob.")
            return
        key = (ctx.guild.id, ctx.author.id)
        remaining = self.rob_cooldowns.get(key, 0) - time.time()
        if remaining > 0:
            await ctx.send(f"⏳ Try again in {int(remaining // 60) + 1} minutes.")
            return
        await self._profile(ctx)
        target_profile = await db.get_or_create_user(self.bot.db_pool, target.id, ctx.guild.id)
        target_wallet = target_profile["wallet"]
        amount = max(1, int(target_wallet * self.config["rob_max_percent"])) if target_wallet else 0
        penalty = max(1, int(amount * self.config["rob_penalty_percent"])) if amount else 0
        if amount == 0:
            await ctx.send("❌ That user's wallet is empty.")
            return
        success = random.random() < self.config["rob_success_chance"]
        try:
            if success:
                await db.rob_user(self.bot.db_pool, ctx.author.id, target.id, ctx.guild.id, amount, 0)
                await ctx.send(f"🕵️ Success! You stole 🪙 `{amount:,}` from {target.mention}.")
            else:
                await db.rob_user(self.bot.db_pool, ctx.author.id, target.id, ctx.guild.id, 0, penalty)
                await ctx.send(f"🚨 You were caught and paid 🪙 `{penalty:,}` to {target.mention}.")
        except ValueError as error:
            await ctx.send(f"❌ {error}")
            return
        self.rob_cooldowns[key] = time.time() + self.config["rob_cooldown_seconds"]

    @commands.group(name="pets", invoke_without_command=True)
    async def pets(self, ctx):
        """Show owned pets or the available pet actions."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        owned = await db.get_pets(self.bot.db_pool, ctx.author.id, ctx.guild.id)
        if owned:
            lines = [f"{pet['emoji']} **{pet['name']}** {'(equipped)' if pet['equipped'] else ''}" for pet in owned]
            await ctx.send("🐾 Your pets:\n" + "\n".join(lines) + "\nUse `$pets adopt <pet>` or `$pets equip <pet>`." )
            return
        available = ", ".join(f"{pet_id} ({pet['cost']:,})" for pet_id, pet in self.config["pets"].items())
        await ctx.send(f"🐾 You have no pets. Adopt one with `$pets adopt <pet>`:\n{available}")

    @pets.command(name="adopt")
    async def pets_adopt(self, ctx, pet_id: str):
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        pet_id = pet_id.lower().replace(" ", "_")
        pet = self.config["pets"].get(pet_id)
        if not pet:
            await ctx.send(f"❌ Unknown pet. Choose: {', '.join(self.config['pets'])}")
            return
        await self._profile(ctx)
        try:
            await db.adopt_pet(self.bot.db_pool, ctx.author.id, ctx.guild.id, pet_id, pet["name"], pet["description"], pet["emoji"], pet["cost"])
            await ctx.send(f"✅ You adopted {pet['emoji']} **{pet['name']}** for 🪙 `{pet['cost']:,}`.")
        except ValueError as error:
            await ctx.send(f"❌ {error}")

    @pets.command(name="equip")
    async def pets_equip(self, ctx, pet_id: str):
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        try:
            await db.equip_pet(self.bot.db_pool, ctx.author.id, ctx.guild.id, pet_id.lower().replace(" ", "_"))
            await ctx.send(f"✅ Your **{pet_id}** is now equipped.")
        except ValueError as error:
            await ctx.send(f"❌ {error}")

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
        event_id, event = random.choice(list(self.config["event_rewards"].items()))
        reward = random.randint(event["min"], event["max"])
        self.event_cooldown = time.time() + self.config["event_cooldown_seconds"]
        await self._profile(ctx)
        await db.update_balances(self.bot.db_pool, ctx.author.id, ctx.guild.id, reward, 0, "RANDOM_EVENT", f"Participated in {event_id} event")
        await ctx.send(f"🚨 **{event['label']}!** {ctx.author.mention} found 🪙 `{reward:,}`.")

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
        except Exception as error:
            print(f"Prestige database error: {error}")
            await ctx.send("❌ Prestige is temporarily unavailable because the economy database needs a migration. Please restart the bot.")


async def setup(bot):
    await bot.add_cog(AdvancedEconomy(bot))
