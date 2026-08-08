import json
import os
import aiofiles
import aiohttp
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Toggle this to True when you have added your Supabase credentials to .env
USE_SUPABASE = os.getenv("USE_SUPABASE", "False") == "True"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

REMINDER_FILE = "data/reminder.json"
VERSIONS_FILE = "data/versions.json"
MAINTENANCE_FILE = "data/maintenance.json"


async def supabase_request(method, endpoint, data=None, extra_headers=None):
    if not USE_SUPABASE:
        return None
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if extra_headers:
        headers.update(extra_headers)
        
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, headers=headers, json=data) as resp:
                if resp.status >= 300:
                    print(f"Supabase error ({resp.status}): {await resp.text()}")
                    return None
                
                # Some requests (like empty POSTs) might not return JSON
                text = await resp.text()
                if not text:
                    return []
                return json.loads(text)
        except Exception as e:
            print(f"Supabase connection error: {e}")
            return None


async def check_supabase_connection():
    """Checks if we can hit the REST API and the bot_data table exists."""
    if not USE_SUPABASE:
        return False
    # Just try to fetch 1 row from bot_data
    res = await supabase_request("GET", "bot_data?select=key&limit=1")
    return res is not None


# ==========================================
# REMINDERS
# ==========================================

async def load_reminders() -> list:
    """Async loads reminders from Supabase or JSON"""
    if USE_SUPABASE:
        res = await supabase_request("GET", "bot_data?key=eq.reminders&select=value")
        if res and len(res) > 0:
            return res[0].get("value", {}).get("reminders", [])
        return []
    
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

