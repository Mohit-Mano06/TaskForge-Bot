import asyncpg
from datetime import datetime, timezone

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
    tx_desc: str = None
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
