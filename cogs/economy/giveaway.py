import asyncio
import json
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands

from cogs.economy import db
from cogs.admin.config import OWNER_IDS, user_has_admin_access

# IST timezone is used in all giveaway timing displays and scheduling.
IST = ZoneInfo("Asia/Kolkata")

# Change these values to adjust the giveaway timings.
# Entry window duration = how long people can react to join.
# Reminder lead time = how long before close we ping again.
# Winner announcement delay = how long after close the result is revealed.
# For quick testing, set GIVEAWAY_USE_TEST_TIMINGS = True and the values below will be used in seconds.
GIVEAWAY_USE_TEST_TIMINGS = False
GIVEAWAY_ENTRY_DURATION_HOURS = 28 #hours
GIVEAWAY_REMINDER_BEFORE_CLOSE_HOURS = 2 #hours
GIVEAWAY_WINNER_ANNOUNCEMENT_DELAY_HOURS = 3 
GIVEAWAY_TEST_ENTRY_SECONDS = 20
GIVEAWAY_TEST_REMINDER_SECONDS = 5
GIVEAWAY_TEST_WINNER_DELAY_SECONDS = 5

GIVEAWAY_PRIZE_MIN = 10000
GIVEAWAY_PRIZE_MAX = 50000
GIVEAWAY_LOW_PRIZE_THRESHOLD = 15000
GIVEAWAY_BONUS_ITEM_POOL = [
    "golden_coin",
    "cool_badge",
    "limited_poster",
    "glowing_aura",
    "profile_frame",
]
GIVEAWAY_REACTION = "🎉"

# Only configured owners or authorized admin-role members may manage giveaways.
# Keep this list centrally in cogs/admin/config.py.
GIVEAWAY_ALLOWED_STARTER_IDS = set(OWNER_IDS)

# For testing, keep this as a placeholder so it does not spam everyone.
# Later, replace it with "@everyone" or your own mention if you want a wider ping.
GIVEAWAY_PING_TEXT = "<@everyone>"

