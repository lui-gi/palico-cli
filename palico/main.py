from __future__ import annotations

import sys

import click

from palico import display, gemini


def _ensure_api_key(override: str | None = None) -> str:
    if override:
        return override
    try:
        from palico.secrets import GEMINI_API_KEY
        if GEMINI_API_KEY and GEMINI_API_KEY != "your-api-key-here":
            return GEMINI_API_KEY
    except ImportError:
        pass
    print("Error: add your Gemini API key to palico/secrets.py", file=sys.stderr)
    sys.exit(1)


@click.group()
@click.option("--api", "api_key", metavar="KEY", help="Gemini API key override")
@click.pass_context
def run(ctx: click.Context, api_key: str | None) -> None:
    """Palico — your pentesting and bug bounty companion."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key


@run.command()
@click.argument("question_text")
@click.pass_context
def question(ctx: click.Context, question_text: str) -> None:
    """Answer a security or pentesting question in 2-3 sentences."""
    gemini.init(_ensure_api_key(ctx.obj.get("api_key")))
    answer = gemini.answer_question(question_text)
    display.show_answer(question_text, answer)


@run.command()
@click.argument("engagement_name")
@click.pass_context
def start(ctx: click.Context, engagement_name: str) -> None:
    """Generate a tailored pentesting checklist for an engagement."""
    gemini.init(_ensure_api_key(ctx.obj.get("api_key")))
    try:
        target_info = display.prompt_target_info(engagement_name)
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    checklist = gemini.generate_checklist(engagement_name, target_info)
    display.show_checklist(engagement_name, checklist)


@run.command()
def owasp() -> None:
    """Display the OWASP Top 10."""
    display.show_owasp()
