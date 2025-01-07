import json
import os
from dao_agent_demo.logs import pretty_print_messages
from dao_agent_demo.prompt_helpers import (
    extract_vote, update_narrative, roll_d20, resolve_round_with_relationships
    )

from dotenv import dotenv_values

config = dotenv_values("../.env")

DAO_ADDRESS = os.getenv("TARGET_DAO", "")

def generate_summary(game_context, world_context, players, gm, client, off_chain, **kwargs):
    # Include narrative context for continuity (last 10 entries)
    recent_narratives = game_context["narrative"][-20:] if game_context["narrative"] else [{"description": "The story is just beginning."}]
    recent_narrative_descriptions = " ".join(entry["description"] for entry in recent_narratives)

    # 1a. Generate a Summary of the Narrative
    print("\n\033[93m1a. Generate a Summary (GM Phase):\033[0m")

    summary_length = max(5, min(20, game_context["round"]))

    summary_input = {
        "role": "user",
        "content": (
            f"GM World Context: {json.dumps(world_context)}.\n"
            f"Recent Narrative: {recent_narrative_descriptions}\n"
            f"Player Key/Names: {[player.key for player in players]}/{[player.name for player in players]}\n"
            "Summarize the key events of the narrative into a concise and engaging short story. "
            f"The summary should be no more than {summary_length} paragraphs, capturing the main developments and tone of the story."
        )
    }

    summary_response = client.run(agent=gm.agent, messages=[summary_input], stream=False)
    game_context["narrative_summary"] = summary_response.messages[-1]["content"]
    pretty_print_messages(summary_response.messages)
    update_narrative(game_context, gm_situation=game_context["narrative_summary"], summary_only=True)
    return game_context

def introduce_scenario(game_context, world_context, players, gm, client, off_chain, **kwargs):

    # TODO check for current proposals that have not been voted on
    # save current proposal id in game context
    # also set current proposal here
    if "narrative_summary" not in game_context:
        raise ValueError("Narrative summary is required to introduce a scenario.")
    gm_input = {
        "role": "user",
        "content": (
            f"GM World Context: {json.dumps(world_context)}.\n"
            f"Recent Narrative: {game_context['narrative_summary']}\n"
            # add recent proposal 
            "Based on this recent summary and the world context introduce a new scenario or challenge. "
            "The scenario should:\n"
            "- Build on the existing narrative.\n"
            "- Add a new twist or complication for the world.\n"
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


def deliberation(game_context, world_context, players, gm, client, off_chain, **kwargs):
    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for deliberation phase.")
    if "narrative_summary" not in game_context:
        raise ValueError("Narrative summary is required for deliberation phase.")

    for voter in players:
        deliberation_input = {
            "role": "user",
            "content": (
                f"Scenario: {game_context['new_scenario']}\n"
                f"Narrative Summary: {game_context['narrative_summary']}\n" 
                "Based on your character's beliefs and priorities, provide a succinct suggestion (1-2 sentences) for addressing the scenario.\n" 
                "Do not submit a proposal or call any function this is just for deliberation and negotiation."
            )
        }
        deliberation_response = client.run(agent=voter.agent, messages=[deliberation_input], stream=False)
        
        pretty_print_messages(deliberation_response.messages)

        if "suggestions" not in game_context:
            game_context["suggestions"] = {}
        
        game_context["suggestions"][voter.name] = deliberation_response.messages[-1]["content"]
        
        update_narrative(game_context, gm_situation=deliberation_response.messages[-1]["content"])
    return game_context

def soft_signal(game_context, world_context, players, gm, client, off_chain, **kwargs):
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
                "Do not include any additional text or explanations and do not execute any functions. Only provide the response in this format."
            )
        }

        signal_response = client.run(agent=voter.agent, messages=[signal_input], stream=False)

        if "soft_signals" not in game_context:
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


def negotiation(game_context, world_context, players, gm, client, off_chain, **kwargs):
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
                "Provide a compromise suggestion (succinct, 1-2 sentences) that aligns with your beliefs."
                "Do not submit a proposal or call any function this is just for deliberation and negotiation."
            )
        }

        # print("negotiation_input", negotiation_input)

        negotiation_response = client.run(agent=voter.agent, messages=[negotiation_input], stream=False)

        compromise = negotiation_response.messages[-1]["content"]
        
        pretty_print_messages(negotiation_response.messages)
        update_narrative(game_context, gm_situation=compromise)
        if "negotiations" not in game_context:
            game_context["negotiations"] = {}
        game_context["negotiations"][voter.name] = compromise
    return game_context