DATA_PATH = os.path.join("data", "giveaway_entries.json")


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self._tasks = {}
        self._ensure_data_file()
        self.active_giveaways = self._load_state()

    def _ensure_data_file(self):
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        if not os.path.exists(DATA_PATH):
            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _load_state(self):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.active_giveaways, f, indent=2)

    def _guild_state(self, guild_id):
        guild_id = str(guild_id)
        if guild_id not in self.active_giveaways:
            self.active_giveaways[guild_id] = {
                "active": False,
                "entries": [],
                "message_id": None,
                "channel_id": None,
                "started_at": None,
                "entry_closes_at": None,
                "winner_announced_at": None,
                "last_winner": None,
                "last_prize": 0,
                "pending_reward": None,
            }
        return self.active_giveaways[guild_id]

    def _format_ist(self, dt):
        if dt is None:
            return "Not set"
        return self._as_utc(dt).astimezone(IST).strftime("%Y-%m-%d %H:%M IST")

    @staticmethod
    def _as_utc(dt):
        if dt.tzinfo is None or dt.utcoffset() is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _entry_duration(self):
        if GIVEAWAY_USE_TEST_TIMINGS:
            return timedelta(seconds=GIVEAWAY_TEST_ENTRY_SECONDS)
        return timedelta(hours=GIVEAWAY_ENTRY_DURATION_HOURS)

    def _reminder_duration(self):
        if GIVEAWAY_USE_TEST_TIMINGS:
            return timedelta(seconds=GIVEAWAY_TEST_REMINDER_SECONDS)
        return timedelta(hours=GIVEAWAY_REMINDER_BEFORE_CLOSE_HOURS)

    def _winner_delay(self):
        if GIVEAWAY_USE_TEST_TIMINGS:
            return timedelta(seconds=GIVEAWAY_TEST_WINNER_DELAY_SECONDS)
        return timedelta(hours=GIVEAWAY_WINNER_ANNOUNCEMENT_DELAY_HOURS)

    async def _grant_giveaway_reward(self, guild, user_id, amount, item_bonus=None):
        if not hasattr(self.bot, "db_pool") or self.bot.db_pool is None:
            return False

        try:
            await db.update_balances(
                self.bot.db_pool,
                user_id,
                guild.id,
                wallet_change=amount,
                bank_change=0,
                tx_type="GIVEAWAY_WIN",
                tx_desc="Weekly giveaway prize",
            )
            if item_bonus:
                await db.add_item_to_inventory(self.bot.db_pool, user_id, guild.id, item_bonus, 1)
            return True
        except Exception:
            return False

    async def _credit_pending_reward_if_possible(self, guild_id, user_id):
        state = self._guild_state(guild_id)
        pending = state.get("pending_reward")
        if not pending:
            return False

        if str(user_id) != str(pending.get("user_id")):
            return False

        if not await self._profile_exists(guild_id, user_id):
            return False

        guild = self.bot.get_guild(int(guild_id))
        if guild is None:
            return False

        success = await self._grant_giveaway_reward(
            guild,
            user_id,
            pending.get("amount", 0),
            pending.get("item_bonus"),
        )
        if success:
            state["pending_reward"] = None
            self._save_state()
        return success

    async def _profile_exists(self, guild_id, user_id):
        if not hasattr(self.bot, "db_pool") or self.bot.db_pool is None:
            return False

        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM public.economy_users WHERE user_id = $1 AND guild_id = $2",
                str(user_id), str(guild_id),
            )
            return row is not None

    async def _send_giveaway_message(self, guild, channel, message_text):
        return await channel.send(message_text)

    def _get_channel_for_giveaway(self, guild, guild_id):
        state = self._guild_state(guild_id)
        channel_id = state.get("channel_id")
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel is not None:
                return channel
        return guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)

    async def _close_giveaway(self, guild_id):
        guild = self.bot.get_guild(int(guild_id))
        if guild is None:
            return

        state = self._guild_state(guild_id)
        if not state.get("active"):
            return

        entries = list(state.get("entries", []))
        state["active"] = False
        state["message_id"] = None
        state["channel_id"] = None
        state["entry_closes_at"] = None
        state["winner_announced_at"] = None

        if not entries:
            self._save_state()
            channel = self._get_channel_for_giveaway(guild, guild_id)
            if channel:
                await channel.send("🎁 Giveaway closed with no entries. No winner was selected.")
            return

        winner_id = random.choice(entries)
        prize_amount = random.randint(GIVEAWAY_PRIZE_MIN, GIVEAWAY_PRIZE_MAX)
        item_bonus = None
        if prize_amount <= GIVEAWAY_LOW_PRIZE_THRESHOLD:
            item_bonus = random.choice(GIVEAWAY_BONUS_ITEM_POOL)

        state["last_winner"] = winner_id
        state["last_prize"] = prize_amount
        state["pending_reward"] = None

        winner_member = guild.get_member(int(winner_id)) or await self.bot.fetch_user(int(winner_id))
        profile_missing = not await self._profile_exists(guild_id, winner_id)

        if profile_missing:
            state["pending_reward"] = {
                "user_id": str(winner_id),
                "amount": prize_amount,
                "item_bonus": item_bonus,
            }
            self._save_state()
            try:
                if hasattr(winner_member, "send"):
                    await winner_member.send(
                        "🎁 You won the weekly giveaway! Please create your economy profile with `$balance` in the server, and your reward will be credited once your profile exists."
                    )
            except Exception:
                pass
        else:
            success = await self._grant_giveaway_reward(guild, winner_id, prize_amount, item_bonus)
            self._save_state()
            if success:
                state["pending_reward"] = None

        self._schedule_winner_announcement(guild_id)

    def _schedule_winner_announcement(self, guild_id):
        delay = self._winner_delay().total_seconds()
        task = asyncio.create_task(self._announce_winner_after_delay(guild_id, delay))
        self._tasks[f"{guild_id}:winner"] = task

    async def _announce_winner_after_delay(self, guild_id, delay):
        await asyncio.sleep(delay)
        guild = self.bot.get_guild(int(guild_id))
        if guild is None:
            return
        state = self._guild_state(guild_id)
        if state.get("last_winner") is None:
            return

        winner_id = state["last_winner"]
        winner_member = guild.get_member(int(winner_id)) or await self.bot.fetch_user(int(winner_id))
        channel = self._get_channel_for_giveaway(guild, guild_id)
        if channel:
            pending = state.get("pending_reward")
            if pending and str(pending.get("user_id")) == str(winner_id):
                await self._credit_pending_reward_if_possible(guild_id, winner_id)

            profile_missing = not await self._profile_exists(guild_id, winner_id)
            item_bonus = pending.get("item_bonus") if pending else None
            if item_bonus is None and state.get("last_prize", 0) <= GIVEAWAY_LOW_PRIZE_THRESHOLD:
                item_bonus = random.choice(GIVEAWAY_BONUS_ITEM_POOL)

            final_message = (
                f"🎊 {winner_member.mention} has won the weekly giveaway! "
                f"Prize: `{state['last_prize']:,}` coins"
            )
            if item_bonus:
                final_message += f" + `{item_bonus}` item bonus."

            if profile_missing:
                final_message += "\nYour profile was missing, so please create your economy profile using `$balance` or another economy command and then your rewards will be credited."
            else:
                final_message += "\nYour rewards have already been credited to your profile."

            await channel.send(final_message)

    def _schedule_giveaway_tasks(self, guild_id, starts_at, closes_at):
        closes_at = self._as_utc(closes_at)
        now = datetime.now(timezone.utc)
        # Reminder before close
        reminder_delay = (closes_at - now - self._reminder_duration()).total_seconds()
        if reminder_delay > 0:
            reminder_task = asyncio.create_task(self._send_reminder(guild_id, reminder_delay))
            self._tasks[f"{guild_id}:reminder"] = reminder_task

        close_delay = max(0, (closes_at - now).total_seconds())
        close_task = asyncio.create_task(self._close_after_delay(guild_id, close_delay))
        self._tasks[f"{guild_id}:close"] = close_task

    async def _send_reminder(self, guild_id, delay):
        await asyncio.sleep(delay)
        guild = self.bot.get_guild(int(guild_id))
        if guild is None:
            return
        state = self._guild_state(guild_id)
        if not state.get("active"):
            return
        channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if channel:
            await channel.send(
                f"{GIVEAWAY_PING_TEXT} Giveaway closes soon! React to the active giveaway message before the entry window ends."
            )

    async def _close_after_delay(self, guild_id, delay):
        await asyncio.sleep(delay)
        await self._close_giveaway(guild_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name != GIVEAWAY_REACTION:
            return

        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        state = self._guild_state(payload.guild_id)
        if not state.get("active"):
            return

        if payload.message_id != state.get("message_id"):
            return

        user_id = str(payload.user_id)
        if user_id not in state["entries"]:
            state["entries"].append(user_id)
            self._save_state()

    @commands.group(name="giveaway", invoke_without_command=True)
    async def giveaway(self, ctx):
        await ctx.send(
            "🎁 Giveaway commands:\n"
            "`$giveaway start` — start a giveaway and create the reaction entry message\n"
            "`$giveaway status` — see current entries and timing\n"
            "`$giveaway reset` — clear the current giveaway state\n"
        )

    def _can_manage_giveaway(self, user):
        if user is None:
            return False
        return user.id in GIVEAWAY_ALLOWED_STARTER_IDS or user_has_admin_access(user)

    @giveaway.command(name="start")
    async def giveaway_start(self, ctx):
        if not self._can_manage_giveaway(ctx.author):
            await ctx.send("🚫 Only the giveaway owner can start a giveaway.")
            return

        guild_id = str(ctx.guild.id)
        state = self._guild_state(guild_id)
        if state.get("active"):
            await ctx.send("⚠️ A giveaway is already active in this server.")
            return

        started_at = datetime.now(timezone.utc)
        closes_at = started_at + self._entry_duration()

        state["active"] = True
        state["entries"] = []
        state["message_id"] = None
        state["channel_id"] = str(ctx.channel.id)
        state["started_at"] = started_at.isoformat()
        state["entry_closes_at"] = closes_at.isoformat()
        state["winner_announced_at"] = None
        state["last_winner"] = None
        state["last_prize"] = 0
        self._save_state()

        ping_message = (
            f"{GIVEAWAY_PING_TEXT} 🎁 Weekly giveaway is live!\n"
            f"Entry window: {self._format_ist(started_at)} to {self._format_ist(closes_at)}\n"
            "React with 🎉 to this message to be added to the giveaway list."
        )

        message = await ctx.send(ping_message)
        await message.add_reaction(GIVEAWAY_REACTION)
        state["message_id"] = message.id
        state["channel_id"] = str(message.channel.id)
        self._save_state()

        # This is the place to change when the giveaway closes in IST.
        self._schedule_giveaway_tasks(guild_id, started_at, closes_at)

        await ctx.send(
            "✅ Giveaway started. The entry message is live and reacting with 🎉 adds a participant."
        )

    @giveaway.command(name="status")
    async def giveaway_status(self, ctx):
        state = self._guild_state(str(ctx.guild.id))
        if not state.get("active"):
            if state.get("last_winner"):
                await ctx.send(
                    f"📊 Last winner: <@{state['last_winner']}>\n"
                    f"Prize: `{state['last_prize']:,}` coins"
                )
                return
            await ctx.send("📊 No giveaway is currently running.")
            return

        started_at = self._as_utc(datetime.fromisoformat(state["started_at"])) if state.get("started_at") else None
        closes_at = self._as_utc(datetime.fromisoformat(state["entry_closes_at"])) if state.get("entry_closes_at") else None

        embed = discord.Embed(
            title="🎁 Live Giveaway",
            description="Participants can join by reacting with 🎉 to the giveaway message.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Entrants", value=str(len(state.get("entries", []))), inline=True)
        embed.add_field(name="Entry window", value=f"{self._format_ist(started_at)} to {self._format_ist(closes_at)}", inline=False)
        embed.add_field(name="Prize Range", value=f"{GIVEAWAY_PRIZE_MIN:,} - {GIVEAWAY_PRIZE_MAX:,} coins", inline=True)
        embed.add_field(name="Winner reveal delay", value=f"{GIVEAWAY_WINNER_ANNOUNCEMENT_DELAY_HOURS} hours after close", inline=True)
        await ctx.send(embed=embed)

    @giveaway.command(name="reset")
    async def giveaway_reset(self, ctx):
        if not self._can_manage_giveaway(ctx.author):
            await ctx.send("🚫 Only the giveaway owner can reset a giveaway.")
            return

        state = self._guild_state(str(ctx.guild.id))
        state["active"] = False
        state["entries"] = []
        state["message_id"] = None
        state["channel_id"] = None
        state["started_at"] = None
        state["entry_closes_at"] = None
        state["winner_announced_at"] = None
        state["last_winner"] = None
        state["last_prize"] = 0
        self._save_state()
        await ctx.send("✅ Giveaway state reset.")


async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))
