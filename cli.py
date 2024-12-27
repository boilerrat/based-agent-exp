import click
import os

from dao_agent_demo.worlds import fetch_world_files
world_choices = fetch_world_files(os.path.join(os.path.dirname(__file__), "worlds"))
from dao_agent_demo.prompt_helpers import get_character_json, get_instructions_from_json

@click.group()
def cli():
    """
    DAO Agents Simulation CLI
    """
    pass

@cli.command()
@click.option(
    "--character-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the Character Definition JSON file",
    default="characters/default_character_data.json",
    show_default=True
)
def chat(character_file: str):
    """
    Run a chat with the DAO Agent
    """
    click.echo(click.style(f"Running agent chat Character Definition file: {click.style(character_file, fg='blue')}", fg="yellow"))
    from dao_agent_demo.agents import dao_agent
    from dao_agent_demo.run import run_demo_loop
    file_json = get_character_json(character_file, character_type="OPERATOR")
    instructions = get_instructions_from_json(file_json)
    run_demo_loop(dao_agent(instructions))

@cli.command()
@click.option(
    "--character-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the Character Definition JSON file",
    default="characters/default_character_data.json",
    show_default=True
)
def auto(character_file: str):
    """
    Run an autonomous simulation with the DAO Agent
    """
    click.echo(click.style(f"Running autonomus agent conversation Character Definition file: {click.style(character_file, fg='blue')}", fg="yellow"))
    from dao_agent_demo.run import run_autonomous_loop
    run_autonomous_loop()


@cli.command()
@click.option(
    "--character-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the Character Definition JSON file",
    default="characters/default_character_data.json",
    show_default=True
)
def two_agent(character_file: str):
    """
    Run a two-agent simulation with the DAO Agent
    """
    click.echo(click.style(f"Running two-agent simulation Character Definition file: {click.style(character_file, fg='blue')}", fg="yellow"))
    from dao_agent_demo.agents import dao_agent
    from dao_agent_demo.run import run_demo_loop
    from dao_agent_demo.prompt_helpers import get_instructions, set_character_file
    file_json = get_character_json(character_file, character_type="OPERATOR")
    instructions = get_instructions_from_json(file_json)
    from dao_agent_demo.run import run_openai_conversation_loop
    run_openai_conversation_loop(dao_agent(instructions))


@cli.command()
@click.option(
    "--world-definition",
    type=click.Choice(world_choices),
    help="World Definition to use for simulation"
)
@click.option(
    "--off-chain",
    is_flag=True,
    help="Run the simulation without interacting on-chain",
    default=False
)
def run_simulation(
    world_definition: str,
    off_chain: bool
):
    """
    Run a full multi-agent dao simulation session using a world definition
    """
    click.echo(click.style(
        (
            f"Running simulation with settings: "
            f"{click.style(f'on-chain actions: <{not off_chain}>', fg='blue')}"
        ),
        fg="yellow"
    ))
    from dao_agent_demo.run import run_dao_simulation_loop
    click.echo(world_definition)
    if world_definition:
        click.echo(click.style(f"Running simulation with World Definition file: {click.style(world_definition, fg='blue')}", fg="yellow"))
    # run_dao_simulation_loop(f"./worlds/{world_definition}")
    run_dao_simulation_loop(
        off_chain=off_chain,
        world=os.path.join(os.path.dirname(__file__), "worlds", world_definition) if world_definition else None
    )

@cli.command()
def create_wallet(num_players: int):
    """
    Create a set of wallet for the DAO Agents
    """
    from dao_agent_demo.create_wallet import main
    main(prefix="PLAYER_")

@cli.command()
@click.option(
    "--num-players",
    type=int,
    help="Number of players to create",
    default=3,
    show_default=True
)   
def create_sim(num_players: int):
    """
    Create a new world simulation
    """
    from dao_agent_demo.create_sim import main
    main(num_players=3)

def run():
    cli()


if __name__ == "__main__":
    run()
