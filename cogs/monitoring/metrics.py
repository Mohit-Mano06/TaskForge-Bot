import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil


@dataclass
class HealthSnapshot:
    discord_ready: bool
    discord_latency_ms: float
    database_status: str
    database_query_latency_ms: float | None
    supabase_status: str
    mistral_configured: bool
    cpu_percent: float
    memory_mb: float
    disk_percent: float
    uptime_seconds: int
    checked_at: datetime

    @property
    def overall_status(self) -> str:
        if not self.discord_ready or self.database_status == "Unreachable":
            return "unhealthy"
        if self.database_status != "Connected" or self.supabase_status == "Unreachable":
            return "degraded"
        if self.discord_latency_ms >= 500 or self.disk_percent >= 90:
            return "degraded"
        return "healthy"


async def collect_health_snapshot(bot) -> HealthSnapshot:
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 ** 2)
    cpu_percent = await asyncio.to_thread(process.cpu_percent, interval=0.1)
    disk_percent = psutil.disk_usage(os.getcwd()).percent

    discord_ready = bot.is_ready() and not bot.is_closed()
    discord_latency_ms = (bot.latency * 1000) if discord_ready else 0.0

    database_status = "Disabled"
    database_query_latency_ms = None
    pool = getattr(bot, "db_pool", None)
    if pool:
        started = time.perf_counter()
        try:
            await pool.fetchval("SELECT 1")
            elapsed = time.perf_counter() - started
            database_query_latency_ms = elapsed * 1000
            database_status = "Connected"
        except Exception:
            database_status = "Unreachable"

    supabase_status = "Disabled"
    try:
        import database
        if database.USE_SUPABASE:
            supabase_status = "Healthy" if await database.check_supabase_connection() else "Unreachable"
    except Exception:
        supabase_status = "Unreachable"

    return HealthSnapshot(
        discord_ready=discord_ready,
        discord_latency_ms=discord_latency_ms,
        database_status=database_status,
        database_query_latency_ms=database_query_latency_ms,
        supabase_status=supabase_status,
        mistral_configured=bool(os.getenv("MISTRAL_TOKEN")),
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        disk_percent=disk_percent,
        uptime_seconds=max(0, int(time.time() - getattr(bot, "process_start_time", time.time()))),
        checked_at=datetime.now(timezone.utc),
    )


def update_health_metrics(snapshot: HealthSnapshot) -> None:
    return None