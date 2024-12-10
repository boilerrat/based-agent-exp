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
    openai_client = OpenAI()
    (initial_context, players, gm) = dao_simulation_setup()
    game_context = initial_context.copy()
    turn_order = game_context["turn_order"]
    current_turn = 0  # Start with the first player in the turn order

    print("Starting DAO governance simulation...")

    # Current player and GM
    player = players[turn_order[current_turn]]
    gma = gm_agent(get_instructions_from_file(gm), gm["Name"]) 

    player_agents = {}
    for player in players:
        player_agents[player["Key"]] = (player_agent(get_instructions_from_file(player), player["Name"]))
    
    while True:
        

        # 1. Scenario Introduction (GM Phase)
        print("\n\033[93m1. Scenario Introduction (GM Phase):\033[0m")


        gm_world_context = gm["WorldContext"]

        # Include narrative context for continuity (last 10 entries)
        recent_narratives = game_context["narrative"][-20:] if game_context["narrative"] else [{"description": "The story is just beginning."}]
        recent_narrative_descriptions = " ".join(entry["description"] for entry in recent_narratives)

        # 1a. Generate a Summary of the Narrative
        print("\n\033[93m1a. Generate a Summary (GM Phase):\033[0m")

        summary_input = {
            "role": "user",
            "content": (
                f"Game Context: {json.dumps(game_context)}.\n"
                f"Recent Narrative: {recent_narrative_descriptions}\n"
                f"Player Key/Names: {[player['Key'] for player in players]}/{[player['Name'] for player in players]}\n"
                "Summarize the key events of the narrative into a concise and engaging short story. "
                "The summary should be no more than 2-5 paragraphs, capturing the main developments and tone of the story."
            )
        }

        summary_response = client.run(agent=gma, messages=[summary_input], stream=False)


        narrative_summary = summary_response.messages
        pretty_print_messages(narrative_summary)
        # Add the summary to the narrative log as a new entry
        update_narrative(game_context, gm_situation=narrative_summary, summary_only=True)


        # 1b. Introduce a New Scenario
        print("\n\033[93m1b. Introduce a New Scenario (GM Phase):\033[0m")

        gm_input = {
            "role": "user",
            "content": (
                f"Game Context: {json.dumps(game_context)}.\n"
                f"GM World Context: {json.dumps(gm_world_context)}.\n"
                f"Recent Narrative: {narrative_summary}\n"
                "Based on this summary and the current state of the colony, introduce a new scenario or challenge. "
                "The scenario should:\n"
                "- Build on the existing narrative.\n"
                "- Add a new twist or complication for the colony.\n"
                "- Create tension or urgency for the players to address in this round.\n"
                "- Keep the new scenario concise and engaging (2-3 sentences). Avoid overly complex or abstract scenarios."

            )
        }

        # Generate GM scenario
        scenario_response = client.run(agent=gma, messages=[gm_input], stream=False)

        gm_message = scenario_response.messages
        pretty_print_messages(gm_message)

        # Add the scenario to the narrative log
        update_narrative(game_context, gm_situation=scenario_response.messages)

        # 2. Deliberation Phase
        print("\n\033[93m2. Deliberation Phase:\033[0m")

        suggestions = {}
        for voter in players:
            deliberation_input = {
                "role": "user",
                "content": f"Scenario: {gm_message}. Context: {json.dumps(game_context)}. Based on your character's beliefs and priorities, provide a succinct suggestion (1-2 sentences) for addressing the scenario."
            }
            deliberation_response = client.run(agent=player_agents[voter["Key"]], messages=[deliberation_input], stream=False)
            
            pretty_print_messages(deliberation_response.messages)

            suggestions[voter["Name"]] = deliberation_response.messages
            

        # 3. Soft Signal Phase
        print("\n\033[93m3. Soft Signal Phase:\033[0m")

        soft_signals = {}
        for voter in players:
            signal_input = {
                "role": "user",
                "content": (
                    f"Scenario: {gm_message}. Suggestions: {json.dumps(suggestions[voter['Name']])}.\n"
                    "For each suggestion, respond in the following format:\n\n"
                    "{\n"
                    '  "Suggestion 1": "For",\n'
                    '  "Suggestion 2": "Against",\n'
                    '  "Suggestion 3": "For"\n'
                    "}\n"
                    "Based on your character's beliefs and priorities, indicate whether you support or oppose each suggestion.\n"
                    "Do not include any additional text or explanations. Only provide the response in this format."
                )
            }

            signal_response = client.run(agent=player_agents[voter["Key"]], messages=[signal_input], stream=False)
            pretty_print_messages(signal_response.messages)

            try:
                signals = json.loads(signal_response.messages[-1]["content"])
                soft_signals[voter["Name"]] = signals
            except json.JSONDecodeError as e:
                print(f"\n\033[91mError decoding signals for {voter['Name']}: {e}\033[0m")
                soft_signals[voter["Name"]] = {}

        # 4. Negotiation Phase
        print("\n\033[93m4. Negotiation Phase:\033[0m")

        negotiations = {}
        for voter in players:
            negotiation_input = {
                "role": "user",
                "content": (
                    f"Scenario: {gm_message}." 
                    f"Incentive: {game_context.get('incentives', '')}. "
                    f"Suggestions: {json.dumps(suggestions[voter['Name']])}. "
                    "Provide a compromise proposal (succinct, 1-2 sentences) that aligns with your beliefs."
                )
            }

            negotiation_response = client.run(agent=player_agents[voter["Key"]], messages=[negotiation_input], stream=False)

            compromise = negotiation_response.messages
            pretty_print_messages(compromise)
            negotiations[voter["Name"]] = compromise

        # 5. Proposal Submission Phase
        print("\n\033[93m5. Proposal Submission Phase:\033[0m")
        print("\n\033[93mPlayer with Initiative:\033[0m", player["Name"])
        proposal_input = {
            "role": "user",
            "content": (
                f"Scenario: {gm_message}.\n"
                f"Negotiations: {json.dumps(negotiations)}.\n"
                "Based on the negotiations and scenario, propose a specific and actionable solution.\n"
                "Your proposal should:\n"
                "- Focus on one clear, decisive action.\n"
                "- Be aligned with your character's beliefs.\n"
                "- Add a unique and interesting twist to the overall narrative.\n"
                "- Recognize that not everyone may agree with your decision.\n"
                "- Write the proposal in 2-4 sentences, starting with the phrase 'Proposal:'."
            )
        }
        proposal_response = client.run(agent=player_agents[voter["Key"]], messages=[proposal_input], stream=False)

        proposal_message = proposal_response.messages
        pretty_print_messages(proposal_message)
        update_narrative(game_context, proposer_name=player["Name"], proposal=proposal_message)

        # Add proposal to game context
        game_context["current_proposal"] = proposal_message

        # 6. Voting Phase
        print("\n\033[93m6. Voting Phase:\033[0m")

        votes = {}
        proposer_key = players[turn_order[current_turn]]["Key"]  # Determine proposer
        for voter in players:
            relationship_key = f"{voter['Key']}-{proposer_key}"
            reverse_key = f"{proposer_key}-{voter['Name']}"
            relationship_value = (
                game_context["relationships"].get(relationship_key) or
                game_context["relationships"].get(reverse_key) or
                0
            )
            vote_input = {
                "role": "user",
                "content": (
                    f"Proposal: {game_context['current_proposal']}.\n"
                    f"Context: {json.dumps(game_context)}.\n"
                    f"The proposer of this proposal is {proposer_key}. Your current relationship with them is {relationship_value}.\n"
                    "You are voting on this proposal based on your role, personal goals, and your relationship with the proposer.\n"
                    "Consider the following:\n"
                    "- Does this proposal align with your beliefs and priorities?\n"
                    "- Will this proposal help achieve your personal objectives, or does it conflict with them?\n"
                    "- How does your relationship with the proposer affect your willingness to support their idea?\n"
                    "Be decisive in your vote (Yes, No, or Abstain), only vote Yes if you strongly support the proposal,"
                    "and explain your reasoning succinctly in a few sentences."
                )
            }

            vote_response = client.run(agent=player_agents[voter["Key"]], messages=[vote_input], stream=False)

            vote_message = vote_response.messages
            votes[voter["Key"]] = extract_vote(vote_message[-1]["content"])
            pretty_print_messages(vote_message)
            update_narrative(game_context, proposal=game_context["current_proposal"], vote_message=f"{voter['Name']}: {vote_message}", player_vote=votes[voter["Key"]])

        # 7. Round Resolution
        print("\n\033[93m7. Round Resolution Phase:\033[0m")

        game_context = resolve_round_with_relationships(game_context, votes, gm_message)
        update_narrative(game_context, proposer_name=players[turn_order[current_turn]]["Name"], outcome=game_context["last_decision"], proposal=game_context["current_proposal"])

        # 8 Proposal resolution. If the proposal passed, roll a d20 for the outcome
        print("\n\033[93m8. Proposal resolution Phase:\033[0m")
        
        if game_context["last_decision"] == "Proposal Passed":
            roll_result = roll_d20()
            
            # GM interprets the roll result
            if roll_result == 20:
                gm_message_content = (
                    f"Result: The action in the proposal is a resounding success! Not only does it solve the current challenge, "
                    f"but it also inspires unity and optimism in the community."
                )
            elif 15 <= roll_result <= 19:
                gm_message_content = (
                    f"Result: The action in the proposal succeeds with notable benefits. While some tensions remain, the colony "
                    f"sees progress in addressing the challenge."
                )
            elif 10 <= roll_result <= 14:
                gm_message_content = (
                    f"Result: The action in the proposal has limited success. It alleviates some immediate pressures, but deeper "
                    f"issues persist."
                )
            elif 2 <= roll_result <= 9:
                gm_message_content = (
                    f"Result: The action in the proposal falls short of expectations, introducing minor problems. Factional tensions grow, "
                    f"and the challenge remains unresolved."
                )
            elif roll_result == 1:
                gm_message_content = (
                    f"Result: The action in the proposal critically fails, backfiring in an unexpected way. New problems emerge, "
                    f"worsening the situation for the population."
                )
            
        # If the proposal failed, add a generic failure message to the narrative
        else:
            gm_message_content = (
                f"Result: The proposal failed to gain enough support. Factional tensions rise, leaving the challenge unresolved."
            )

        proposal_resolution = client.run(agent=gma, messages=[{"role": "user", "content": gm_message_content},], stream=False)
        proposal_resolution_messages = proposal_resolution.messages
        pretty_print_messages(proposal_resolution_messages)
        update_narrative(game_context, gm_situation=proposal_resolution_messages)

        print(f"\n\033[93mRelationship Results:\033[0m {json.dumps(game_context['relationships'], indent=2)}")
        print(f"\n\033[93mResource Results:\033[0m {json.dumps(game_context['resources'], indent=2)}")


        # Advance turn order
        current_turn = (current_turn + 1) % len(players)
        game_context["round"] += 1

        # Check if simulation should continue
        user_input = input("\nPress Enter to continue to the next round, or type 'exit' to end: ")
        if user_input.lower() == 'exit':
            break






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

