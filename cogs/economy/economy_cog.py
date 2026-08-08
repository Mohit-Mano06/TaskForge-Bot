import discord
from discord.ext import commands
from cogs.economy import db

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _check_db(self):
        """Helper to ensure db_pool is initialized."""
        return hasattr(self.bot, 'db_pool') and self.bot.db_pool is not None

    @commands.command(name="balance", aliases=["bal"])
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

async def setup(bot):
    await bot.add_cog(Economy(bot))
