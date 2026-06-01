"""UbU Phase 0 CLI.

Typer commands: demo, refresh.
Rich rendering: Calendar table, Affect profile, Claim Register summary, footer.
--offline flag reads the fixture; no token required.

May import: loop, schema (display types), affect (per-task margin display),
Rich, Typer, stdlib.
Forbidden: direct planning logic; direct issue-to-task mapping; schema mutation.
"""

from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ubu_phase0 import affect as _affect
from ubu_phase0.loop import LoopError, LoopResult, run
from ubu_phase0.schema import PlanningStatus, TaskSpec

app = typer.Typer(
    name="ubu-phase0",
    help="UbU Phase 0 demo prototype — ETHConf NYC.",
    add_completion=False,
    pretty_exceptions_enable=False,
)


# ---------------------------------------------------------------------------
# Affect margin visual (three-char block indicator)
# ---------------------------------------------------------------------------


def _affect_margin(task: TaskSpec, result: LoopResult) -> Text:
    """Compute per-task affect margin and return a coloured three-char Text."""
    feasibility = _affect.check_task_affect_feasibility(result.affect_profile, task)
    score = feasibility.minimum_score
    if score >= 0.7:
        return Text("▆▆▆", style="green")
    if score >= 0.4:
        return Text("▃▃▃", style="yellow")
    return Text("░░░", style="red")


# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------


def _render(result: LoopResult, console: Console) -> None:
    """Render the full demo output to console."""
    # ---- Header -----------------------------------------------------------
    console.rule("[bold]UbU Phase 0 Demo[/bold]")
    console.print(
        f"  Data source: [cyan]{result.mode}[/cyan]"
        f"     Source: [cyan]{result.source_label}[/cyan]"
    )
    console.print()

    # ---- Imported tasks ---------------------------------------------------
    tasks = result.task_graph.tasks
    console.print(f"[bold]Imported Tasks[/bold]  ({len(tasks)} tasks)")
    for task in tasks:
        console.print(
            f"  #{task.external_id}  {task.title}  "
            f"[dim]{task.source_ref}[/dim]  "
            f"[dim italic]{task.authority_source.value}[/dim italic]"
        )
    console.print()

    # ---- Affect profile ---------------------------------------------------
    labels = result.affect_profile.preset_labels
    console.print("[bold]Affect Profile[/bold]")
    console.print(
        f"  energy: [cyan]{labels.get('energy', '?')}[/cyan]"
        f"  |  stress: [cyan]{labels.get('stress', '?')}[/cyan]"
        f"  |  mood_intensity: [cyan]{labels.get('mood_intensity', '?')}[/cyan]"
    )
    if result.affect_profile.needs_review:
        console.print("  [dim](skip-calibration defaults — needs_review=True)[/dim]")
    console.print()

    # ---- Planning window --------------------------------------------------
    tw = result.planning_request.time_window
    console.print("[bold]Planning Window[/bold]")
    console.print(f"  {tw.start_time}  —  {tw.end_time}")
    console.print()

    # ---- Calendar preview -------------------------------------------------
    response = result.planning_response
    task_map = {t.id: t for t in tasks}
    console.print("[bold]Calendar Preview[/bold]")

    if response.status == PlanningStatus.rejected:
        console.print("  [red]Planning rejected[/red]")
        for failure in response.diagnostics.skeleton_failure_diagnostics:
            console.print(f"  {failure.user_facing_summary}")
    else:
        candidates = response.plan_candidates
        if not candidates or not candidates[0].schedule:
            console.print("  [yellow]No tasks scheduled in the 4-hour window.[/yellow]")
        else:
            candidate = candidates[0]
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
            table.add_column("Time", style="cyan", min_width=13)
            table.add_column("Task", min_width=36)
            table.add_column("Source", style="dim", min_width=14)
            table.add_column("Affect", min_width=5)

            for placement in candidate.schedule:
                placed = task_map.get(placement.task_id)
                if placed is None:
                    continue
                time_str = f"{placement.start_time[11:16]}–{placement.end_time[11:16]}"
                table.add_row(
                    time_str,
                    placed.title,
                    placed.authority_source.value,
                    _affect_margin(placed, result),
                )
            console.print(table)

            for fragment in candidate.explanation_fragments:
                console.print(f"  [dim]{fragment.text}[/dim]")

    # ---- Warnings ---------------------------------------------------------
    all_warnings = result.warnings + response.diagnostics.warnings
    if all_warnings:
        console.print()
        console.print("[bold yellow]Warnings[/bold yellow]")
        for w in all_warnings:
            console.print(f"  [yellow]⚠[/yellow]  {w}")

    console.print()

    # ---- Claim register summary -------------------------------------------
    console.print("[bold]Claim Register Summary[/bold]")
    claims = result.claim_register.claims
    by_status: dict[str, int] = {}
    for claim in claims:
        by_status[claim.status] = by_status.get(claim.status, 0) + 1
    for status, count in sorted(by_status.items()):
        console.print(f"  {status}: {count}")
    deferred = [c for c in claims if c.status == "deferred"]
    if deferred:
        console.print("  Notable deferrals:")
        for c in deferred:
            console.print(f"    [{c.id}] {c.claim}")
    console.print()

    # ---- Footer -----------------------------------------------------------
    diag = response.diagnostics
    cov = diag.coverage_estimate
    cov_str = "—" if cov is None else str(cov)
    console.print(
        f"  probability_quality: [dim]{diag.probability_quality.value}[/dim]"
        f"  (Phase 1 will populate)"
    )
    console.print(
        f"  coverage_estimate:   [dim]{cov_str}[/dim]"
        f"  (Phase 1 will populate)"
    )
    console.rule()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def demo(
    offline: bool = typer.Option(
        False, "--offline", is_flag=True, flag_value=True,
        help="Use fixture; no token required.",
    ),
) -> None:
    """Run the UbU Phase 0 planning demo."""
    console = Console()
    try:
        result = run(offline=offline)
    except LoopError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    _render(result, console)


@app.command()
def refresh(
    offline: bool = typer.Option(
        False, "--offline", is_flag=True, flag_value=True,
        help="Use fixture; no token required.",
    ),
) -> None:
    """Re-ingest and replan (same as re-running demo)."""
    console = Console()
    try:
        result = run(offline=offline)
    except LoopError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    console.print("[dim]↺ refreshed[/dim]")
    _render(result, console)
