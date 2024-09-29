import os
from rich.table import Table
from rich.console import Console

def docker_ps_pretty():
    result = os.popen("docker ps -a --format '{{.ID}}|{{.Names}}|{{.Status}}|{{.Ports}}'").read()
    rows = result.strip().split("\n")

    table = Table(title="Docker Containers", show_header=True, header_style="bold magenta", border_style="green")

    table.add_column("CONTAINER ID", justify="center")
    table.add_column("NAMES", justify="left")
    table.add_column("STATUS", justify="center")
    table.add_column("PORTS", justify="left")

    for row in rows:
        columns = row.split('|')
        table.add_row(*columns)

    console = Console()
    console.print(table)

if __name__ == "__main__":
    docker_ps_pretty()