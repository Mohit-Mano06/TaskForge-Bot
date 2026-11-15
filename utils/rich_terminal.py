# rich_terminal.py — TaskForge-Bot
# Optional rich UI layer. Delete this file to revert to plain print() output.

import sys
import io
import logging
import asyncio
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

# Initialize rich console with explicit UTF-8 encoding for Windows support
console = Console(force_terminal=True)

# ── Logging setup ──────────────────────────────────────────────────────────────

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                markup=True,
                show_path=False,
            )
        ],
    )
    return logging.getLogger("TaskForge")

logger = setup_logging()


def log(message: str, level: str = "info"):
    """Route a message to the rich logger at the given level."""
    if level == "success":
        logger.info(f"[bold green]{message}[/bold green]")
    elif level == "warning":
        logger.warning(f"[yellow]{message}[/yellow]")
    elif level == "error":
        logger.error(f"[bold red]{message}[/bold red]")
    else:
        logger.info(message)


# ── Null stream — silences any stray print() calls ────────────────────────────

class _NullStream(io.IOBase):
    """A write-only stream that discards everything."""
    def write(self, *args, **kwargs):
        return 0
    def writelines(self, *args, **kwargs):
        pass
    def flush(self):
        pass


# ── Extension loader with progress bar ────────────────────────────────────────

async def load_extensions_with_ui(bot, extensions: list):
    """Load bot extensions while showing a rich progress bar.
    All print() output is suppressed during loading so it does not
    bleed into the progress bar display.
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]TaskForge-Bot[/bold cyan]  •  Loading Modules",
            border_style="cyan",
        )
    )

    failed = []

    # Redirect stdout → /dev/null for the duration of cog loading
    _orig_stdout = sys.stdout
    sys.stdout = _NullStream()

    try:
        with Progress(
            SpinnerColumn(spinner_name="dots", style="bold blue"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("[cyan]Initialising…", total=len(extensions))

            for ext in extensions:
                short = ext.split(".")[-1]
                progress.update(task, description=f"[cyan]Loading [bold]{short}[/bold]…")
                try:
                    await bot.load_extension(ext)
                except Exception as e:
                    failed.append((ext, e))

                await asyncio.sleep(0.04)   # small delay for visual feedback
                progress.advance(task)

            progress.update(
                task,
                description="[bold green]All modules loaded![/bold green]",
            )
    finally:
        # Always restore stdout even if something raises
        sys.stdout = _orig_stdout

    console.print()

    if failed:
        for ext, err in failed:
            logger.error(f"[red]Failed to load[/red] [bold]{ext}[/bold]: {err}")
    else:
        logger.info("[bold green]Setup complete — all extensions loaded successfully.[/bold green]")
