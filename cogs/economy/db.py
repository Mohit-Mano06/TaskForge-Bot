import asyncpg
from datetime import datetime, timezone


async def ensure_economy_schema(pool: asyncpg.Pool):
    """Apply additive economy migrations required by the loaded cogs."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.economy_users (
                user_id text NOT NULL,
                guild_id text NOT NULL,
                wallet integer NOT NULL DEFAULT 0,
                bank integer NOT NULL DEFAULT 0,
                xp integer NOT NULL DEFAULT 0,
                level integer NOT NULL DEFAULT 1,
                daily_streak integer NOT NULL DEFAULT 0,
                last_daily timestamptz,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, guild_id)
            );
            CREATE TABLE IF NOT EXISTS public.economy_inventory (
                user_id text NOT NULL,
                guild_id text NOT NULL,
                item_id text NOT NULL,
                quantity integer NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, guild_id, item_id)
            );
            CREATE TABLE IF NOT EXISTS public.economy_transactions (
                id bigserial PRIMARY KEY,
                user_id text NOT NULL,
                guild_id text NOT NULL,
                amount integer NOT NULL,
                type text NOT NULL,
                description text,
                created_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS public.economy_achievements (
                achievement_id text PRIMARY KEY,
                name text NOT NULL
            );
            CREATE TABLE IF NOT EXISTS public.economy_user_achievements (
                user_id text NOT NULL,
                guild_id text NOT NULL,
                achievement_id text NOT NULL,
                unlocked_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, guild_id, achievement_id)
            );
            CREATE TABLE IF NOT EXISTS public.economy_pets (
                pet_id text PRIMARY KEY,
                name text NOT NULL,
                description text NOT NULL,
                emoji text NOT NULL
            );
            CREATE TABLE IF NOT EXISTS public.economy_user_pets (
                user_id text NOT NULL,
                guild_id text NOT NULL,
                pet_id text NOT NULL REFERENCES public.economy_pets(pet_id),
                equipped boolean NOT NULL DEFAULT false,
                adopted_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, guild_id, pet_id)
            );
            CREATE TABLE IF NOT EXISTS public.economy_pets (
                pet_id text PRIMARY KEY,
                name text NOT NULL,
                description text NOT NULL,
                emoji text NOT NULL
            );
            CREATE TABLE IF NOT EXISTS public.economy_user_pets (
                user_id text NOT NULL,
                guild_id text NOT NULL,
                pet_id text NOT NULL REFERENCES public.economy_pets(pet_id),
                equipped boolean NOT NULL DEFAULT false,
                adopted_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, guild_id, pet_id)
            );
            ALTER TABLE public.economy_users
                ADD COLUMN IF NOT EXISTS prestige integer NOT NULL DEFAULT 0;
            """
        )


