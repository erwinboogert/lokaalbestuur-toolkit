"""CLI entry point voor WikiBrain."""

import click
from pathlib import Path
import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@click.group()
@click.option("--config", default="config.yaml", help="Pad naar config.yaml")
@click.pass_context
def cli(ctx, config):
    """WikiBrain — kennisbank voor journalistiek bronmateriaal."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.option("--force", is_flag=True, help="Verwerk alle bestanden opnieuw")
@click.option("--dry-run", is_flag=True, help="Toon wat verwerkt zou worden")
@click.option("--batch-size", type=int, default=None, help="Overschrijf batch_size uit config")
@click.pass_context
def ingest(ctx, force, dry_run, batch_size):
    """Verwerk nieuwe en gewijzigde bronbestanden."""
    from wikibrain.ingest import run_ingest
    cfg = ctx.obj["config"]
    if batch_size:
        cfg["ingest"]["batch_size"] = batch_size
    run_ingest(cfg, force=force, dry_run=dry_run)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Toon wat er zou veranderen")
@click.option("--force-concept", default=None, help="Hercompileer één specifiek concept")
@click.option("--all", "compile_all", is_flag=True, help="Hercompileer volledige wiki")
@click.option("--limit", type=int, default=None, help="Verwerk maximaal N bronnen")
@click.pass_context
def compile(ctx, dry_run, force_concept, compile_all, limit):
    """Bouw en onderhoud de wiki op basis van de wachtrij."""
    import json
    from wikibrain.compile import run_compile
    cfg = ctx.obj["config"]

    if not dry_run and not force_concept:
        raw_dir = Path(cfg["paths"]["raw"])
        queue_path = raw_dir / "queue.json"
        if queue_path.exists():
            queue = json.loads(queue_path.read_text())
            pending_count = len([i for i in queue if i["status"] == "pending"])
            effective = limit if limit else pending_count
            if effective >= 25:
                click.echo(f"\n⚠️  Let op: {effective} bronnen in de wachtrij.")
                click.echo("   Elke bron kost meerdere Claude-calls (discovery + bronpagina + artikelen).")
                click.echo("   Bij grote aantallen kan dit een flink deel van je Claude-bundel verbruiken.")
                click.echo("   Overweeg om in batches te werken, bijvoorbeeld:")
                click.echo(f"   wikibrain compile --limit 50\n")
                if not click.confirm("   Toch doorgaan met alle bronnen?", default=False):
                    click.echo("Geannuleerd. Gebruik --limit N om in batches te werken.")
                    return

    run_compile(cfg, dry_run=dry_run, force_concept=force_concept, compile_all=compile_all, limit=limit)


@cli.command()
@click.argument("question")
@click.option("--output", default="markdown", type=click.Choice(["markdown", "slides", "table", "mermaid", "image"]))
@click.pass_context
def query(ctx, question, output):
    """Stel een vraag aan de wiki."""
    from wikibrain.query import run_query
    cfg = ctx.obj["config"]
    run_query(cfg, question=question, output_format=output)


@cli.command()
@click.argument("term")
@click.option("--top", default=10, help="Aantal resultaten")
@click.option("--in", "search_in", default=None, type=click.Choice(["concepts", "sources"]))
@click.option("--type", "result_type", default=None, type=click.Choice(["concept", "source"]))
@click.pass_context
def search(ctx, term, top, search_in, result_type):
    """Zoek in de wiki-index."""
    from wikibrain.search import run_search
    cfg = ctx.obj["config"]
    run_search(cfg, term=term, top_k=top, search_in=search_in, result_type=result_type)


@cli.command()
@click.option("--fix", is_flag=True, help="Claude stelt fixes voor")
@click.option("--report", is_flag=True, help="Schrijf rapport naar wiki/_meta/health_report.md")
@click.option("--check", default=None, help="Voer alleen één specifieke check uit")
@click.pass_context
def lint(ctx, fix, report, check):
    """Kwaliteitscontrole van de wiki."""
    from wikibrain.lint import run_lint
    cfg = ctx.obj["config"]
    run_lint(cfg, fix=fix, report=report, check=check)


def main():
    cli()


if __name__ == "__main__":
    main()
