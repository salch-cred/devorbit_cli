"""Rich terminal dashboard with a dependency-free fallback."""

def show_dashboard(engine):
    rows = [
        ("Provider", engine.settings.provider),
        ("Primary model", engine.model_chain[0]),
        ("Last model", str(engine.last_model_used or "—")),
        ("Workspace", engine.settings.workspace_dir),
        ("Browser", "headless" if engine._browser_headless else "visible"),
        ("Tools", str(engine.enable_tools)),
        ("Auto approve", str(engine._auto_approve_holder["value"])),
        ("Messages", str(len(engine.messages))),
        ("Models", str(len(engine.model_chain))),
        ("Max tool loops", str(engine.settings.max_tool_iterations)),
        ("Context budget", str(engine.settings.max_context_tokens)),
    ]
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        from rich import box
        console = Console()
        accent = "blue" if engine.settings.theme != "light" else "bright_blue"
        left = Table.grid(padding=(0, 1)); left.add_column(style="bold"); left.add_column()
        right = Table(box=box.SIMPLE_HEAVY, header_style="bold " + accent); right.add_column("Runtime"); right.add_column("Value")
        for key, value in rows[:7]: left.add_row(key, value)
        for key, value in rows[7:]: right.add_row(key, value)
        console.print(Panel.fit("[bold]DEVORBIT[/bold]\n[dim]Agent workspace dashboard[/dim]", border_style=accent))
        console.print(Columns([Panel(left, title="Session", border_style=accent), Panel(right, title="Engine", border_style="green")], equal=True, expand=True))
        console.print("[dim]Commands:[/dim] /settings  /team <task>  /index  /tools  /models")
    except ImportError:
        width = 72
        print("+" + "-" * (width - 2) + "+")
        print("| DEVORBIT — Agent workspace dashboard".ljust(width - 1) + "|")
        print("+" + "-" * (width - 2) + "+")
        for key, value in rows:
            line = "| " + key.ljust(20) + str(value)
            print(line[:width - 1].ljust(width - 1) + "|")
        print("+" + "-" * (width - 2) + "+")
        print("Commands: /settings  /team <task>  /index  /tools  /models")