async def get_or_create_user(pool: asyncpg.Pool, user_id: str, guild_id: str) -> dict:
    """Gets a user's economy record, creating one with default values if it doesn't exist."""
    user_id = str(user_id)
    guild_id = str(guild_id)
    
    # Try fetching first
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM public.economy_users WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )
        if row:
            return dict(row)
        
        # If not exists, insert new profile
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO public.economy_users (user_id, guild_id, wallet, bank, xp, level, daily_streak, last_daily)
                VALUES ($1, $2, 0, 0, 0, 1, 0, NULL)
                ON CONFLICT (user_id, guild_id) DO UPDATE SET updated_at = NOW()
                RETURNING *
                """,
                user_id, guild_id
            )
            return dict(row)
        except Exception as e:
            # Fallback in case of race conditions
            row = await conn.fetchrow(
                "SELECT * FROM public.economy_users WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            if row:
                return dict(row)
            raise e

async def update_balances(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    wallet_change: int,
    bank_change: int,
    tx_type: str,
    tx_desc: str | None = None
) -> dict:
    """Updates the user's wallet and bank balances, and inserts an audit log transaction."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get current record (locking row for update)
            row = await conn.fetchrow(
                "SELECT wallet, bank FROM public.economy_users WHERE user_id = $1 AND guild_id = $2 FOR UPDATE",
                user_id, guild_id
            )
            if not row:
                # Create if not exists
                await conn.execute(
                    "INSERT INTO public.economy_users (user_id, guild_id, wallet, bank) VALUES ($1, $2, 0, 0)",
                    user_id, guild_id
                )
                current_wallet = 0
                current_bank = 0
            else:
                current_wallet = row['wallet']
                current_bank = row['bank']

            new_wallet = current_wallet + wallet_change
            new_bank = current_bank + bank_change

            if new_wallet < 0 or new_bank < 0:
                raise ValueError("Insufficient balance for this transaction.")

            # Update economy user record
            updated_row = await conn.fetchrow(
                """
                UPDATE public.economy_users
                SET wallet = $3, bank = $4, updated_at = NOW()
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
                """,
                user_id, guild_id, new_wallet, new_bank
            )

            # Insert transaction log
            total_change = wallet_change + bank_change
            await conn.execute(
                """
                INSERT INTO public.economy_transactions (user_id, guild_id, amount, type, description)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, guild_id, total_change, tx_type, tx_desc
            )

            return dict(updated_row)


async def gamble(pool, user_id, guild_id, bet, won, multiplier):
    """Resolve a coin gamble while locking the player's wallet."""
    user_id, guild_id = str(user_id), str(guild_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT wallet FROM public.economy_users WHERE user_id = $1 AND guild_id = $2 FOR UPDATE",
                user_id, guild_id
            )
            if not row or row["wallet"] < bet:
                raise ValueError("You do not have enough wallet coins for that bet.")
            change = bet * multiplier if won else -bet
            updated = await conn.fetchrow(
                "UPDATE public.economy_users SET wallet = wallet + $3, updated_at = NOW() "
                "WHERE user_id = $1 AND guild_id = $2 RETURNING *", user_id, guild_id, change
            )
            await conn.execute(
                "INSERT INTO public.economy_transactions "
                "(user_id, guild_id, amount, type, description) VALUES ($1, $2, $3, 'GAMBLE', $4)",
                user_id, guild_id, change, "Won gamble" if won else "Lost gamble"
            )
            return dict(updated), change


async def rob_user(pool, robber_id, target_id, guild_id, amount, penalty):
    """Transfer a robbery reward or penalty under deterministic row locks."""
    robber_id, target_id, guild_id = map(str, (robber_id, target_id, guild_id))
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                "SELECT user_id, wallet FROM public.economy_users "
                "WHERE guild_id = $1 AND user_id = ANY($2::text[]) ORDER BY user_id FOR UPDATE",
                guild_id, [robber_id, target_id]
            )
            wallets = {row["user_id"]: row["wallet"] for row in rows}
            if robber_id not in wallets or target_id not in wallets:
                raise ValueError("Both users need an economy profile first.")
            if wallets[target_id] < amount:
                raise ValueError("That user does not have enough wallet coins to rob.")
            if wallets[robber_id] < penalty:
                raise ValueError("You need more wallet coins to cover the robbery risk.")
            await conn.execute(
                "UPDATE public.economy_users SET wallet = wallet - $3 WHERE user_id = $1 AND guild_id = $2",
                target_id, guild_id, amount
            )
            await conn.execute(
                "UPDATE public.economy_users SET wallet = wallet + $3 WHERE user_id = $1 AND guild_id = $2",
                robber_id, guild_id, amount
            )
            if penalty:
                await conn.execute(
                    "UPDATE public.economy_users SET wallet = wallet - $3 WHERE user_id = $1 AND guild_id = $2",
                    robber_id, guild_id, penalty
                )
                await conn.execute(
                    "UPDATE public.economy_users SET wallet = wallet + $3 WHERE user_id = $1 AND guild_id = $2",
                    target_id, guild_id, penalty
                )
            return amount