def submit_proposal(game_context, world_context, players, gm, client, off_chain, **kwargs):

    turn_order = game_context["turn_order"]
    current_turn = game_context["current_turn"]

    if "new_scenario" not in game_context:
        raise ValueError("New scenario is required for proposal submission.")
    if "negotiations" not in game_context:
        raise ValueError("Negotiations are required for proposal submission.")

    player = players[turn_order[current_turn]]
    print("\n\033[93mPlayer with Initiative:\033[0m", player.name)
    proposal_input = {
        "role": "user",
        "content": (
            f"World Context: {json.dumps(world_context)}.\n"
            f"Scenario: {game_context['new_scenario']}.\n"
            f"Negotiations: {json.dumps(game_context['negotiations'])}.\n"
            "Focus on one clear, decisive action and be aligned with your character's beliefs.\n"
            "Your response should be in the following json format:\n"
            "{\n"
               '"proposal_title": "The proposal title.",\n'
               '"proposal_description": "The proposal description in markdown format.",\n'
               '"proposal_id": "proposal id.",\n'
               '"proposal_link": "generate art for link",\n'
            "}\n"
            "Do not include any additional text or explanations. Only provide the response in this format.\n"
            )
    }
    if not off_chain:
        proposal_input["content"] += (
            "The only function to call is submit_dao_proposal_onchain."
            "Based on the negotiations and scenario submit a new proposal onchain only once (submit_dao_proposal_onchain(proposal_title: str, proposal_description: str, proposal_link: str)).\n"
        )
    else:
        proposal_input["content"] += (
            "Submit a new proposal with id 0"
            )
    proposal_response = client.run(agent=player.agent, messages=[proposal_input], stream=False, context_variables={"agent_key":player.key})

    proposal_messages = proposal_response.messages

    proposal_message = proposal_messages[0]["content"]
    pretty_print_messages(proposal_messages)
    update_narrative(game_context, proposer_name=player.name, proposal=proposal_message)

    # Add proposal to game context (try to find the json in the messages)
    for message in proposal_messages:
        try:
            proposal = json.loads(message["content"])
            game_context["current_proposal"] = proposal["proposal_description"]
            game_context["current_proposal_id"] = proposal["proposal_id"]
        except json.JSONDecodeError as e:
            pass
        except TypeError as e:
            pass
    
    if not off_chain:
        print(f"\n\033[93mProposal URL:\033[0m https://admin.daohaus.fun/#/molochv3/0x2105/{DAO_ADDRESS}/proposal/{game_context['current_proposal_id']}" )
    # add proposal id
    return game_context


def voting(game_context, world_context, players, gm, client, off_chain, **kwargs):
    # get proposal id and current proposal off game context
    if "current_proposal" not in game_context:
        ("Current proposal is required for voting phase.")
        return game_context
    if "current_proposal_id" not in game_context:
        ("Current proposal is required for voting phase.")
        return game_context
    if "new_scenario" not in game_context:
        ("New scenario is required for voting phase.")
        return game_context
    

    votes = {}
    proposer_key = players[game_context["turn_order"][game_context["current_turn"]]].key  # Determine proposer
    proposal_id = game_context["current_proposal_id"]
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
                f"Proposal ID: {game_context['current_proposal_id']}.\n"
                f"Scenario: {json.dumps(game_context['new_scenario'])}.\n"
                "Be decisive in your vote and explicitly state your choice (Yes, No, or Abstain), only vote Yes if you strongly support the proposal,"
                "Consider the following:\n"
                f"- The proposer of this proposal is {voter.name}. Your current relationship with them is {relationship_value}.\n"
                "- Do not vote no on your own proposal.\n"
                "- Does this proposal align with your beliefs and priorities?\n"
                "- Will this proposal help achieve your personal objectives, or does it conflict with them?\n"
                "Explain your reasoning succinctly in a few sentences. Do not submit a proposal just vote."
            )
        }
        if not off_chain:
            vote_input["content"] += (
                "The only function to call is vote_onchain(proposal_id: int, vote: str).\n"
                "vote_onchain using the proposal ID. factor in your personal goals, and your relationship with the proposer.\n"
                "Do not submit a proposal! the only function to call is vote_onchain. Do not vote more than once.\n"
            )
        print("\n\033[93mVoter:\033[0m", voter.name, voter.key)
        vote_response = client.run(agent=voter.agent, messages=[vote_input], context_variables={"agent_key":voter.key}, stream=False)

        vote_messages = vote_response.messages
        votes[voter.key] = extract_vote(vote_messages[-1]["content"])
        if "votes" not in game_context:
            game_context["votes"] = {}
        if "votes_reasoning" not in game_context:
            game_context["votes_reasoning"] = {}
        game_context["votes"][voter.name] = votes[voter.key]
        game_context["votes_reasoning"][voter.name] = vote_messages[-1]["content"]
        pretty_print_messages(vote_messages)
        update_narrative(game_context, proposal=game_context["current_proposal"], vote_message=f"{voter.name}: {vote_messages[-1]['content']}", player_vote=votes[voter.key])

    return game_context

