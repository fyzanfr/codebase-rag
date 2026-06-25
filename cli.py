import os
import asyncio
import logging
import typer
from rich.console import Console
from pathlib import Path

app = typer.Typer(name="opencode", help="Codebase RAG Ingestion & Query CLI")
console = Console()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@app.command()
def index(
    repo: str = typer.Option(..., "--repo", "-r", help="Name of the repository"),
    path: str = typer.Option(..., "--path", "-p", help="Filesystem path to the local repository directory")
):
    """
    Scan a local directory, run the AST pipeline, and seed the entire codebase into Qdrant Cloud.
    """
    from ingestion.walker import async_git_and_parse_worker
    from ingestion.parser import ASTChunker
    from ingestion import queries

    local_repo_path = Path(path).resolve()

    if not os.path.exists(local_repo_path):
        console.print(f"[bold red]Error:[/bold red] The path '{local_repo_path}' does not exist.", style="red")
        raise typer.Exit(code=1)

    console.print(f"\n[bold cyan]Initializing baseline seed for repository:[/bold cyan] [green]{repo}[/green]")

    chunker = ASTChunker(
        languages=queries.LANG_CAPSULES,
        queries=queries.CHUNK_QUERIES,
        ext_map=queries.EXTENSION_MAP
    )

    all_relative_paths = []
    for root, _, files in os.walk(local_repo_path):
        for file in files:
            full_path = Path(root) / file
            rel_path = str(full_path.relative_to(local_repo_path))

            if full_path.suffix.lower() in chunker.ext_map:
                all_relative_paths.append(rel_path)

    if not all_relative_paths:
        console.print("[bold yellow]Warning:[/bold yellow] No supported source files found matching your chunker extensions.", style="yellow")
        return

    console.print(f"Found [bold yellow]{len(all_relative_paths)}[/bold yellow] valid files to process.")

    try:
        async_git_and_parse_worker(
            repo_name=repo,
            clone_url=str(local_repo_path),
            target_commit="HEAD",
            update_paths=all_relative_paths,
            delete_paths=[],
            chunker=chunker
        )
        console.print(f"\n[bold green]Success![/bold green] '{repo}' baseline successfully processed through the pipeline!\n")
    except Exception as e:
        console.print(f"\n[bold red]Ingestion Failed:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)

@app.command()
def query(
    query_text: str = typer.Argument(..., help="Natural language query about the codebase"),
    top_k: int = typer.Option(4, "--top-k", "-k", help="Number of code chunks to retrieve"),
    provider: str = typer.Option("groq", "--provider", help="LLM provider (groq, openai, gemini, anthropic)"),
    model: str = typer.Option("llama-3.3-70b-versatile", "--model", "-m", help="Model name"),
    api_key: str = typer.Option("", "--api-key", envvar=["GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"], help="API key (or set env var)")
):
    """
    Ask a natural language question about your codebase. Retrieves relevant chunks from Qdrant and answers via LLM.
    """
    async def run():
        from retrieval.search import HybridRetriever
        from generation.llm import LLMFactory

        if not api_key:
            console.print("[bold red]Error:[/bold red] No API key provided. Set the appropriate env var or pass --api-key.", style="red")
            raise typer.Exit(code=1)

        console.print(f"[bold cyan]Querying codebase:[/bold cyan] '{query_text}'")

        retriever = HybridRetriever()
        search_hits = await retriever.query(query_text, top_k=top_k)

        if not search_hits:
            console.print("[bold yellow]No relevant code chunks found.[/bold yellow]", style="yellow")
            return

        context_segments = []
        for hit in search_hits:
            segment = f"--- File: {hit['path']} ({hit['symbol']}:{hit['start_line']}-{hit['end_line']}) ---\n{hit['body']}"
            context_segments.append(segment)

        codebase_context = "\n\n".join(context_segments)

        system_prompt = f"""You are an elite AI pair-programmer. Use the following codebase context snippets to accurately resolve the user request.

Codebase Context:
    {codebase_context}"""

        console.print(f"Generating answer via [green]{provider}[/green]...")

        try:
            llm = LLMFactory.get_provider(
                provider_name=provider,
                api_key=api_key,
                model_name=model
            )
            response = llm.generate(
                system_prompt=system_prompt,
                user_prompt=query_text
            )
            console.print("\n" + "=" * 50)
            console.print(response)
            console.print("=" * 50 + "\n")
        except Exception as e:
            console.print(f"[bold red]Generation failed:[/bold red] {e}", style="red")
            raise typer.Exit(code=1)

    asyncio.run(run())

if __name__ == "__main__":
    app()