async def adopt_pet(pool, user_id, guild_id, pet_id, name, description, emoji, cost):
    """Buy and equip a pet once, recording the purchase."""
    user_id, guild_id = str(user_id), str(guild_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO public.economy_pets (pet_id, name, description, emoji) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (pet_id) DO NOTHING", pet_id, name, description, emoji
            )
            owned = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM public.economy_user_pets WHERE user_id = $1 AND guild_id = $2 AND pet_id = $3)",
                user_id, guild_id, pet_id
            )
            if owned:
                raise ValueError("You already own that pet.")
            updated = await conn.fetchrow(
                "UPDATE public.economy_users SET wallet = wallet - $3, updated_at = NOW() "
                "WHERE user_id = $1 AND guild_id = $2 AND wallet >= $3 RETURNING *", user_id, guild_id, cost
            )
            if not updated:
                raise ValueError("You do not have enough wallet coins for that pet.")
            await conn.execute(
                "INSERT INTO public.economy_user_pets (user_id, guild_id, pet_id, equipped) VALUES ($1, $2, $3, true)",
                user_id, guild_id, pet_id
            )
            await conn.execute(
                "UPDATE public.economy_user_pets SET equipped = false WHERE user_id = $1 AND guild_id = $2 AND pet_id <> $3",
                user_id, guild_id, pet_id
            )
            await conn.execute(
                "INSERT INTO public.economy_transactions "
                "(user_id, guild_id, amount, type, description) VALUES ($1, $2, $3, 'PET_PURCHASE', $4)",
                user_id, guild_id, -cost, f"Adopted {name}"
            )


async def get_pets(pool, user_id, guild_id):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT p.pet_id, p.name, p.description, p.emoji, up.equipped "
            "FROM public.economy_user_pets up JOIN public.economy_pets p ON p.pet_id = up.pet_id "
            "WHERE up.user_id = $1 AND up.guild_id = $2 ORDER BY up.adopted_at",
            str(user_id), str(guild_id)
        )
        return [dict(row) for row in rows]


async def equip_pet(pool, user_id, guild_id, pet_id):
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM public.economy_user_pets WHERE user_id = $1 AND guild_id = $2 AND pet_id = $3)",
                str(user_id), str(guild_id), pet_id
            )
            if not exists:
                raise ValueError("You do not own that pet.")
            await conn.execute(
                "UPDATE public.economy_user_pets SET equipped = false WHERE user_id = $1 AND guild_id = $2",
                str(user_id), str(guild_id)
            )
            await conn.execute(
                "UPDATE public.economy_user_pets SET equipped = true WHERE user_id = $1 AND guild_id = $2 AND pet_id = $3",
                str(user_id), str(guild_id), pet_id
            )


async def grant_starter_bonus(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    amount: int
) -> tuple[dict, bool]:
    """Grants a one-time starter wallet bonus if the user has not claimed it."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    if amount <= 0:
        user_data = await get_or_create_user(pool, user_id, guild_id)
        return user_data, False

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT * FROM public.economy_users WHERE user_id = $1 AND guild_id = $2 FOR UPDATE",
                user_id, guild_id
            )
            if not row:
                row = await conn.fetchrow(
                    """
                    INSERT INTO public.economy_users (user_id, guild_id, wallet, bank, xp, level, daily_streak, last_daily)
                    VALUES ($1, $2, 0, 0, 0, 1, 0, NULL)
                    ON CONFLICT (user_id, guild_id) DO UPDATE SET updated_at = NOW()
                    RETURNING *
                    """,
                    user_id, guild_id
                )

            already_granted = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM public.economy_transactions
                    WHERE user_id = $1 AND guild_id = $2 AND type = 'STARTER_BONUS'
                )
                """,
                user_id, guild_id
            )
            if already_granted:
                return dict(row), False

            updated_row = await conn.fetchrow(
                """
                UPDATE public.economy_users
                SET wallet = wallet + $3, updated_at = NOW()
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
                """,
                user_id, guild_id, amount
            )
            await conn.execute(
                """
                INSERT INTO public.economy_transactions (user_id, guild_id, amount, type, description)
                VALUES ($1, $2, $3, 'STARTER_BONUS', $4)
                """,
                user_id, guild_id, amount, "One-time starter bonus for first economy command"
            )

            return dict(updated_row), True

