import discord
from discord.ext import commands
from cogs.economy import db
import json
import os
import time
import random
from datetime import datetime, timezone
from cogs.monitoring.metrics import (
    taskforge_economy_transactions_total,
    taskforge_vc_active_sessions,
    taskforge_vc_reward_coins_total,
)
from cogs.admin.config import user_is_owner

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self._load_config()
        self.text_cooldowns = {}
        self.vc_sessions = {}

    def _load_config(self):
        try:
            with open("data/economy_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading economy_config.json: {e}")
            return {
                "text_activity": {"cooldown_seconds": 60, "min_length": 5, "reward_min": 2, "reward_max": 5, "xp_min": 1, "xp_max": 3},
                "vc_activity": {"interval_minutes": 10, "reward_per_interval": 5, "xp_per_interval": 2},
                "starter_bonus": {"enabled": True, "wallet": 100}
            }

    def _check_db(self):
        """Helper to ensure db_pool is initialized."""
        return hasattr(self.bot, 'db_pool') and self.bot.db_pool is not None

    async def _ensure_starter_bonus(self, ctx):
        cfg = self.config.get("starter_bonus", {})
        if not cfg.get("enabled", True):
            user_data = await db.get_or_create_user(self.bot.db_pool, ctx.author.id, ctx.guild.id)
            await self._credit_pending_giveaway_reward(ctx.guild, ctx.author)
            return user_data, False

        amount = int(cfg.get("wallet", 100))
        user_data, granted = await db.grant_starter_bonus(
            self.bot.db_pool,
            ctx.author.id,
            ctx.guild.id,
            amount
        )
        await self._credit_pending_giveaway_reward(ctx.guild, ctx.author)
        return user_data, granted

    async def _credit_pending_giveaway_reward(self, guild, member):
        giveaway_cog = self.bot.get_cog("GiveawayCog")
        if giveaway_cog is None:
            return

        await giveaway_cog._credit_pending_reward_if_possible(str(guild.id), str(member.id))

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx, member: discord.Member | None = None):
        """Displays the wallet, bank balance, level, and XP of a user."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        member = member or ctx.author
        if member.bot:
            await ctx.send("🤖 Bots do not have an economy profile.")
            return

        try:
            starter_granted = False
            if member.id == ctx.author.id:
                user_data, starter_granted = await self._ensure_starter_bonus(ctx)
            else:
                user_data = await db.get_or_create_user(self.bot.db_pool, str(member.id), ctx.guild.id)
            
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
            if starter_granted:
                amount = self.config.get("starter_bonus", {}).get("wallet", 100)
                embed.add_field(name="Starter Bonus", value=f"`{amount:,}` coins added to your wallet", inline=False)
            
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
            user_data, starter_granted = await self._ensure_starter_bonus(ctx)
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
            taskforge_economy_transactions_total.labels(type="deposit").inc()

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
            user_data, starter_granted = await self._ensure_starter_bonus(ctx)
            bank = user_data["bank"]

            if bank <= 0:
                if starter_granted:
                    bonus = self.config.get("starter_bonus", {}).get("wallet", 100)
                    await ctx.send(f"Starter bonus received: `{bonus:,}` coins in your wallet.\nYou don't have any coins in your bank to withdraw.")
                    return
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
            taskforge_economy_transactions_total.labels(type="withdraw").inc()

            await ctx.send(f"✅ Withdrew 🪙 `{with_amount:,}` coins from your bank!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred during the transaction: {e}")

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: discord.Member | None = None):
        """Displays the inventory of a user."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        member = member or ctx.author
        if member.bot:
            await ctx.send("🤖 Bots do not have an inventory.")
            return

        try:
            items = await db.get_inventory(self.bot.db_pool, str(member.id), ctx.guild.id)
            
            if not items:
                await ctx.send(f"🎒 {member.display_name}'s inventory is currently empty.")
                return

            embed = discord.Embed(
                title=f"🎒 {member.display_name}'s Inventory",
                color=discord.Color.blue(),
                description="A list of all items currently held by the user."
            )

            inventory_list = []
            for item_data in items:
                item_id = item_data['item_id']
                quantity = item_data['quantity']
                
                # Get item details from config
                item_details = self.config.get("items", {}).get(item_id)
                if item_details:
                    name = item_details.get("name", item_id)
                    inventory_list.append(f"{name} ×{quantity}")
                else:
                    inventory_list.append(f"Unknown Item ({item_id}) ×{quantity}")

            embed.add_field(name="Items", value="\n".join(inventory_list), inline=False)
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ An error occurred while retrieving the inventory: {e}")

    def _normalize_item_id(self, item_text: str) -> str:
        return item_text.strip().lower().replace(" ", "_")

    def _resolve_item_id(self, item_text: str) -> str:
        self.config = self._load_config()
        requested = self._normalize_item_id(item_text)

        if self._get_item(requested):
            return requested

        for item_id, item in self.config.get("items", {}).items():
            aliases = item.get("aliases", [])
            if not aliases:
                continue

            normalized_aliases = [self._normalize_item_id(alias) for alias in aliases]
            if requested in normalized_aliases:
                return item_id

        return requested

    def _get_item(self, item_id: str):
        self.config = self._load_config()
        return self.config.get("items", {}).get(item_id)

    def _get_currency_symbol(self) -> str:
        self.config = self._load_config()
        return self.config.get("shop", {}).get("currency_symbol", "🪙")

    def _format_shop_price(self, price_value, currency: str) -> str:
        price = int(price_value or 0)
        if price <= 0:
            return "Unavailable"
        return f"{currency} {price:,}"

    @staticmethod
    def _normalize_shop_category(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if normalized in ["all", "any", "everything"]:
            return "all"
        if normalized in ["collectible", "collectibles"]:
            return "collectible"
        if normalized in ["cosmetic", "cosmetics"]:
            return "cosmetic"
        return None

    def _build_shop_page_embed(self, catalog, page, query=None, currency="🪙", page_size=6, category="all"):
        total_pages = max(1, (len(catalog) + page_size - 1) // page_size)
        valid_page = max(1, min(int(page), total_pages))
        start = (valid_page - 1) * page_size
        end = start + page_size
        visible_items = catalog[start:end]

        cards = []
        for index, (item_key, item) in enumerate(visible_items, start=start + 1):
            item_name = item.get("name", item_key)
            item_type = str(item.get("type", "collectible")).capitalize()
            buy_price = int(item.get("buy_price", 0) or 0)
            price_text = "Unavailable" if buy_price <= 0 else f"{currency} {buy_price:,}"
            description = item.get("description", "No description.")
            cards.append(
                f"**{index}. {item_name}**\n"
                f"`{item_type}` • {price_text}\n"
                f"_{description}_"
            )

        page_nav = " ".join(
            f"[{idx}]" if idx == valid_page else str(idx)
            for idx in range(1, total_pages + 1)
        )

        embed = discord.Embed(
            title="🛒 TaskForge Shop",
            description="Use `$buy <item_id> <quantity>` to purchase and `$sell <item_id> <quantity>` to sell items.\nSearch: `$shop search relic`   Page: `$shop page 2`",
            color=discord.Color.blue()
        )
        if not cards:
            cards = ["No items available on this page."]

        embed.add_field(
            name=f"Available Items • Page {valid_page}/{total_pages} • {category.title()}",
            value="\n\n".join(cards),
            inline=False
        )
        embed.add_field(name="Page Buttons", value=page_nav, inline=False)
        if query:
            embed.set_footer(text=f"Search results: {query} | Use $shop page <number>")
        else:
            embed.set_footer(text="Use $shop page <number>, $shop next, $shop prev, or $shop cosmetics")
        return embed

    def _get_shop_catalog(self, category: str = "all"):
        self.config = self._load_config()
        shop_config = self.config.get("shop", {})
        show_daily_only = shop_config.get("show_daily_only", False)
        item_order = shop_config.get("default_order", list(self.config.get("items", {}).keys()))
        catalog = []
        normalized_category = self._normalize_shop_category(category) or "all"

        for item_key in item_order:
            item = self._get_item(item_key)
            if not item:
                continue
            if item.get("daily_only", False) and not show_daily_only:
                continue
            item_type = str(item.get("type", "collectible")).lower()
            if normalized_category != "all" and item_type != normalized_category:
                continue
            catalog.append((item_key, item))

        return catalog

    def _search_shop_items(self, query: str, category: str = "all"):
        term = self._normalize_item_id(query or "")
        if not term:
            return []

        matches = []
        for item_key, item in self._get_shop_catalog(category):
            searchable = [
                item_key,
                item.get("name", ""),
                item.get("description", ""),
                *item.get("aliases", [])
            ]
            normalized_values = [self._normalize_item_id(str(value)) for value in searchable if value]
            if any(term in value for value in normalized_values):
                matches.append((item_key, item))

        return matches

    @commands.command(name="shop")
    async def shop(self, ctx, *args):
        """Displays the shop, supports item lookup, pagination, search, and category filters."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        self.config = self._load_config()
        shop_config = self.config.get("shop", {})
        currency = shop_config.get("currency_symbol", "🪙")
        show_daily_only = shop_config.get("show_daily_only", False)
        page_size = 6

        category = "all"
        filtered_args = []
        for token in args:
            normalized_category = self._normalize_shop_category(token)
            if normalized_category:
                category = normalized_category
            else:
                filtered_args.append(token)

        args = filtered_args

        if not args:
            catalog = self._get_shop_catalog(category)
            page = 1
            query = None
        elif args[0].lower() in ["search", "find", "lookup"]:
            query = " ".join(args[1:]).strip()
            if not query:
                await ctx.send("❌ Please add a search term, for example: `$shop search relic`.")
                return
            catalog = self._search_shop_items(query, category)
            page = 1
            if not catalog:
                await ctx.send(f"❌ No shop items match `{query}` in the `{category}` category.")
                return
        elif args[0].lower() in ["page", "p"]:
            try:
                page = int(args[1]) if len(args) > 1 else 1
            except ValueError:
                await ctx.send("❌ Please use a valid page number, for example: `$shop page 2`.")
                return
            catalog = self._get_shop_catalog(category)
            query = None
        elif args[0].lower() in ["next", "n"]:
            catalog = self._get_shop_catalog(category)
            total_pages = max(1, (len(catalog) + page_size - 1) // page_size)
            page = 2 if total_pages > 1 else 1
            query = None
        elif args[0].lower() in ["prev", "previous", "back", "b"]:
            catalog = self._get_shop_catalog(category)
            page = 1
            query = None
        elif args[0].lower() in ["first", "start"]:
            catalog = self._get_shop_catalog(category)
            page = 1
            query = None
        elif args[0].lower() in ["last"]:
            catalog = self._get_shop_catalog(category)
            page = max(1, len(catalog) // page_size + (1 if len(catalog) % page_size else 0))
            query = None
        elif args[0].isdigit():
            page = int(args[0])
            catalog = self._get_shop_catalog(category)
            query = None
        else:
            lookup = " ".join(args)
            normalized_id = self._resolve_item_id(lookup)
            item = self._get_item(normalized_id)
            if not item or (item.get("daily_only", False) and not show_daily_only):
                matches = self._search_shop_items(lookup, category)
                if not matches:
                    await ctx.send("❌ That item is not available in the shop.")
                    return
                catalog = matches
                page = 1
                query = lookup
            else:
                embed = discord.Embed(
                    title=f"🛒 {item.get('name', normalized_id)}",
                    description=item.get("description", "No description available."),
                    color=discord.Color.blue()
                )
                embed.add_field(name="Rarity", value=item.get("rarity", "Unknown"), inline=True)
                embed.add_field(name="Buy Price", value=self._format_shop_price(item.get("buy_price", 0), currency), inline=True)
                embed.add_field(name="Sell Price", value=self._format_shop_price(item.get("sell_price", 0), currency), inline=True)
                embed.add_field(name="Type", value=str(item.get("type", "collectible")).capitalize(), inline=True)
                embed.add_field(name="Daily Only", value="Yes" if item.get("daily_only", False) else "No", inline=True)
                embed.set_footer(text="Use $shop page 2 or $shop search relic to browse more items.")
                await ctx.send(embed=embed)
                return

        if not catalog:
            await ctx.send(f"❌ No shop items are available in the `{category}` category.")
            return

        total_pages = max(1, (len(catalog) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        embed = self._build_shop_page_embed(catalog, page, query=query, currency=currency, page_size=page_size, category=category)
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, item_id: str, quantity: int = 1):
        """Purchase shop items using wallet coins."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        if quantity <= 0:
            await ctx.send("❌ Quantity must be at least 1.")
            return

        self.config = self._load_config()
        item_key = self._resolve_item_id(item_id)
        item = self._get_item(item_key)
        if not item or item.get("daily_only", False):
            await ctx.send("❌ That item is not available for purchase.")
            return

        price = int(item.get("buy_price", 0))
        if price <= 0:
            await ctx.send("❌ This item cannot be purchased.")
            return

        total_cost = price * quantity
        currency = self._get_currency_symbol()
        user_data, _ = await self._ensure_starter_bonus(ctx)
        if user_data["wallet"] < total_cost:
            await ctx.send(f"❌ You need {currency} `{total_cost:,}` but only have {currency} `{user_data['wallet']:,}`.")
            return

        try:
            await db.update_balances(
                self.bot.db_pool,
                ctx.author.id,
                ctx.guild.id,
                wallet_change=-total_cost,
                bank_change=0,
                tx_type="SHOP_PURCHASE",
                tx_desc=f"Bought {quantity}x {item.get('name')}"
            )
            await db.add_item_to_inventory(self.bot.db_pool, ctx.author.id, ctx.guild.id, item_key, quantity)
            taskforge_economy_transactions_total.labels(type="purchase").inc()
            await ctx.send(f"✅ Purchased {quantity}x {item.get('name')} for {currency} `{total_cost:,}`.")
        except Exception as e:
            await ctx.send(f"❌ Failed to complete purchase: {e}")

    @commands.command(name="sell")
    async def sell(self, ctx, item_id: str, quantity: int = 1):
        """Sell an item from your inventory for coins."""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        if quantity <= 0:
            await ctx.send("❌ Quantity must be at least 1.")
            return

        self.config = self._load_config()
        item_key = self._resolve_item_id(item_id)
        item = self._get_item(item_key)
        if not item:
            await ctx.send("❌ That item does not exist.")
            return

        sell_price = int(item.get("sell_price", 0))
        if sell_price <= 0:
            await ctx.send("❌ This item cannot be sold.")
            return

        inventory = await db.get_inventory(self.bot.db_pool, str(ctx.author.id), ctx.guild.id)
        owned = next((entry for entry in inventory if entry["item_id"] == item_key), None)
        if not owned or owned["quantity"] < quantity:
            await ctx.send(f"❌ You don't have enough of {item.get('name')} to sell.")
            return

        total_gain = sell_price * quantity
        currency = self._get_currency_symbol()
        try:
            await db.remove_item_from_inventory(self.bot.db_pool, ctx.author.id, ctx.guild.id, item_key, quantity)
            await db.update_balances(
                self.bot.db_pool,
                ctx.author.id,
                ctx.guild.id,
                wallet_change=total_gain,
                bank_change=0,
                tx_type="ITEM_SALE",
                tx_desc=f"Sold {quantity}x {item.get('name')}"
            )
            taskforge_economy_transactions_total.labels(type="sale").inc()
            await ctx.send(f"✅ Sold {quantity}x {item.get('name')} for {currency} `{total_gain:,}`.")
        except ValueError as e:
            await ctx.send(f"❌ {e}")
        except Exception as e:
            await ctx.send(f"❌ Failed to complete sale: {e}")

    @commands.command(name="reset_economy", aliases=["reset"])
    async def reset_economy(self, ctx, target: str | None = None):
        """Wipes all economy data for everyone. Owner only."""
        if not user_is_owner(ctx.author):
            await ctx.send("❌ You don't have permissions to use this command.")
            return

        if target and target.lower() != "economy":
            await ctx.send("❌ Invalid reset target. Did you mean `$reset economy`?")
            return

        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        # Guardrail: Confirmation step
        confirm_embed = discord.Embed(
            title="⚠️ WARNING: ECONOMY RESET",
            description="This will **PERMANENTLY DELETE** all wallet balances, bank accounts, inventories, and transaction logs for **EVERYONE** in the database.\n\nThis action cannot be undone.",
            color=discord.Color.red()
        )
        confirm_embed.set_footer(text="Type `$confirm_reset` to proceed.")
        await ctx.send(embed=confirm_embed)

        def check(m):
            return m.author == ctx.author and m.content == "$confirm_reset"

        try:
            # Wait for confirmation message
            await self.bot.wait_for("message", check=check, timeout=30.0)
            
            await db.reset_economy_data(self.bot.db_pool)
            await ctx.send("✅ Economy has been successfully reset. Everyone is starting from scratch!")
        except Exception:
            await ctx.send("❌ Reset cancelled or timed out. No data was deleted.")

    def _get_weighted_reward_tier(self):
        """Returns a reward tier based on configured probabilities."""
        probs = self.config.get("daily_rewards", {}).get("probabilities", {})
        if not probs:
            return "common"
        
        # Create a list of tiers based on weights
        tiers = []
        for tier, weight in probs.items():
            tiers.extend([tier] * weight)
        
        return random.choice(tiers)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily reward and maintain your streak!"""
        if not self._check_db():
            await ctx.send("❌ PostgreSQL database connection is not configured/available.")
            return

        try:
            user_data, starter_granted = await self._ensure_starter_bonus(ctx)
            last_daily = user_data.get("last_daily")
            now = datetime.now(timezone.utc)

            # Check if already claimed today
            if last_daily:
                # If last_daily is a datetime object (from asyncpg)
                if last_daily.date() == now.date():
                    await ctx.send("❌ You've already claimed your daily reward today! Come back tomorrow.")
                    return

                # Check for streak reset (more than 24h + 12h grace period)
                # If last claim was more than 48 hours ago, reset streak
                diff = now - last_daily
                if diff.days >= 2:
                    await db.update_balances(
                        self.bot.db_pool,
                        ctx.author.id,
                        ctx.guild.id,
                        wallet_change=0,
                        bank_change=0,
                        tx_type="STREAK_RESET",
                        tx_desc="Daily streak reset due to inactivity"
                    )
                    # We need a way to reset the streak in DB. 
                    # I'll add a helper or use a direct update.
                    async with self.bot.db_pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE public.economy_users SET daily_streak = 0 WHERE user_id = $1 AND guild_id = $2",
                            str(ctx.author.id), str(ctx.guild.id)
                        )
                    user_data['daily_streak'] = 0

            # Determine reward tier
            tier = self._get_weighted_reward_tier()
            tier_cfg = self.config.get("daily_rewards", {}).get("rewards", {}).get(tier, {})
            
            coins = random.randint(tier_cfg.get("coins_min", 50), tier_cfg.get("coins_max", 200))
            xp = random.randint(tier_cfg.get("xp_min", 10), tier_cfg.get("xp_max", 30))
            
            # Handle items
            possible_items = tier_cfg.get("items", [])
            rewarded_item = None
            if possible_items:
                rewarded_item = random.choice(possible_items)

            # Update streak
            streak_increment = 1
            # (Optional: add bonus for milestones like 7 days)
            
            # Update DB
            await db.claim_daily(
                self.bot.db_pool,
                ctx.author.id,
                ctx.guild.id,
                coins,
                xp,
                streak_increment
            )
            taskforge_economy_transactions_total.labels(type="daily_reward").inc()
            
            # Update XP separately using existing function
            await db.update_xp(self.bot.db_pool, ctx.author.id, ctx.guild.id, xp)
            
            # Add item if rewarded
            if rewarded_item:
                await db.add_item_to_inventory(self.bot.db_pool, ctx.author.id, ctx.guild.id, rewarded_item)

            # Build response
            item_name = self.config.get("items", {}).get(rewarded_item, {}).get("name", "Unknown Item") if rewarded_item else None
            
            embed = discord.Embed(
                title="🎁 Daily Crate Opened!",
                description=f"Congratulations {ctx.author.mention}, you've claimed your daily reward!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Coins", value=f"`{coins:,}`", inline=True)
            embed.add_field(name="✨ XP", value=f"`{xp}`", inline=True)
            
            if item_name:
                embed.add_field(name="📦 Item", value=f"{item_name}", inline=False)
            
            new_streak = user_data['daily_streak'] + 1
            embed.set_footer(text=f"🔥 Daily Streak: {new_streak} days")
            
            await ctx.send(embed=embed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ An error occurred while claiming your daily reward: {e}")

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
            taskforge_economy_transactions_total.labels(type="text_reward").inc()
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
                taskforge_vc_active_sessions.set(len(self.vc_sessions))

    async def _end_vc_session(self, guild_id, member):
        session_key = (str(guild_id), str(member.id))
        if session_key in self.vc_sessions:
            join_time = self.vc_sessions.pop(session_key)
            taskforge_vc_active_sessions.set(len(self.vc_sessions))
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
                    taskforge_economy_transactions_total.labels(type="vc_reward").inc()
                    taskforge_vc_reward_coins_total.inc(coin_reward)
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