async def save_reminders(reminders_list: list):
    """Async saves reminders to Supabase or JSON"""
    if USE_SUPABASE:
        payload = {"key": "reminders", "value": {"reminders": reminders_list}}
        # Upsert config: Merge duplicates means it will update existing row if key exists
        await supabase_request("POST", "bot_data", data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    
    # Always keep JSON updated as a backup!
    os.makedirs(os.path.dirname(REMINDER_FILE), exist_ok=True)
    async with aiofiles.open(REMINDER_FILE, "w") as f:
        await f.write(json.dumps({"reminders": reminders_list}, indent=4))


# ==========================================
# VERSIONS / RELEASES
# ==========================================

async def get_latest_release():
    """Async fetches the latest release from Supabase or JSON"""
    if USE_SUPABASE:
        res = await supabase_request("GET", "bot_data?key=eq.versions&select=value")
        if res and len(res) > 0:
            releases = res[0].get("value", {}).get("releases", [])
            return releases[-1] if releases else None
        return None

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

async def save_release(release_data: dict):
    """Async saves a new release to Supabase or JSON, removing duplicates"""
    # Fetch existing from wherever we are loading it
    file_data = {"releases": []}
    
    if USE_SUPABASE:
        res = await supabase_request("GET", "bot_data?key=eq.versions&select=value")
        if res and len(res) > 0:
             file_data = res[0].get("value", {"releases": []})
    elif os.path.exists(VERSIONS_FILE):
        try:
            async with aiofiles.open(VERSIONS_FILE, "r") as f:
                content = await f.read()
                file_data = json.loads(content)
        except Exception:
            pass
            
    if "releases" not in file_data:
        file_data["releases"] = []
    
    # Remove any existing entries with the same version (keep latest only)
    new_version = release_data.get("version")
    if new_version:
        file_data["releases"] = [r for r in file_data["releases"] if r.get("version") != new_version]
    
    file_data["releases"].append(release_data)

    if USE_SUPABASE:
        payload = {"key": "versions", "value": file_data}
        await supabase_request("POST", "bot_data", data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    
    # Always update local JSON as backup
    os.makedirs(os.path.dirname(VERSIONS_FILE), exist_ok=True)
    async with aiofiles.open(VERSIONS_FILE, "w") as f:
        await f.write(json.dumps(file_data, indent=4))

# ==========================================
# ECONOMY & SHOP (SUPABASE ONLY)
# ==========================================

async def get_balance(user_id: str) -> dict:
    """Returns {"balance": int, "last_daily": str} for a user."""
    if not USE_SUPABASE:
        return {"balance": 0, "last_daily": None}
    
    res = await supabase_request("GET", f"user_economy?user_id=eq.{user_id}&select=balance,last_daily")
    if res and len(res) > 0:
        return res[0]
    return {"balance": 0, "last_daily": None}

async def update_balance(user_id: str, amount: int, transaction_type: str, description: str = ""):
    """Changes user balance by `amount` (can be negative) and logs transaction."""
    if not USE_SUPABASE:
        return False
        
    current = await get_balance(user_id)
    new_balance = current["balance"] + amount

    # Upsert new balance
    payload = {
        "user_id": user_id,
        "balance": new_balance
    }
    if current["last_daily"]:
        payload["last_daily"] = current["last_daily"]

    await supabase_request("POST", "user_economy", data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    
    # Log transaction
    log_payload = {
        "user_id": user_id,
        "amount": amount,
        "type": transaction_type,
        "description": description
    }
    await supabase_request("POST", "transactions", data=log_payload)
    return True

async def update_last_daily(user_id: str):
    """Sets last_daily to current time."""
    if not USE_SUPABASE:
        return False
    current = await get_balance(user_id)
    payload = {
        "user_id": user_id,
        "balance": current["balance"],
        "last_daily": datetime.now(timezone.utc).isoformat()
    }
    await supabase_request("POST", "user_economy", data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    return True

async def get_shop_items() -> list:
    if not USE_SUPABASE:
        return []
    res = await supabase_request("GET", "shop_items?select=*")
    return res if res else []

async def get_inventory(user_id: str) -> list:
    """Gets inventory joined with shop_items."""
    if not USE_SUPABASE:
        return []
    res = await supabase_request("GET", f"user_inventory?user_id=eq.{user_id}&select=id,quantity,item_id,shop_items(*)")
    return res if res else []

async def add_item_to_inventory(user_id: str, item_id: int, quantity: int = 1):
    if not USE_SUPABASE:
        return False
        
    res = await supabase_request("GET", f"user_inventory?user_id=eq.{user_id}&item_id=eq.{item_id}&select=id,quantity")
    if res and len(res) > 0:
        new_quantity = res[0]["quantity"] + quantity
        inv_id = res[0]["id"]
        # Update existing
        await supabase_request("PATCH", f"user_inventory?id=eq.{inv_id}", data={"quantity": new_quantity})
    else:
        # Insert new
        payload = {
            "user_id": user_id,
            "item_id": item_id,
            "quantity": quantity
        }
        await supabase_request("POST", "user_inventory", data=payload)
    return True

# ==========================================
# LEADERBOARD (SUPABASE ONLY)
# ==========================================

async def update_leaderboard_stat(guild_id: str, user_id: str, stat_type: str, amount: int):
    """Updates a user's leaderboard stat (messages_count, vc_time, commands_used)."""
    if not USE_SUPABASE:
        return False
        
    # First, fetch existing stats
    res = await supabase_request("GET", f"leaderboard?guild_id=eq.{guild_id}&user_id=eq.{user_id}&select=messages_count,vc_time,commands_used")
    
    current_stats = {
        "messages_count": 0,
        "vc_time": 0,
        "commands_used": 0
    }
    
    exists = False
    if res and len(res) > 0:
        current_stats.update(res[0])
        exists = True
        
    current_stats[stat_type] += amount
    
    # Payload
    payload = {
        "guild_id": str(guild_id),
        "user_id": str(user_id),
        "messages_count": current_stats["messages_count"],
        "vc_time": current_stats["vc_time"],
        "commands_used": current_stats["commands_used"]
    }
    
    if exists:
        # Explicit PATCH update using the composite key
        await supabase_request("PATCH", f"leaderboard?guild_id=eq.{guild_id}&user_id=eq.{user_id}", data=payload)
    else:
        # Explicit POST insert
        await supabase_request("POST", "leaderboard", data=payload)
        
    return True

async def update_channel_stat(guild_id: str, channel_id: str, amount: int):
    """Increments the message count for a specific channel."""
    if not USE_SUPABASE:
        return False
        
    res = await supabase_request("GET", f"channel_stats?guild_id=eq.{guild_id}&channel_id=eq.{channel_id}&select=messages_count")
    
    current_count = 0
    exists = False
    if res and len(res) > 0:
        current_count = res[0].get("messages_count", 0)
        exists = True
        
    payload = {
        "guild_id": str(guild_id),
        "channel_id": str(channel_id),
        "messages_count": current_count + amount
    }
    
    if exists:
        await supabase_request("PATCH", f"channel_stats?guild_id=eq.{guild_id}&channel_id=eq.{channel_id}", data=payload)
    else:
        await supabase_request("POST", "channel_stats", data=payload)
    return True

async def get_top_channels(guild_id: str, limit: int = 10) -> list:
    """Gets the most active channels in a guild."""
    if not USE_SUPABASE:
        return []
    res = await supabase_request("GET", f"channel_stats?guild_id=eq.{guild_id}&select=channel_id,messages_count&order=messages_count.desc&limit={limit}")
    return res if res else []

async def get_top_leaderboard(guild_id: str, stat_type: str, limit: int = 10) -> list:
    """Gets top users for a specific stat in a guild."""
    if not USE_SUPABASE:
        return []
    
    res = await supabase_request("GET", f"leaderboard?guild_id=eq.{guild_id}&select=user_id,{stat_type}&order={stat_type}.desc&limit={limit}")
    return res if res else []

async def bulk_update_leaderboard_stats(guild_id: str, user_stats: dict, channel_stats: dict = None):
    """
    Upserts multiple users' and channels' message stats at once.
    """
    if not USE_SUPABASE:
        return False
        
    # Update Users
    for user_id, stats in user_stats.items():
        if "messages_count" in stats:
            await update_leaderboard_stat(guild_id, user_id, "messages_count", stats["messages_count"])
            
    # Update Channels
    if channel_stats:
        for channel_id, count in channel_stats.items():
            await update_channel_stat(guild_id, channel_id, count)
            
    return True


# ==========================================
# MAINTENANCE STATE
# ==========================================

async def load_maintenance() -> dict:
    """Async loads maintenance state from Supabase or JSON"""
    default_state = {"enabled": False, "message": "TaskForge is currently undergoing testing/maintenance."}
    if USE_SUPABASE:
        res = await supabase_request("GET", "bot_data?key=eq.maintenance&select=value")
        if res and len(res) > 0:
            return res[0].get("value", default_state)
        return default_state
    
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

async def save_maintenance(state: dict):
    """Async saves maintenance state to Supabase or JSON"""
    if USE_SUPABASE:
        payload = {"key": "maintenance", "value": state}
        await supabase_request("POST", "bot_data", data=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
    
    # Always keep JSON updated as a backup!
    os.makedirs(os.path.dirname(MAINTENANCE_FILE), exist_ok=True)
    async with aiofiles.open(MAINTENANCE_FILE, "w") as f:
        await f.write(json.dumps(state, indent=4))