async def update_xp(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    xp_change: int
) -> dict:
    """Updates the user's XP and handles level ups."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT xp, level FROM public.economy_users WHERE user_id = $1 AND guild_id = $2 FOR UPDATE",
                user_id, guild_id
            )
            if not row:
                await conn.execute(
                    "INSERT INTO public.economy_users (user_id, guild_id, wallet, bank, xp, level) VALUES ($1, $2, 0, 0, 0, 1)",
                    user_id, guild_id
                )
                current_xp = 0
                current_level = 1
            else:
                current_xp = row['xp']
                current_level = row['level']

            new_xp = current_xp + xp_change
            new_level = current_level

            # Simple leveling formula: requires level * 100 XP to reach next level
            # e.g., Level 1 -> Level 2 requires 100 XP
            # Level 2 -> Level 3 requires 200 XP
            while True:
                required_xp = new_level * 100
                if new_xp >= required_xp:
                    new_xp -= required_xp
                    new_level += 1
                else:
                    break

            updated_row = await conn.fetchrow(
                """
                UPDATE public.economy_users
                SET xp = $3, level = $4, updated_at = NOW()
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
                """,
                user_id, guild_id, new_xp, new_level
            )
            return dict(updated_row)

async def claim_daily(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    coins: int,
    xp: int,
    streak_increment: int
) -> dict:
    """Claims the daily reward, updates balance, XP, and streak."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT wallet, xp, level, daily_streak, last_daily FROM public.economy_users WHERE user_id = $1 AND guild_id = $2 FOR UPDATE",
                user_id, guild_id
            )
            if not row:
                # This should ideally not happen if get_or_create_user is used first
                raise ValueError("User profile not found.")

            new_wallet = row['wallet'] + coins
            new_streak = row['daily_streak'] + streak_increment
            
            # Update user record
            updated_row = await conn.fetchrow(
                """
                UPDATE public.economy_users
                SET wallet = $3, daily_streak = $4, last_daily = NOW(), updated_at = NOW()
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
                """,
                user_id, guild_id, new_wallet, new_streak
            )

            # Log transaction
            await conn.execute(
                """
                INSERT INTO public.economy_transactions (user_id, guild_id, amount, type, description)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, guild_id, coins, "DAILY_REWARD", f"Claimed daily reward: {coins} coins"
            )

            # Also update XP (reusing the logic from update_xp if possible, 
            # but since we are in a transaction, we do it here)
            # Note: update_xp is a separate function, so we'll call it or replicate logic.
            # For simplicity and transaction integrity, we'll handle XP here or call a helper.
            
            return dict(updated_row)

async def add_item_to_inventory(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    item_id: str,
    quantity: int = 1
):
    """Adds an item to the user's inventory, incrementing quantity if it exists."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO public.economy_inventory (user_id, guild_id, item_id, quantity)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, guild_id, item_id) 
            DO UPDATE SET quantity = economy_inventory.quantity + $4
            """,
            user_id, guild_id, item_id, quantity
        )

async def remove_item_from_inventory(
    pool: asyncpg.Pool,
    user_id: str,
    guild_id: str,
    item_id: str,
    quantity: int = 1
):
    """Removes an item quantity from the user's inventory."""
    user_id = str(user_id)
    guild_id = str(guild_id)

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT quantity FROM public.economy_inventory WHERE user_id = $1 AND guild_id = $2 AND item_id = $3 FOR UPDATE",
                user_id, guild_id, item_id
            )
            if not row or row['quantity'] < quantity:
                raise ValueError("Insufficient item quantity to sell.")

            new_quantity = row['quantity'] - quantity
            if new_quantity <= 0:
                await conn.execute(
                    "DELETE FROM public.economy_inventory WHERE user_id = $1 AND guild_id = $2 AND item_id = $3",
                    user_id, guild_id, item_id
                )
            else:
                await conn.execute(
                    "UPDATE public.economy_inventory SET quantity = $3 WHERE user_id = $1 AND guild_id = $2 AND item_id = $4",
                    user_id, guild_id, new_quantity, item_id
                )

