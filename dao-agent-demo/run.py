import os
import time
import json
import random
import sys
from swarm import Swarm
from swarm.repl import run_demo_loop
from agents import dao_agent, gm_agent, player_agent, check_recent_cast_notifications
from openai import OpenAI

from prompt_helpers import (
    set_character_file, get_character_json, get_instructions, dao_simulation_setup, 
    extract_vote, check_alignment, update_narrative, roll_d20,
    get_instructions_from_file, resolve_round_with_relationships
    )
from interval_utils import get_interval, set_random_interval
import sim_phases


lower_interval = 20
upper_interval = 100

# this is the main loop that runs the agent in autonomous mode
# you can modify this to change the behavior of the agent
def run_autonomous_loop(agent):
    client = Swarm()
    messages = []

    print("Starting autonomous DAO Agent loop...")
    character_json = get_character_json()

    while True:
        # Generate a thought
        thought = random.choices(
            population=[thought['text'] for thought in character_json["autonomous_thoughts"]],
            weights=[thought['weight'] for thought in character_json["autonomous_thoughts"]],
            k=1
        )[0]
        thought = f"{character_json['pre_autonomous_thought']} {thought} {character_json['post_autonomous_thought']}"

        if check_recent_cast_notifications():
            messages.append({"role": "user", "content": thought})

            print(f"\n\033[90mAgent's Thought:\033[0m {thought}")

            print("\n\033[90mChecking for new cast notifications...\033[0m")
            # Run the agent to generate a response and take action
            response = client.run(agent=agent, messages=messages, stream=True)

            # Process and print the streaming response
            response_obj = process_and_print_streaming_response(response)

            # Update messages with the new response
            messages.extend(response_obj.messages)
        else:
            print("\n\033[90mNo new cast notifications found...\033[0m")

        # Set a random interval between 600 and 3600 seconds
        set_random_interval(lower_interval, upper_interval)

        print(f"\n\033[90mNext thought in {get_interval()} seconds...\033[0m")
        # Wait for the specified interval
        time.sleep(get_interval())


# this is the main loop that runs the agent in two-agent mode
# you can modify this to change the behavior of the agent
def run_openai_conversation_loop(agent):
    """Facilitates a conversation between an OpenAI-powered agent and the DAO Agent."""
    client = Swarm()
    openai_client = OpenAI()
    messages = []

    print("Starting OpenAI-DAO Agent conversation loop...")

    # Initial prompt to start the conversation
    openai_messages = [{
        "role":
        "system",
        "content":
        "You are a user guiding a blockchain agent through various tasks on the Base blockchain. Engage in a conversation, suggesting actions and responding to the agent's outputs. Be creative and explore different blockchain capabilities. You're not simulating a conversation, but you will be in one yourself. Make sure you follow the rules of improv and always ask for some sort of function to occur. Be unique and interesting."
    }, {
        "role":
        "user",
        "content":
        "Start a conversation with the DAO Agent and guide it through some blockchain tasks."
    }]

    while True:
        # Generate OpenAI response
        openai_response = openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=openai_messages)

        openai_message = openai_response.choices[0].message.content
        print(f"\n\033[92mOpenAI Guide:\033[0m {openai_message}")

        # Send OpenAI's message to DAO Agent
        messages.append({"role": "user", "content": openai_message})
        response = client.run(agent=agent, messages=messages, stream=True)
        response_obj = process_and_print_streaming_response(response)

        # Update messages with DAO Agent's response
        messages.extend(response_obj.messages)

        # Add DAO Agent's response to OpenAI conversation
        dao_agent_response = response_obj.messages[-1][
            "content"] if response_obj.messages else "No response from DAO Agent."
        openai_messages.append({
            "role":
            "user",
            "content":
            f"DAO Agent response: {dao_agent_response}"
        })

        # Check if user wants to continue
        user_input = input(
            "\nPress Enter to continue the conversation, or type 'exit' to end: "
        )
        if user_input.lower() == 'exit':
            break

def run_dao_simulation_loop():
    """
    Runs the DAO governance simulation loop.
    """
    # Initialize Swarm and OpenAI clients
    client = Swarm()
    
    world = choose_world()
    print(f"Selected world: {world}")

    (initial_context, players, gm) = dao_simulation_setup(world)
    game_context = initial_context["Initial"].copy()
    world_context = initial_context["World"].copy()
    simulation_steps = initial_context["Phases"]
    turn_order = game_context["turn_order"]
    current_turn = game_context["current_turn"]  # Start with the first player in the turn order

    print("Starting DAO governance simulation...")

    # Current player and GM
    player = players[turn_order[current_turn]]
    gm.set_agent(gm_agent(gm.get_instructions_string(), gm.name))

    for player in players:
        player.set_agent(player_agent(player.get_instructions_string(), player.name))

     # Initialize extra arguments
    extra_args = {}

    while True:
        

        for step in simulation_steps:
            print(f"\n\033[93mExecuting Phase: {step}\033[0m")
            
            # Dynamically load the phase function from `phases.py`
            phase_function = getattr(sim_phases, step, None)
            if callable(phase_function):
                game_context = phase_function(game_context, world_context, players, gm, client, **extra_args)

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
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            if not files:
                print("No files found in the folder.")
                return None

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
        print("3. two-agent - AI-to-agent conversation mode")
        print("4. dao-simulation - DAO simulation mode")

        choice = input(
            "\nChoose a mode (enter number or name): ").lower().strip()

        mode_map = {
            '1': 'chat',
            '2': 'auto',
            '3': 'two-agent',
            '4': 'dao-simulation',
            'chat': 'chat',
            'auto': 'auto',
            'two-agent': 'two-agent',
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


def pretty_print_messages(messages) -> None:

    for message in messages:
        if message.get("role") != "assistant":
            continue

        # print agent name in blue
        print(f"\033[94m{message['sender']}\033[0m:", end=" ")

        # print response, if any
        if message["content"]:
            print(message["content"])

        # print tool calls in purple, if any
        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")


def main(mode): 

    mode = mode or choose_mode()
    instructions = get_instructions()

    mode_functions = {
        'chat': lambda: run_demo_loop(dao_agent(instructions)),
        'auto': lambda: run_autonomous_loop(dao_agent(instructions)),
        'two-agent': lambda: run_openai_conversation_loop(dao_agent(instructions)),
        'dao-simulation': lambda: run_dao_simulation_loop()
    }

    print(f"\nStarting {mode} mode...")
    mode_functions[mode]()


if __name__ == "__main__":
    mode = ""
    if len(sys.argv) > 1:
        character_file_path = sys.argv[1].lower().strip()
        set_character_file(character_file_path)
        if len(sys.argv) > 2:
            mode = sys.argv[2].lower().strip()
    else:
        character_file_path = "default_character_data.json"
        set_character_file(character_file_path)
    print(f"Starting DAO Agent ({character_file_path})...")
    main(mode)

