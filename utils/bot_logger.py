# utils/bot_logger.py — TaskForge-Bot
# Handles terminal output routing.
# Import this in main.py with:  from utils.bot_logger import log_print, RICH_ENABLED, rich_terminal
#
# To disable rich UI: remove utils/rich_terminal.py — this file will fall back to plain print().

try:
    from . import rich_terminal
    RICH_ENABLED = True

    def log_print(msg: str, level: str = "info"):
        msg = str(msg)
        if "❌" in msg or "FATAL" in msg or "Error" in msg:
            rich_terminal.log(msg, "error")
        elif "Warning" in msg or "💡" in msg:
            rich_terminal.log(msg, "warning")
        elif "✅" in msg or "🟢" in msg:
            rich_terminal.log(msg, "success")
        else:
            rich_terminal.log(msg, level)

except ImportError:
    rich_terminal = None
    RICH_ENABLED = False

    def log_print(msg: str, level: str = "info"):
        print(msg)
