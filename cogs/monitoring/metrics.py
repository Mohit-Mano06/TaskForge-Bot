import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil
from prometheus_client import Counter, Gauge, Histogram


taskforge_up = Gauge("taskforge_up", "Whether the TaskForge process is alive")
taskforge_uptime_seconds = Gauge("taskforge_uptime_seconds", "TaskForge process uptime")
taskforge_discord_ready = Gauge("taskforge_discord_ready", "Whether Discord is ready")
taskforge_discord_latency_ms = Gauge("taskforge_discord_latency_ms", "Discord websocket latency in milliseconds")
taskforge_process_cpu_percent = Gauge("taskforge_process_cpu_percent", "TaskForge process CPU usage percentage")
taskforge_process_memory_bytes = Gauge("taskforge_process_memory_bytes", "TaskForge process RSS memory")
taskforge_disk_usage_percent = Gauge("taskforge_disk_usage_percent", "Disk usage percentage")
taskforge_database_up = Gauge("taskforge_database_up", "Whether PostgreSQL is responding")
taskforge_database_query_duration_seconds = Histogram(
	"taskforge_database_query_duration_seconds", "PostgreSQL health query duration"
)
taskforge_commands_total = Counter(
	"taskforge_commands_total", "Completed and failed prefix commands", ["command", "status"]
)
taskforge_command_duration_seconds = Histogram(
	"taskforge_command_duration_seconds", "Prefix command duration", ["command"]
)
taskforge_messages_seen_total = Counter("taskforge_messages_seen_total", "Non-bot guild messages seen")
taskforge_vc_active_sessions = Gauge("taskforge_vc_active_sessions", "Active voice activity sessions")
taskforge_vc_reward_coins_total = Counter("taskforge_vc_reward_coins_total", "Coins awarded for voice activity")
taskforge_economy_transactions_total = Counter(
	"taskforge_economy_transactions_total", "Successful economy transactions", ["type"]
)
taskforge_errors_total = Counter("taskforge_errors_total", "TaskForge errors", ["component"])


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
			taskforge_database_query_duration_seconds.observe(elapsed)
		except Exception:
			database_status = "Unreachable"
			taskforge_errors_total.labels(component="database").inc()

	supabase_status = "Disabled"
	try:
		import database
		if database.USE_SUPABASE:
			supabase_status = "Healthy" if await database.check_supabase_connection() else "Unreachable"
	except Exception:
		supabase_status = "Unreachable"
		taskforge_errors_total.labels(component="supabase").inc()

	snapshot = HealthSnapshot(
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
	update_health_metrics(snapshot)
	return snapshot


def update_health_metrics(snapshot: HealthSnapshot) -> None:
	taskforge_up.set(1)
	taskforge_uptime_seconds.set(snapshot.uptime_seconds)
	taskforge_discord_ready.set(int(snapshot.discord_ready))
	taskforge_discord_latency_ms.set(snapshot.discord_latency_ms)
	taskforge_process_cpu_percent.set(snapshot.cpu_percent)
	taskforge_process_memory_bytes.set(snapshot.memory_mb * 1024 ** 2)
	taskforge_disk_usage_percent.set(snapshot.disk_percent)
	taskforge_database_up.set(int(snapshot.database_status == "Connected"))