def resolve_round(game_context, world_context, players, gm, client, off_chain, **kwargs):
    if "votes" not in game_context:
        print("Votes are required for round resolution.")
        return game_context
    game_context = resolve_round_with_relationships(game_context, game_context["votes"], game_context["new_scenario"])
    # print("\n\033[93mRound Resolution:\033[0m", game_context)
    return game_context


def round_resolution(game_context, world_context, players, gm, client, off_chain, **kwargs):
    if game_context["last_decision"] == "Proposal Passed":
        roll_result = roll_d20()
        print("\033[1mThe proposal passed but did it do what it was supposed to do?\033[0m")
        print(f"\n🎲 \033[93mRound \033[91mResolution \033[92mROLL \033[94mD20:\033[0m : {roll_result} 🎲\n")
        
        # GM interprets the roll result
        if roll_result == 20:
            gm_message_content = (
                f"Proposal passed but the action in the proposal is a resounding success! Not only does it solve the current challenge, "
                f"but it also inspires unity and optimism in the community."
            )
        elif 15 <= roll_result <= 19:
            gm_message_content = (
                f"Proposal passed but the action in the proposal succeeds with notable benefits. While some tensions remain, the colony "
                f"sees progress in addressing the challenge."
            )
        elif 10 <= roll_result <= 14:
            gm_message_content = (
                f"Proposal passed but the action in the proposal has limited success. It alleviates some immediate pressures, but deeper "
                f"issues persist."
            )
        elif 2 <= roll_result <= 9:
            gm_message_content = (
                f"Proposal passed but the action in the proposal falls short of expectations, introducing minor problems. Factional tensions grow, "
                f"and the challenge remains unresolved."
            )
        elif roll_result == 1:
            gm_message_content = (
                f"Proposal passed but the action in the proposal critically fails, backfiring in an unexpected way. New problems emerge, "
                f"worsening the situation for the population."
            )
        
    # If the proposal failed, add a generic failure message to the narrative
    else:
        gm_message_content = (
            f"The proposal failed to gain enough support. Factional tensions rise, leaving the challenge unresolved."
        )

    proposal_resolution = client.run(agent=gm.agent, messages=[
        {
            "role": "user", 
            "content": (
                f"Narrative Summary: {game_context['narrative_summary']}.\n"
                f"Current Scenario: {json.dumps(game_context['new_scenario'])}.\n"
                f"Proposal: {game_context['current_proposal']}.\n"
                f"Result: {gm_message_content}"
                "Based on the result of the proposal, provide a narrative resolution to the round. "
            )
        },
        ], stream=False)
    proposal_resolution_messages = proposal_resolution.messages
    pretty_print_messages(proposal_resolution_messages)
    update_narrative(game_context, gm_situation=proposal_resolution_messages[-1]["content"])
    if "proposal_resolution" not in game_context:
        game_context["proposal_resolution"] = {}
    game_context["proposal_resolution"] = proposal_resolution_messages[-1]["content"]
    # clear current proposal and current proposal id
    game_context["current_proposal"] = None
    game_context["current_proposal_id"] = None
    return game_context


