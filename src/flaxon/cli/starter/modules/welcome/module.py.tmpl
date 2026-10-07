"""A real Python API with a module-owned Teloce component."""

from pathlib import Path
from datetime import datetime, timezone
from flaxon import __version__
from flaxon.modules import FlaxonModule

welcome = FlaxonModule("welcome", ui_dir=Path(__file__).parent / "ui")


@welcome.get("/status")
async def status():
    return {
        "message": "Your Teloce interface is talking to a Flaxon module.",
        "framework": "Flaxon",
        "version": __version__,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@welcome.cli_command("welcome", help_text="Explain your new Flaxon project")
def welcome_project(console):
    from settings import PROJECT_NAME

    console.success(f"Welcome to {PROJECT_NAME}.")
    console.info("Flaxon handles your Python routes, APIs, data, and administration.")
    console.info("Build complete server-rendered apps with Jinax, or interactive apps with Teloce.")
    console.info("Your UI is your choice. Start at https://flaxon-website.vercel.app/docs.html")
    return 0


@welcome.cli_command("welcome-status", help_text="Run the welcome module's async status helper")
async def welcome_status(console):
    result = await status()
    console.success(result["message"])
    console.info(f"Flaxon {result['version']} — {result['time']}")
    return 0
