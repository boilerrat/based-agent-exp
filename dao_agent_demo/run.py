import os
import time
import json
import random
import sys
from swarm import Swarm
from swarm.repl import run_demo_loop
from openai import OpenAI

from dao_agent_demo.agents import alderman_agent, dao_agent, gm_agent, player_agent
from dao_agent_demo.tools import check_recent_unacted_cast_notifications, check_recent_unacted_proposals
from dao_agent_demo.logs import pretty_print_messages
from dao_agent_demo.prompt_helpers import (
    get_character_json, 
    get_instructions_from_json,
    dao_simulation_setup,
    )
from dao_agent_demo.interval_utils import get_interval, set_random_interval
import dao_agent_demo.sim_phases as sim_phases
from dao_agent_demo.worlds import fetch_world_files



lower_interval = 20
upper_interval = 100

# this is the main loop that runs the agent in autonomous mode
# you can modify this to change the behavior of the agent
def run_autonomous_loop():
    client = Swarm()
    messages = []

    print("Starting autonomous DAO Agent loop...")
    file_json = get_character_json("operators/alderman.json", character_type="OPERATOR")
    character_json = get_instructions_from_json(file_json)

    agent = alderman_agent()

    while True:
        # Generate a thought
        # thought = random.choices(
        #     population=[thought['text'] for thought in character_json["autonomous_thoughts"]],
        #     weights=[thought['weight'] for thought in character_json["autonomous_thoughts"]],
        #     k=1
        # )[0]
        # thought = f"{character_json['pre_autonomous_thought']} {thought} {character_json['post_autonomous_thought']}"
        
        
        new_notification = check_recent_unacted_cast_notifications()
        new_proposal = check_recent_unacted_proposals()
        debug = os.getenv("DEBUG")
        

        # if debug:
        #     thought = "Hello, can you tell me about fair launch tokens?"
        #     messages.append({"role": "user", "content": thought})

        #     print(f"\n\033[90mAgent's Thought:\033[0m {thought}")

        #     # Run the agent to generate a response and take action
        #     response = client.run(agent=agent, messages=messages, stream=True)

        #     # Process and print the streaming response
        #     response_obj = process_and_print_streaming_response(response)

        #     # Update messages with the new response
        #     messages.extend(response_obj.messages)
        
        # check for new notifications first
        if new_notification:
            print("\n\033[90mNew cast notification found...\033[0m")
            messages.append({"role": "user", "content": new_notification})
        else:
            print("\n\033[90mNo new cast notifications found...\033[0m")
            if new_proposal:
                print("\n\033[90mNew proposals found...\033[0m")
                print(new_proposal)
                # Get the first proposal from the list and parse its details
                proposal = new_proposal[0]  # Access first item in list
                details = json.loads(proposal['proposals_details'])  # Parse the JSON string
                messages.append({
                    "role": "user", 
                    "content": f"New Proposal for governor: {details['title']} -- {details['description']}"
                })
            else:
                print("\n\033[90mNo new proposals found...\033[0m")
            
        if messages:
            # Run the agent to generate a response and take action
            response = client.run(agent=agent, messages=messages, stream=True)

            # Process and print the streaming response
            response_obj = process_and_print_streaming_response(response)

            # Update messages with the new response
            messages.extend(response_obj.messages)


        # Set a random interval between 600 and 3600 seconds
        set_random_interval(lower_interval, upper_interval)

        print(f"\n\033[90mNext thought in {get_interval()} seconds...\033[0m")
        # Wait for the specified interval
        time.sleep(get_interval())


