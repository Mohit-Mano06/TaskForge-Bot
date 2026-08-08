import discord
from discord.ext import commands
from cogs.economy import db
import json
import os
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()
        self.text_cooldowns = {}
        self.vc_sessions = {}

    def _load_config(self):
        try:
            with open("data/economy_config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading economy_config.json: {e}")
            return {
                "text_activity": {"cooldown_seconds": 60, "min_length": 5, "reward_min": 2, "reward_max": 5, "xp_min": 1, "xp_max": 3},
                "vc_activity": {"interval_minutes": 10, "reward_per_interval": 5, "xp_per_interval": 2}
            }

    def _check_db(self):
        """Helper to ensure db_pool is initialized."""
        return hasattr(self.bot, 'db_pool') and self.bot.db_pool is not None

    @commands.command(name="balance", aliases=["bal", "profile"])
    async def balance(self, ctx, member: discord.Member = None):
        """Displays the wallet, bank balance, level, and XP of a user."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        member = member or ctx.author
        if member.bot:
            await ctx.send("🤖 Bots do not have an economy profile.")
            return

        try:
            user_data = await db.get_or_create_user(self.bot.db_pool, member.id, ctx.guild.id)
            
            embed = discord.Embed(
                title=f"💰 {member.display_name}'s Economy Profile",
                color=discord.Color.gold(),
                description=f"Here is a summary of the virtual assets for {member.mention}:"
            )
            embed.add_field(name="💰 Wallet", value=f"🪙 `{user_data['wallet']:,}` coins", inline=True)
            embed.add_field(name="🏦 Bank", value=f"🪙 `{user_data['bank']:,}` coins", inline=True)
            embed.add_field(name="💵 Total Wealth", value=f"🪙 `{user_data['wallet'] + user_data['bank']:,}` coins", inline=True)
            embed.add_field(name="⭐ Level", value=f"`{user_data['level']}`", inline=True)
            embed.add_field(name="✨ XP", value=f"`{user_data['xp']}` XP", inline=True)
            
            streak_text = f"🔥 Streak: {user_data['daily_streak']} days" if user_data['daily_streak'] > 0 else "💨 No active streak"
            embed.set_footer(text=streak_text)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ An error occurred while retrieving the balance: {e}")

    @commands.command(name="deposit", aliases=["dep"])
    async def deposit(self, ctx, amount: str):
        """Deposits coins from your wallet into your bank."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        try:
            user_data = await db.get_or_create_user(self.bot.db_pool, ctx.author.id, ctx.guild.id)
            wallet = user_data["wallet"]

            if wallet <= 0:
                await ctx.send("❌ You don't have any coins in your wallet to deposit.")
                return

            if amount.lower() in ["all", "max"]:
                dep_amount = wallet
            else:
                try:
                    dep_amount = int(amount)
                except ValueError:
                    await ctx.send("❌ Please specify a valid amount to deposit (a positive integer, or 'all').")
                    return

            if dep_amount <= 0:
                await ctx.send("❌ You must deposit at least 1 coin.")
                return

            if dep_amount > wallet:
                await ctx.send(f"❌ You only have 🪙 `{wallet:,}` coins in your wallet.")
                return

            # Update database
            await db.update_balances(
                self.bot.db_pool,
                ctx.author.id,
                ctx.guild.id,
                wallet_change=-dep_amount,
                bank_change=dep_amount,
                tx_type="DEPOSIT",
                tx_desc=f"Deposited {dep_amount} coins to bank"
            )

            await ctx.send(f"✅ Deposited 🪙 `{dep_amount:,}` coins into your bank!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred during the transaction: {e}")

    @commands.command(name="withdraw", aliases=["with"])
    async def withdraw(self, ctx, amount: str):
        """Withdraws coins from your bank into your wallet."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        try:
            user_data = await db.get_or_create_user(self.bot.db_pool, ctx.author.id, ctx.guild.id)
            bank = user_data["bank"]

            if bank <= 0:
                await ctx.send("❌ You don't have any coins in your bank to withdraw.")
                return

            if amount.lower() in ["all", "max"]:
                with_amount = bank
            else:
                try:
                    with_amount = int(amount)
                except ValueError:
                    await ctx.send("❌ Please specify a valid amount to withdraw (a positive integer, or 'all').")
                    return

            if with_amount <= 0:
                await ctx.send("❌ You must withdraw at least 1 coin.")
                return

            if with_amount > bank:
                await ctx.send(f"❌ You only have 🪙 `{bank:,}` coins in your bank.")
                return

            # Update database
            await db.update_balances(
                self.bot.db_pool,
                ctx.author.id,
                ctx.guild.id,
                wallet_change=with_amount,
                bank_change=-with_amount,
                tx_type="WITHDRAW",
                tx_desc=f"Withdrew {with_amount} coins from bank"
            )

            await ctx.send(f"✅ Withdrew 🪙 `{with_amount:,}` coins from your bank!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred during the transaction: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
            
        if not self._check_db():
            return
            
        cfg = self.config.get("text_activity", {})
        if len(message.content) < cfg.get("min_length", 5):
            return
            
        user_id = str(message.author.id)
        now = time.time()
        
        # Cooldown check
        last_time = self.text_cooldowns.get(user_id, 0)
        if now - last_time < cfg.get("cooldown_seconds", 60):
            return
            
        self.text_cooldowns[user_id] = now
        
        # Calculate rewards
        coin_reward = random.randint(cfg.get("reward_min", 2), cfg.get("reward_max", 5))
        xp_reward = random.randint(cfg.get("xp_min", 1), cfg.get("xp_max", 3))
        
        try:
            await db.get_or_create_user(self.bot.db_pool, message.author.id, message.guild.id)
            await db.update_balances(
                self.bot.db_pool, 
                message.author.id, 
                message.guild.id, 
                coin_reward, 0, 
                "TEXT_ACTIVITY", "Earned from text activity"
            )
            await db.update_xp(
                self.bot.db_pool,
                message.author.id,
                message.guild.id,
                xp_reward
            )
        except Exception as e:
            print(f"Error rewarding text activity: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return
            
        if not self._check_db():
            return
            
        guild_id = str(member.guild.id)
        
        # Handle before channel (someone leaving or switching)
        if before.channel is not None and before.channel != after.channel:
            humans_before = [m for m in before.channel.members if not m.bot]
            if len(humans_before) < 2:
                # If less than 2 humans remain, end sessions for everyone who was tracking
                await self._end_vc_session(guild_id, member)
                for remaining_member in humans_before:
                    await self._end_vc_session(guild_id, remaining_member)
            else:
                # Still enough people, just end the session for the leaving member
                await self._end_vc_session(guild_id, member)
                
        # Handle after channel (someone joining or switching)
        if after.channel is not None and after.channel != before.channel:
            humans_after = [m for m in after.channel.members if not m.bot]
            if len(humans_after) >= 2:
                # Ensure all humans in the channel have a session started
                for m in humans_after:
                    session_key = (guild_id, str(m.id))
                    if session_key not in self.vc_sessions:
                        self.vc_sessions[session_key] = time.time()

    async def _end_vc_session(self, guild_id, member):
        session_key = (str(guild_id), str(member.id))
        if session_key in self.vc_sessions:
            join_time = self.vc_sessions.pop(session_key)
            duration_minutes = (time.time() - join_time) / 60.0
            
            cfg = self.config.get("vc_activity", {})
            interval = cfg.get("interval_minutes", 10)
            intervals_completed = int(duration_minutes // interval)
            
            if intervals_completed > 0:
                coin_reward = intervals_completed * cfg.get("reward_per_interval", 5)
                xp_reward = intervals_completed * cfg.get("xp_per_interval", 2)
                
                try:
                    await db.get_or_create_user(self.bot.db_pool, member.id, member.guild.id)
                    await db.update_balances(
                        self.bot.db_pool, 
                        member.id, 
                        member.guild.id, 
                        coin_reward, 0, 
                        "VC_ACTIVITY", f"Earned from VC activity ({duration_minutes:.1f} mins)"
                    )
                    await db.update_xp(
                        self.bot.db_pool,
                        member.id,
                        member.guild.id,
                        xp_reward
                    )
                except Exception as e:
                    print(f"Error rewarding VC activity: {e}")


async def setup(bot):
    await bot.add_cog(Economy(bot))
