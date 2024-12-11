import json
from run import pretty_print_messages
from prompt_helpers import (
    set_character_file, get_character_json, get_instructions, dao_simulation_setup, 
    extract_vote, check_alignment, update_narrative, roll_d20,
    get_instructions_from_file, resolve_round_with_relationships
    )


def generate_summary(game_context, world_context, players, gm, client, **kwargs):
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
            f"Player Key/Names: {[player.key for player in players]}/{[player.name for player in players]}\n"
            "Summarize the key events of the narrative into a concise and engaging short story. "
            "The summary should be no more than 2-5 paragraphs, capturing the main developments and tone of the story."
        )
    }

    summary_response = client.run(agent=gm.agent, messages=[summary_input], stream=False)
    game_context["narrative_summary"] = summary_response.messages
    pretty_print_messages(game_context["narrative_summary"])
    update_narrative(game_context, gm_situation=game_context["narrative_summary"], summary_only=True)
    return game_context

def introduce_scenario(game_context, world_context, players, gm, client, **kwargs):
    if "narrative_summary" not in game_context:
        raise ValueError("Narrative summary is required to introduce a scenario.")
    gm_input = {
        "role": "user",
        "content": (
            f"GM World Context: {json.dumps(world_context)}.\n"
            f"Recent Narrative: {game_context['narrative_summary']}\n"
            "Based on this summary and the current state of the colony, introduce a new scenario or challenge. "
            "The scenario should:\n"
            "- Build on the existing narrative.\n"
            "- Add a new twist or complication for the colony.\n"
            "- Create tension or urgency for the players to address in this round.\n"
            "- Keep the new scenario concise and engaging (2-3 sentences). Avoid overly complex or abstract scenarios."

        )
    }

    # Generate GM scenario
    scenario_response = client.run(agent=gm.agent, messages=[gm_input], stream=False)

    messages = scenario_response.messages
    message = messages[-1]["content"]

    game_context["new_scenario"] = message
    pretty_print_messages(messages)
    # Add the scenario to the narrative log
    update_narrative(game_context, gm_situation=message)
    return game_context


def deliberation(game_context, world_context, players, gm, client, **kwargs):
    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for deliberation phase.")
    if "narrative_summary" not in game_context:
        raise ValueError("Narrative summary is required for deliberation phase.")

    for voter in players:
        deliberation_input = {
            "role": "user",
            "content": f"Scenario: {game_context['new_scenario']}.Narrative Summary: {game_context['narrative_summary']} Based on your character's beliefs and priorities, provide a succinct suggestion (1-2 sentences) for addressing the scenario."
        }
        deliberation_response = client.run(agent=voter.agent, messages=[deliberation_input], stream=False)
        
        pretty_print_messages(deliberation_response.messages)

        if "suggestions" not in game_context:
            game_context["suggestions"] = {}
        
        game_context["suggestions"][voter.name] = deliberation_response.messages[-1]["content"]
        
        update_narrative(game_context, gm_situation=deliberation_response.messages[-1]["content"])
    return game_context

def soft_signal(game_context, world_context, players, gm, client, **kwargs):
    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for soft signal phase.")
    if "suggestions" not in game_context:
        raise ValueError("Suggestions are required for soft signal phase.")
    for voter in players:
        signal_input = {
            "role": "user",
            "content": (
                f"Scenario: {game_context['new_scenario']}. Suggestions: {game_context['suggestions']}.\n"
                "For each suggestion, respond in the following format:\n\n"
                "{\n"
                '  "Suggestion 1": "For",\n'
                '  "Suggestion 2": "Against",\n'
                '  "Suggestion 3": "Abstain"\n'
                "}\n"
                "Based on your character's beliefs and priorities, indicate whether you support, oppose or abstain for each suggestion.\n"
                "Do not include any additional text or explanations. Only provide the response in this format."
            )
        }

        signal_response = client.run(agent=voter.agent, messages=[signal_input], stream=False)

        if "soft_signal" not in game_context:
            game_context["soft_signals"] = {}
        if voter.name not in game_context["soft_signals"]:
            game_context["soft_signals"][voter.name] = {}
        try:
            signals = json.loads(signal_response.messages[-1]["content"])
            game_context["soft_signals"][voter.name] = signals

        except json.JSONDecodeError as e:
            print(f"\n\033[91mError decoding signals for {voter.name}: {e}\033[0m")
            game_context["soft_signals"][voter.name] = {}
            
        pretty_print_messages(signal_response.messages)
        update_narrative(game_context, gm_situation=signal_response.messages[-1]["content"])
    return game_context


