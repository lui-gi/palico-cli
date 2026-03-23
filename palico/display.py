from datetime import date, datetime
from getpass import getpass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()

_URGENT_DAYS = 3


def _parse_deadline(deadline_str: str | None) -> date | None:
    if not deadline_str:
        return None
    try:
        return date.fromisoformat(str(deadline_str))
    except ValueError:
        return None


def _format_deadline(deadline_str: str | None) -> tuple[str, bool]:
    """Returns (display_string, is_urgent)."""
    dl = _parse_deadline(deadline_str)
    if dl is None:
        return "no deadline", False
    today = date.today()
    delta = (dl - today).days
    label = dl.strftime("due %a %b %-d")
    urgent = 0 <= delta <= _URGENT_DAYS
    return label, urgent


def show_dashboard(projects: list[dict]) -> None:
    today_str = date.today().strftime("%A, %B %-d")
    console.print()
    console.print(f"  Good morning. Today is [bold]{today_str}[/bold].")
    console.print()

    if not projects:
        console.print("  [dim]No projects yet. Say 'start a new project called ...' to begin.[/dim]")
        console.print()
        return

    console.print("  Your projects:")
    for i, p in enumerate(projects, 1):
        deadline_label, urgent = _format_deadline(p.get("deadline"))
        urgency = " [bold yellow]⚠[/bold yellow]" if urgent else ""
        name = p["name"]
        console.print(f"  [bold]{i}.[/bold] {name:<22} {deadline_label}{urgency}")

    console.print()
    console.print("  Which project do you want to tackle?")
    console.print()


def show_project(project: dict, notes: list[dict], suggestions: list[str]) -> None:
    lines: list[Text] = []

    # Notes section
    lines.append(Text("Notes:", style="bold"))
    if notes:
        for n in notes:
            lines.append(Text(f"  • {n['content']}"))
    else:
        lines.append(Text("  (none yet)", style="dim"))

    lines.append(Text(""))

    # Suggestions section
    lines.append(Text("Suggestions:", style="bold"))
    if suggestions:
        for idx, s in enumerate(suggestions, 1):
            lines.append(Text(f"  {idx}. {s}"))
    else:
        lines.append(Text("  (none)", style="dim"))

    content = Text("\n").join(lines)

    deadline_str = project.get("deadline")
    dl = _parse_deadline(deadline_str)
    subtitle = dl.strftime("due %a %b %-d") if dl else "no deadline"

    panel = Panel(
        content,
        title=f"[bold]{project['name']}[/bold]",
        subtitle=f"[dim]{subtitle}[/dim]",
        border_style="blue",
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def print_reply(text: str) -> None:
    console.print(f"  [bold cyan]palico:[/bold cyan] {text}")


def prompt_api_key() -> str:
    console.print()
    console.print("  [bold]Welcome to palico![/bold]")
    console.print("  A Gemini API key is required. Get one at https://aistudio.google.com/apikey")
    console.print()
    key = Prompt.ask("  Enter your Gemini API key", password=True, console=console)
    console.print()
    return key.strip()