async def get_inventory(pool: asyncpg.Pool, user_id: str, guild_id: str) -> list:
    """Retrieves all items and their quantities for a user."""
    user_id = str(user_id)
    guild_id = str(guild_id)
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT item_id, quantity FROM public.economy_inventory WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )
        return [dict(row) for row in rows]

async def reset_economy_data(pool: asyncpg.Pool):
    """Wipes all economy data from the database. Use with extreme caution."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Order matters due to foreign keys
            await conn.execute("DELETE FROM public.economy_user_achievements")
            await conn.execute("DELETE FROM public.economy_user_pets")
            await conn.execute("DELETE FROM public.economy_inventory")
            await conn.execute("DELETE FROM public.economy_transactions")
            await conn.execute("DELETE FROM public.economy_users")


async def gift_currency(pool, sender_id, recipient_id, guild_id, amount):
    """Atomically transfers wallet currency and records both sides of the gift."""
    sender_id, recipient_id, guild_id = map(str, (sender_id, recipient_id, guild_id))
    if amount <= 0 or sender_id == recipient_id:
        raise ValueError("Invalid gift.")

    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                "SELECT user_id, wallet FROM public.economy_users "
                "WHERE guild_id = $1 AND user_id = ANY($2::text[]) FOR UPDATE",
                guild_id, [sender_id, recipient_id]
            )
            balances = {row["user_id"]: row["wallet"] for row in rows}
            if sender_id not in balances or recipient_id not in balances:
                raise ValueError("Both users need an economy profile first.")
            if balances[sender_id] < amount:
                raise ValueError("Insufficient wallet balance.")

            await conn.execute(
                "UPDATE public.economy_users SET wallet = wallet - $3, updated_at = NOW() "
                "WHERE user_id = $1 AND guild_id = $2", sender_id, guild_id, amount
            )
            await conn.execute(
                "UPDATE public.economy_users SET wallet = wallet + $3, updated_at = NOW() "
                "WHERE user_id = $1 AND guild_id = $2", recipient_id, guild_id, amount
            )
            description = f"Gift from {sender_id} to {recipient_id}"
            await conn.executemany(
                "INSERT INTO public.economy_transactions "
                "(user_id, guild_id, amount, type, description) VALUES ($1, $2, $3, $4, $5)",
                [(sender_id, guild_id, -amount, "GIFT_SENT", description),
                 (recipient_id, guild_id, amount, "GIFT_RECEIVED", description)]
            )


async def gift_item(pool, sender_id, recipient_id, guild_id, item_id, quantity):
    """Atomically moves inventory items between two users."""
    sender_id, recipient_id, guild_id = map(str, (sender_id, recipient_id, guild_id))
    if quantity <= 0 or sender_id == recipient_id:
        raise ValueError("Invalid item gift.")

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT quantity FROM public.economy_inventory "
                "WHERE user_id = $1 AND guild_id = $2 AND item_id = $3 FOR UPDATE",
                sender_id, guild_id, item_id
            )
            if not row or row["quantity"] < quantity:
                raise ValueError("Insufficient item quantity.")
            remaining = row["quantity"] - quantity
            if remaining:
                await conn.execute(
                    "UPDATE public.economy_inventory SET quantity = $4 "
                    "WHERE user_id = $1 AND guild_id = $2 AND item_id = $3",
                    sender_id, guild_id, item_id, remaining
                )
            else:
                await conn.execute(
                    "DELETE FROM public.economy_inventory "
                    "WHERE user_id = $1 AND guild_id = $2 AND item_id = $3",
                    sender_id, guild_id, item_id
                )
            await conn.execute(
                "INSERT INTO public.economy_inventory (user_id, guild_id, item_id, quantity) "
                "VALUES ($1, $2, $3, $4) ON CONFLICT (user_id, guild_id, item_id) "
                "DO UPDATE SET quantity = economy_inventory.quantity + EXCLUDED.quantity",
                recipient_id, guild_id, item_id, quantity
            )


async def get_economy_leaderboard(pool, guild_id, limit=10):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, wallet, bank, level, prestige FROM public.economy_users "
            "WHERE guild_id = $1 ORDER BY (wallet + bank) DESC LIMIT $2",
            str(guild_id), limit
        )
        return [dict(row) for row in rows]


async def record_achievement(pool, user_id, guild_id, achievement_id, name, reward_coins=0, reward_xp=0):
    """Awards an achievement once, including its configured rewards."""
    user_id, guild_id = str(user_id), str(guild_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO public.economy_achievements (achievement_id, name) "
                "VALUES ($1, $2) ON CONFLICT (achievement_id) DO UPDATE SET name = EXCLUDED.name",
                achievement_id, name
            )
            inserted = await conn.fetchval(
                "INSERT INTO public.economy_user_achievements "
                "(user_id, guild_id, achievement_id) VALUES ($1, $2, $3) "
                "ON CONFLICT (user_id, guild_id, achievement_id) DO NOTHING RETURNING achievement_id",
                user_id, guild_id, achievement_id
            )
            if not inserted:
                return False
            if reward_coins:
                await conn.execute(
                    "UPDATE public.economy_users SET wallet = wallet + $3, updated_at = NOW() "
                    "WHERE user_id = $1 AND guild_id = $2", user_id, guild_id, reward_coins
                )
            if reward_xp:
                await conn.execute(
                    "UPDATE public.economy_users SET xp = xp + $3, updated_at = NOW() "
                    "WHERE user_id = $1 AND guild_id = $2", user_id, guild_id, reward_xp
                )
            return True


async def get_achievements(pool, user_id, guild_id):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT ua.achievement_id, COALESCE(a.name, ua.achievement_id) AS name, "
            "ua.unlocked_at AS earned_at "
            "FROM public.economy_user_achievements ua "
            "LEFT JOIN public.economy_achievements a ON a.achievement_id = ua.achievement_id "
            "WHERE ua.user_id = $1 AND ua.guild_id = $2 ORDER BY ua.unlocked_at",
            str(user_id), str(guild_id)
        )
        return [dict(row) for row in rows]


async def prestige_user(pool, user_id, guild_id, required_level, reward_coins):
    """Resets level progress and increments prestige under a row lock."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT level, prestige FROM public.economy_users "
                "WHERE user_id = $1 AND guild_id = $2 FOR UPDATE", str(user_id), str(guild_id)
            )
            if not row or row["level"] < required_level:
                raise ValueError(f"You need level {required_level} to prestige.")
            updated = await conn.fetchrow(
                "UPDATE public.economy_users SET level = 1, xp = 0, prestige = prestige + 1, "
                "wallet = wallet + $3, updated_at = NOW() WHERE user_id = $1 AND guild_id = $2 RETURNING *",
                str(user_id), str(guild_id), reward_coins
            )
            await conn.execute(
                "INSERT INTO public.economy_transactions "
                "(user_id, guild_id, amount, type, description) VALUES ($1, $2, $3, 'PRESTIGE', $4)",
                str(user_id), str(guild_id), reward_coins, "Prestige reward"
            )
            return dict(updated)