def run_dao_simulation_loop(world=None, off_chain=False):
    """
    Runs the DAO governance simulation loop.
    """
    # Initialize Swarm and OpenAI clients
    client = Swarm()
    
    if not world:
        world = choose_world()
    print(f"Selected world: {world}")
    print(f"On-chain actions: {'Active' if not off_chain else 'Inactive'}")

    (initial_context, players, gm) = dao_simulation_setup(world)
    game_context = initial_context["Initial"].copy()
    world_context = initial_context["World"].copy()
    simulation_steps = initial_context["Phases"]
    current_turn = game_context["current_turn"]  # Start with the first player in the turn order

    print("Starting DAO governance simulation...")

    # verify on_chain reqs if one doesn't exists default to off_chain. .env WEB3_PROVIDER_URI, TARGET_DAO, AGENT_ADDR
    if not off_chain:
        if not os.getenv("TARGET_DAO"):
            print("Error: On-chain mode requires the following environment variables to be set: TARGET_DAO")
            print("See README.md for more information. Defaulting to off-chain mode.")
            off_chain = True
        for player in players:
            try:
                player.set_address(os.getenv(f"{player.key}_AGENT_ADDR"))
            except:
                print(f"Error: {player.key}_AGENT_ADDR not set. Defaulting to off-chain mode.")
                off_chain = True
                break

    # Set agents for the GM and players
    gm.set_agent(gm_agent(json.dumps(gm.get_instructions_from_json()), gm.name, off_chain))
    for player in players:
        player.set_agent(player_agent(player.get_instructions_from_json(), player.name, off_chain))
        
     # Initialize extra arguments
    extra_args = {}

    while True:
        
        for step in simulation_steps:
            print(f"\n\033[93mExecuting Phase: {step}\033[0m")
            
            # Dynamically load the phase function from `phases.py`
            phase_function = getattr(sim_phases, step, None)
            if callable(phase_function):
                game_context = phase_function(game_context, world_context, players, gm, client, off_chain, **extra_args)

                # Dynamically add extra arguments
                # if step == "introduce_scenario":
                #     extra_args["incentives"] = {"bonus": 50}
            else:
                print(f"\033[91mError: Phase '{step}' is not defined.\033[0m")
                break
        
        print(f"\n\033[93mFinal Results:\033[0m {json.dumps(game_context, indent=2)}")
        print(f"\n\033[93mRelationship Results:\033[0m {json.dumps(game_context['relationships'], indent=2)}")
        print(f"\n\033[93mResource Results:\033[0m {json.dumps(game_context['resources'], indent=2)}")


        # Advance turn order
        current_turn = (current_turn + 1) % len(players)
        game_context["current_turn"] = current_turn
        game_context["round"] += 1

        # Check if simulation should continue
        user_input = input("\nPress Enter to continue to the next round, or type 'exit' to end: ")
        if user_input.lower() == 'exit':
            break


def choose_world(folder_path = "worlds"):
    """
    Lists files in a folder and allows the user to choose one.

    Args:
        folder_path (str): Path to the folder containing world files.

    Returns:
        str: The selected file name.
    """
    while True:
        try:
            # List files in the folder
            files = fetch_world_files(folder_path)

            print("\nAvailable Worlds:")
            for idx, file_name in enumerate(files, start=1):
                print(f"{idx}. {file_name}")

            # Ask the user to choose a file
            choice = input("\nChoose a world by number or name: ").strip()

            # Handle numeric input
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(files):
                    return folder_path + "/" + files[index]
                else:
                    print("Invalid number. Please try again.")
            # Handle name input
            elif choice in files:
                print(f"Selected world: {folder_path}/{choice}")
                return folder_path + "/" + choice
            else:
                print("Invalid choice. Please try again.")

        except FileNotFoundError:
            print(f"Error: The folder '{folder_path}' does not exist.")
            return None


def choose_mode():
    while True:
        print("\nAvailable modes:")
        print("1. chat    - Interactive chat mode")
        print("2. auto    - Autonomous action mode")
        print("3. dao-simulation - DAO simulation mode")

        choice = input(
            "\nChoose a mode (enter number or name): ").lower().strip()

        mode_map = {
            '1': 'chat',
            '2': 'auto',
            '3': 'dao-simulation',
            'chat': 'chat',
            'auto': 'auto',
            'dao-simulation': 'dao-simulation'
        }

        if choice in mode_map:
            return mode_map[choice]
        print("Invalid choice. Please try again.")


# Boring stuff to make the logs pretty
def process_and_print_streaming_response(response):
    content = ""
    last_sender = ""
    for chunk in response:
        if "sender" in chunk:
            last_sender = chunk["sender"]
            print('last_sender>>>>', last_sender)

        if "content" in chunk and chunk["content"] is not None:
            if not content and last_sender:
                print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
                last_sender = ""
            print(chunk["content"], end="", flush=True)
            content += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            for tool_call in chunk["tool_calls"]:
                f = tool_call["function"]
                name = f["name"]
                if not name:
                    continue
                print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")

        if "delim" in chunk and chunk["delim"] == "end" and content:
            print()  # End of response message
            content = ""

        if "response" in chunk:
            return chunk["response"]


def main(mode, character_file_path): 

    mode = mode or choose_mode()
    json = get_character_json(character_file_path, character_type="OPERATOR")
    instructions = get_instructions_from_json(json, character_type="OPERATOR")

    mode_functions = {
        'chat': lambda: run_demo_loop(dao_agent(instructions)),
        'auto': lambda: run_autonomous_loop(),
        'dao-simulation': lambda: run_dao_simulation_loop()
    }

    print(f"\nStarting {mode} mode...")
    mode_functions[mode]()


if __name__ == "__main__":
    mode = ""
    if len(sys.argv) > 1:
        character_file_path = sys.argv[1].lower().strip()
        if len(sys.argv) > 2:
            mode = sys.argv[2].lower().strip()
    else:
        character_file_path = "characters/default_character_data.json"

    print(f"Starting DAO Agent ({character_file_path}) with mode {mode}...")
    main(mode, character_file_path)