def negotiation(game_context, world_context, players, gm, client, **kwargs):
    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for negotiation phase.")
    if "suggestions" not in game_context:
        raise ValueError("Suggestions are required for negotiation phase.")
    if "soft_signals" not in game_context:
        raise ValueError("Soft signals are required for negotiation phase.")
    for voter in players:
        negotiation_input = {
            "role": "user",
            "content": (
                f"Scenario: {game_context['new_scenario']}." 
                f"Suggestions: {game_context['suggestions']}. "
                f"Soft Signals: {game_context['soft_signals']}. "
                "Provide a compromise proposal (succinct, 1-2 sentences) that aligns with your beliefs."
            )
        }

        # print("negotiation_input", negotiation_input)

        negotiation_response = client.run(agent=voter.agent, messages=[negotiation_input], stream=False)

        compromise = negotiation_response.messages[-1]["content"]
        
        pretty_print_messages(negotiation_response.messages)
        update_narrative(game_context, gm_situation=compromise)
        if "compromise" not in game_context:
            game_context["negotiations"] = {}
        game_context["negotiations"][voter.name] = compromise
    return game_context

def submit_proposal(game_context, world_context, players, gm, client, **kwargs):
    turn_order = game_context["turn_order"]
    current_turn = game_context["current_turn"]

    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for proposal submission.")
    if "negotiations" not in game_context:
        raise ValueError("Negotiations are required for proposal submission.")

    # Current player and GM
    player = players[turn_order[current_turn]]
    print("\n\033[93mPlayer with Initiative:\033[0m", player.name)
    proposal_input = {
        "role": "user",
        "content": (
            f"Scenario: {game_context['new_scenario']}.\n"
            f"Negotiations: {json.dumps(game_context['negotiations'])}.\n"
            "Based on the negotiations and scenario, submit a dao proposal onchain\n"
            "the proposal_description argument should be in markdown format, generate art and include it at the end of the markdown\n"
            "the proposal_link should be to the generated art url\n"
            "Your proposal should:\n"
            "- Focus on one clear, decisive action.\n"
            "- Be aligned with your character's beliefs.\n"
            "- Add a unique and interesting twist to the overall narrative.\n"
            "- Recognize that not everyone may agree with your decision.\n"
        )
    }
    proposal_response = client.run(agent=player.agent, messages=[proposal_input], stream=False)

    proposal_messages = proposal_response.messages
    proposal_message = proposal_messages[-1]["content"]
    pretty_print_messages(proposal_messages)
    update_narrative(game_context, proposer_name=player.name, proposal=proposal_message)

    # Add proposal to game context
    game_context["current_proposal"] = proposal_message
    return game_context


def voting(game_context, world_context, players, gm, client, **kwargs):
    if "current_proposal" not in game_context:
        raise ValueError("Current proposal is required for voting phase.")
    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for voting phase.")
    

    votes = {}
    proposer_key = players[game_context["turn_order"][game_context["current_turn"]]].key  # Determine proposer
    for voter in players:
        relationship_key = f"{voter.key}-{proposer_key}"
        reverse_key = f"{proposer_key}-{voter.key}"
        relationship_value = (
            game_context["relationships"].get(relationship_key) or
            game_context["relationships"].get(reverse_key) or
            0
        )
        vote_input = {
            "role": "user",
            "content": (
                f"Proposal: {game_context['current_proposal']}.\n"
                f"Scenario: {json.dumps(game_context['new_scenario'])}.\n"
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

        vote_response = client.run(agent=voter.agent, messages=[vote_input], stream=False)

        vote_messages = vote_response.messages
        votes[voter.key] = extract_vote(vote_messages[-1]["content"])
        if "votes" not in game_context:
            game_context["votes"] = {}
        game_context["votes"][voter.name] = votes[voter.key]
        pretty_print_messages(vote_messages)
        update_narrative(game_context, proposal=game_context["current_proposal"], vote_message=f"{voter.name}: {votes[voter.key]}", player_vote=votes[voter.key])
    return game_context

def resolve_round(game_context, world_context, players, gm, client, **kwargs):
    if "votes" not in game_context:
        raise ValueError("Votes are required for round resolution.")
    game_context = resolve_round_with_relationships(game_context, game_context["votes"], game_context["new_scenario"])
    print("\n\033[93mRound Resolution:\033[0m", game_context)
    return game_context


def round_resolution(game_context, world_context, players, gm, client, **kwargs):
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

    proposal_resolution = client.run(agent=gm.agent, messages=[{"role": "user", "content": gm_message_content},], stream=False)
    proposal_resolution_messages = proposal_resolution.messages
    pretty_print_messages(proposal_resolution_messages)
    update_narrative(game_context, gm_situation=proposal_resolution_messages[-1]["content"])
    if "proposal_resolution" not in game_context:
        game_context["proposal_resolution"] = {}
    game_context["proposal_resolution"] = proposal_resolution_messages[-1]["content"]
    return game_context


