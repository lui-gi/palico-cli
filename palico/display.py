from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text

console = Console()

_OWASP_TOP_10 = [
    ("A01:2021", "Broken Access Control",
     "Moving up from #5; 94% of apps tested had some form of broken access control."),
    ("A02:2021", "Cryptographic Failures",
     "Formerly Sensitive Data Exposure. Failures related to cryptography leading to data leaks."),
    ("A03:2021", "Injection",
     "SQL, NoSQL, OS, LDAP injection, and XSS. Drops from #1 as controls improve."),
    ("A04:2021", "Insecure Design",
     "New category. Missing or ineffective security controls in the design phase."),
    ("A05:2021", "Security Misconfiguration",
     "Missing hardening, unnecessary features enabled, default credentials, verbose errors."),
    ("A06:2021", "Vulnerable & Outdated Components",
     "Known-vulnerable libraries, frameworks, and software components in use."),
    ("A07:2021", "Identification & Authentication Failures",
     "Formerly Broken Auth. Weak session management, credential stuffing, missing MFA."),
    ("A08:2021", "Software & Data Integrity Failures",
     "New. Insecure deserialization, untrusted plugins, compromised CI/CD pipelines."),
    ("A09:2021", "Security Logging & Monitoring Failures",
     "Insufficient logging and alerting to detect, escalate, or respond to active breaches."),
    ("A10:2021", "Server-Side Request Forgery (SSRF)",
     "New. Fetching remote resources without validating user-supplied URL allows internal access."),
]


def prompt_target_info(engagement_name: str) -> dict:
    console.print()
    console.print(f"  [bold cyan]Starting engagement:[/bold cyan] {engagement_name}")
    console.print("  [dim]Answer the questions below. Press Enter to skip any.[/dim]")
    console.print()
    return {
        "url":         Prompt.ask("  Target URL",                              default="unknown",       console=console),
        "app_type":    Prompt.ask("  App type (web app/API/mobile/network)",   default="web app",       console=console),
        "tech_stack":  Prompt.ask("  Tech stack (e.g. React + Node.js)",       default="unknown",       console=console),
        "auth_type":   Prompt.ask("  Auth type (JWT/sessions/OAuth/none)",     default="unknown",       console=console),
        "scope_notes": Prompt.ask("  Scope notes",                             default="none provided", console=console),
    }


def show_answer(question_text: str, answer: str) -> None:
    panel = Panel(
        answer,
        title=f"[bold]{question_text}[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def show_checklist(engagement_name: str, checklist: list[dict]) -> None:
    console.print()
    console.rule(f"[bold red]Checklist: {engagement_name}[/bold red]")
    console.print()
    for section in checklist:
        category = section.get("category", "Misc")
        items = section.get("items", [])
        body = Text()
        for item in items:
            body.append(f"  [ ] {item}\n")
        panel = Panel(
            body,
            title=f"[bold yellow]{category}[/bold yellow]",
            border_style="dim",
            padding=(0, 1),
        )
        console.print(panel)
    console.print()


def show_chat_header(session: str, turn_count: int) -> None:
    turns = f"{turn_count // 2} exchanges" if turn_count else "new session"
    console.print()
    console.print(
        f"  [bold cyan]palico[/bold cyan] [dim]session=[/dim][yellow]{session}[/yellow]  "
        f"[dim]{turns}[/dim]  [dim]type /help for commands[/dim]"
    )
    console.print()


def show_chat_reply(text: str) -> None:
    # Strip ===BEGIN=== / ===END=== markers from display (content extracted separately)
    display_text = text
    if "===BEGIN===" in text and "===END===" in text:
        before = text[: text.index("===BEGIN===")].strip()
        after = text[text.index("===END===") + 9 :].strip()
        display_text = "\n\n".join(filter(None, [before, after]))
    panel = Panel(
        Markdown(display_text),
        border_style="cyan",
        padding=(0, 1),
    )
    console.print(panel)


def show_tool_result(tool_name: str, outcome: str) -> None:
    console.print(f"  [dim]\\[tool][/dim] [yellow]{tool_name}[/yellow] [dim]→[/dim] {outcome}")


def show_owasp() -> None:
    table = Table(
        title="OWASP Top 10 — 2021",
        show_header=True,
        header_style="bold red",
        border_style="dim",
        show_lines=True,
    )
    table.add_column("ID", style="bold yellow", width=12)
    table.add_column("Name", style="bold", width=36)
    table.add_column("Summary", style="dim", width=54)
    for code, name, summary in _OWASP_TOP_10:
        table.add_row(code, name, summary)
    console.print()
    console.print(table)
    console.print()
