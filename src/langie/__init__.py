from rich.console import Console

console = Console()

def main():
    console.rule("[bold green]Langie Agent")
    console.print("✅ Repo is live. Next step: add config + engine.", style="bold cyan")

if __name__ == "__main__":
    main()
