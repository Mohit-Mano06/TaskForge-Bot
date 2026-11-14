import json
import os
import aiofiles
import asyncpg
from dotenv import load_dotenv

load_dotenv()

REMINDER_FILE = "data/reminder.json"
VERSIONS_FILE = "data/versions.json"
MAINTENANCE_FILE = "data/maintenance.json"


async def ensure_app_schema(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.bot_data (
                key text PRIMARY KEY,
                value jsonb NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS public.leaderboard (
                guild_id text NOT NULL,
                user_id text NOT NULL,
                messages_count bigint NOT NULL DEFAULT 0,
                vc_time bigint NOT NULL DEFAULT 0,
                commands_used bigint NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS public.channel_stats (
                guild_id text NOT NULL,
                channel_id text NOT NULL,
                messages_count bigint NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, channel_id)
            );
            """
        )


async def _get_bot_data(pool: asyncpg.Pool | None, key: str):
    if pool is None:
        return None
    try:
        value = await pool.fetchval("SELECT value FROM public.bot_data WHERE key = $1", key)
        return json.loads(value) if isinstance(value, str) else value
    except Exception as error:
        print(f"PostgreSQL bot_data read failed: {error}")
        return None


async def _save_bot_data(pool: asyncpg.Pool | None, key: str, value: dict):
    if pool is None:
        return
    try:
        await pool.execute(
            """
            INSERT INTO public.bot_data (key, value)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = now()
            """,
            key,
            json.dumps(value),
        )
    except Exception as error:
        print(f"PostgreSQL bot_data write failed: {error}")


# ==========================================
# REMINDERS
# ==========================================

async def load_reminders(pool: asyncpg.Pool | None) -> list:
    """Load reminders from PostgreSQL, falling back to the local JSON backup."""
    value = await _get_bot_data(pool, "reminders")
    if value is not None:
        return value.get("reminders", [])
    
    # JSON Fallback
    if not os.path.exists(REMINDER_FILE):
        return []
    
    try:
        async with aiofiles.open(REMINDER_FILE, "r") as f:
            content = await f.read()
            if not content.strip():
                return []
            return json.loads(content).get("reminders", [])
    except Exception as e:
        print(f"Error loading reminders: {e}")
        return []

async def save_reminders(pool: asyncpg.Pool | None, reminders_list: list):
    """Save reminders to PostgreSQL and refresh the local JSON backup."""
    await _save_bot_data(pool, "reminders", {"reminders": reminders_list})
    
    # Always keep JSON updated as a backup!
    os.makedirs(os.path.dirname(REMINDER_FILE), exist_ok=True)
    async with aiofiles.open(REMINDER_FILE, "w") as f:
        await f.write(json.dumps({"reminders": reminders_list}, indent=4))


# ==========================================
# VERSIONS / RELEASES
# ==========================================

async def get_latest_release(pool: asyncpg.Pool | None):
    """Fetch the latest release from PostgreSQL or the local JSON backup."""
    data = await _get_bot_data(pool, "versions")
    if data is not None:
        releases = data.get("releases", [])
        return releases[-1] if releases else None

    if not os.path.exists(VERSIONS_FILE):
        return None
        
    try:
        async with aiofiles.open(VERSIONS_FILE, "r") as f:
            content = await f.read()
            data = json.loads(content)
            releases = data.get("releases", [])
            return releases[-1] if releases else None
    except Exception as e:
        print(f"Error loading latest release: {e}")
        return None

async def save_release(pool: asyncpg.Pool | None, release_data: dict):
    """Save a release to PostgreSQL and the local JSON backup, removing duplicates."""
    file_data = await _get_bot_data(pool, "versions")
    if file_data is None and os.path.exists(VERSIONS_FILE):
        try:
            async with aiofiles.open(VERSIONS_FILE, "r") as f:
                content = await f.read()
                file_data = json.loads(content)
        except Exception:
            pass
    if file_data is None:
        file_data = {"releases": []}
            
    if "releases" not in file_data:
        file_data["releases"] = []
    
    # Remove any existing entries with the same version (keep latest only)
    new_version = release_data.get("version")
    if new_version:
        file_data["releases"] = [r for r in file_data["releases"] if r.get("version") != new_version]
    
    file_data["releases"].append(release_data)

    await _save_bot_data(pool, "versions", file_data)
    
    # Always update local JSON as backup
    os.makedirs(os.path.dirname(VERSIONS_FILE), exist_ok=True)
    async with aiofiles.open(VERSIONS_FILE, "w") as f:
        await f.write(json.dumps(file_data, indent=4))

async def update_leaderboard_stat(pool: asyncpg.Pool | None, guild_id: str, user_id: str, stat_type: str, amount: int):
    if pool is None:
        return False
    if stat_type not in {"messages_count", "vc_time", "commands_used"}:
        raise ValueError(f"Unsupported leaderboard stat: {stat_type}")
    await pool.execute(
        f"""
        INSERT INTO public.leaderboard (guild_id, user_id, {stat_type})
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id, user_id) DO UPDATE
        SET {stat_type} = leaderboard.{stat_type} + EXCLUDED.{stat_type}
        """,
        str(guild_id),
        str(user_id),
        amount,
    )
    return True


async def update_channel_stat(pool: asyncpg.Pool | None, guild_id: str, channel_id: str, amount: int):
    if pool is None:
        return False
    await pool.execute(
        """
        INSERT INTO public.channel_stats (guild_id, channel_id, messages_count)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id, channel_id) DO UPDATE
        SET messages_count = channel_stats.messages_count + EXCLUDED.messages_count
        """,
        str(guild_id),
        str(channel_id),
        amount,
    )
    return True


async def get_top_channels(pool: asyncpg.Pool | None, guild_id: str, limit: int = 10) -> list:
    if pool is None:
        return []
    rows = await pool.fetch(
        """
        SELECT channel_id, messages_count FROM public.channel_stats
        WHERE guild_id = $1 ORDER BY messages_count DESC LIMIT $2
        """,
        str(guild_id),
        limit,
    )
    return [dict(row) for row in rows]


async def get_top_leaderboard(pool: asyncpg.Pool | None, guild_id: str, stat_type: str, limit: int = 10) -> list:
    if pool is None:
        return []
    if stat_type not in {"messages_count", "vc_time", "commands_used"}:
        raise ValueError(f"Unsupported leaderboard stat: {stat_type}")
    rows = await pool.fetch(
        f"""
        SELECT user_id, {stat_type} FROM public.leaderboard
        WHERE guild_id = $1 ORDER BY {stat_type} DESC LIMIT $2
        """,
        str(guild_id),
        limit,
    )
    return [dict(row) for row in rows]


async def bulk_update_leaderboard_stats(pool: asyncpg.Pool | None, guild_id: str, user_stats: dict, channel_stats: dict | None = None):
    if pool is None:
        return False
    for user_id, stats in user_stats.items():
        count = stats.get("messages_count")
        if count:
            await update_leaderboard_stat(pool, guild_id, user_id, "messages_count", count)
    if channel_stats:
        for channel_id, count in channel_stats.items():
            if count:
                await update_channel_stat(pool, guild_id, channel_id, count)
    return True


# ==========================================
# MAINTENANCE STATE
# ==========================================

async def load_maintenance(pool: asyncpg.Pool | None) -> dict:
    """Load maintenance state from PostgreSQL or the local JSON backup."""
    default_state = {"enabled": False, "message": "TaskForge is currently undergoing testing/maintenance."}
    value = await _get_bot_data(pool, "maintenance")
    if value is not None:
        return value
    
    # JSON Fallback
    if not os.path.exists(MAINTENANCE_FILE):
        return default_state
    
    try:
        async with aiofiles.open(MAINTENANCE_FILE, "r") as f:
            content = await f.read()
            if not content.strip():
                return default_state
            return json.loads(content)
    except Exception as e:
        print(f"Error loading maintenance state: {e}")
        return default_state

async def save_maintenance(pool: asyncpg.Pool | None, state: dict):
    """Save maintenance state to PostgreSQL and the local JSON backup."""
    await _save_bot_data(pool, "maintenance", state)
    
    # Always keep JSON updated as a backup!
    os.makedirs(os.path.dirname(MAINTENANCE_FILE), exist_ok=True)
    async with aiofiles.open(MAINTENANCE_FILE, "w") as f:
        await f.write(json.dumps(state, indent=4))
