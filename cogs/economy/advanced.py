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
        self.work_cooldowns = {}
        self.config = self._load_config()

    def _load_config(self):
        defaults = {
            "work_cooldown_seconds": 3600,
            "work_min": 100,
            "work_max": 400,
            "work_xp": 20,
            "work_answer_timeout_seconds": 45,
            "work_roles": {
                "developer": {"label": "Developer", "min": 100, "max": 400},
                "chef": {"label": "Chef", "min": 100, "max": 350},
                "detective": {"label": "Detective", "min": 120, "max": 450},
                "miner": {"label": "Miner", "min": 90, "max": 320},
                "dj": {"label": "DJ", "min": 100, "max": 380},
                "gamer": {"label": "Gamer", "min": 100, "max": 400},
            },
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

    def _role_choices(self):
        return self.config.get("work_roles", {})

    async def _generate_work_question(self, role):
        fallback_questions = {
            "developer": ("What keyword defines a function in Python?", "def"),
            "chef": ("What kitchen tool is commonly used to cut vegetables?", "knife"),
            "detective": ("What do detectives collect from a crime scene as evidence?", "clues"),
            "miner": ("What valuable material is commonly mined from the ground?", "ore"),
            "dj": ("What device does a DJ use to play and mix music?", "mixer"),
            "gamer": ("What device do most PC gamers use to control movement?", "keyboard"),
        }
        fallback = fallback_questions.get(role, ("What is 2 + 2?", "4"))
        client = getattr(self.bot, "mistral_client", None)
        if client is None:
            return fallback
        prompt = (
            f"Create one easy beginner question for a Discord economy game role: {role}. "
            "Return exactly two lines: QUESTION: <question> and ANSWER: <short answer>. "
            "Do not use markdown, multiple answers, or trick questions."
        )
        try:
            response = await client.chat.complete_async(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content.strip()
            question_match = re.search(r"QUESTION:\s*(.+)", content, re.IGNORECASE)
            answer_match = re.search(r"ANSWER:\s*(.+)", content, re.IGNORECASE)
            if question_match and answer_match:
                return question_match.group(1).strip(), answer_match.group(1).strip()
        except Exception as error:
            print(f"Work question generation failed: {error}")
        return fallback

    @commands.command(name="work")
    async def work(self, ctx, role: str | None = None):
        """Answer an easy role question for a variable work payout."""
        if not self._ready():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return
        roles = self._role_choices()
        profile = await self._profile(ctx)
        if role is None:
            role = profile.get("job")
        if role is None:
            role_lines = [f"`{role_id}` - {role_data.get('label', role_id.title())}" for role_id, role_data in roles.items()]
            await ctx.send("💼 Choose your first job with `$work <role>`:\n" + "\n".join(role_lines))
            return
        role = role.lower().replace(" ", "_")
        if role not in roles:
            await ctx.send(f"❌ Unknown role. Choose: {', '.join(roles)}")
            return
        if profile.get("job") != role:
            await db.set_user_job(self.bot.db_pool, ctx.author.id, ctx.guild.id, role)
            await ctx.send(f"✅ You are now working as a **{roles[role].get('label', role.title())}**.")
        now = time.time()
        remaining = self.work_cooldowns.get((ctx.guild.id, ctx.author.id), 0) - now
        if remaining > 0:
            await ctx.send(f"⏳ You can work again in {int(remaining // 60) + 1} minutes.")
            return
        self.work_cooldowns[(ctx.guild.id, ctx.author.id)] = now + self.config["work_cooldown_seconds"]
        question, expected_answer = await self._generate_work_question(role)
        await ctx.send(
            f"💼 **{roles[role].get('label', role.title())} job**\n{question}\n"
            f"Reply within {self.config['work_answer_timeout_seconds']} seconds."
        )

        def answer_check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            answer = await self.bot.wait_for(
                "message", check=answer_check,
                timeout=self.config["work_answer_timeout_seconds"]
            )
        except TimeoutError:
            await ctx.send("⌛ Time's up. No payment was awarded.")
            return

        normalized_answer = re.sub(r"[^a-z0-9 ]", "", answer.content.lower()).strip()
        normalized_expected = re.sub(r"[^a-z0-9 ]", "", expected_answer.lower()).strip()
        answer_words = set(normalized_answer.split())
        expected_words = set(normalized_expected.split())
        correct = normalized_answer == normalized_expected or bool(answer_words & expected_words)
        role_config = roles[role]
        if correct:
            reward = random.randint(int(role_config.get("min", self.config["work_min"])), int(role_config.get("max", self.config["work_max"])))
            xp_reward = self.config["work_xp"]
            result = f"✅ Correct! You earned 🪙 `{reward:,}` and ✨ `{xp_reward}` XP."
        else:
            reward = 0
            xp_reward = max(1, self.config["work_xp"] // 4)
            result = f"❌ Not quite. The answer was `{expected_answer}`. You earned ✨ `{xp_reward}` XP."
        await db.update_balances(self.bot.db_pool, ctx.author.id, ctx.guild.id, reward, 0, "WORK", f"Completed {role} job")
        await db.update_xp(self.bot.db_pool, ctx.author.id, ctx.guild.id, xp_reward)
        await ctx.send(result)

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
        except Exception as error:
            print(f"Prestige database error: {error}")
            await ctx.send("❌ Prestige is temporarily unavailable because the economy database needs a migration. Please restart the bot.")


async def setup(bot):
    await bot.add_cog(AdvancedEconomy(bot))
