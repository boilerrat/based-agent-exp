
from decimal import Decimal
from typing import Union, List, Dict, TypedDict

from openai import OpenAI
from swarm import Agent

from dao_agent_demo.prompt_helpers import get_instructions_from_json, get_character_json

from dao_agent_demo.tools import (
    get_knowledge_by_keywords,
    get_agent_address,
    get_dao_proposals,
    get_passed_dao_proposals,
    get_dao_proposal,
    get_proposal_count,
    get_proposal_votes_data,
    summon_meme_token_dao,
    summon_crowd_fund_dao,
    commit_memory,
    get_all_memories,
    generate_art,
    cast_to_farcaster,
    check_cast_replies,
    check_recent_unacted_cast_notifications,
    check_all_past_notifications,
    mark_notification_as_acted,
    cast_reply,
    check_recent_agent_casts,
    check_recent_user_casts,
    check_user_profile,
    submit_dao_proposal_onchain,
    vote_onchain,
)

# agent routing tools
def route_to_agent(agent_name: str):
    """
    Route a notification to an agent.
    """
    agent_name = agent_name.lower()
    print("routing to", agent_name)
    operator_agent = operator_agent_list[agent_name]["file_path"]
    file_json = get_character_json(operator_agent, character_type="OPERATOR")
    instructions = get_instructions_from_json(file_json, character_type="OPERATOR")
    print("instructions", instructions)
    print("functions", operator_agent_list[agent_name]["functions"])
    if operator_agent_list[agent_name]["agent"] is None:
        agent = Agent(
            name=agent_name,
            instructions=instructions,
            model="gpt-4o-mini",
            functions=operator_agent_list[agent_name]["functions"]
        )
        operator_agent_list[agent_name]["agent"] = agent
    else:
        agent = operator_agent_list[agent_name]["agent"]
    return agent

def route_to_synthesizer():
    """
    Route a notification to the synthesizer.
    """
    return route_to_agent("synthesizer")

def route_to_crier():
    """
    Route a notification to the governor.
    """
    return route_to_agent("crier")

def route_to_bard():
    """
    Route a notification to the bard.
    """
    return route_to_agent("bard")

def route_to_taskmaster():
    """
    Route a notification to the taskmaster.
    """
    return route_to_agent("taskmaster")

def route_to_governor():
    """
    Route a notification to the governor.
    """
    return route_to_agent("governor")

# agent list
operator_agent_list = {
    "alderman":{
        "file_path":"operators/alderman.json",
        "functions":[route_to_agent],
        "agent": None
        },
    "taskmaster":{
        "file_path":"operators/taskmaster.json",
        "functions":[summon_crowd_fund_dao, summon_meme_token_dao, get_agent_address, route_to_synthesizer],
        "agent": None
        },
    "maester":{
        "file_path":"operators/maester.json",
        "functions":[get_knowledge_by_keywords, route_to_synthesizer],
        "agent": None
        },
    "bard":{
        "file_path":"operators/bard.json",
        "functions":[generate_art, route_to_taskmaster],
        "agent": None
        },
    "governor":{
        "file_path":"operators/governor.json",
        "functions":[],
        "agent": None
        },
    "synthesizer":{
        "file_path":"operators/synthesizer.json",
        "functions":[route_to_crier],
        "agent": None
        },
    "crier":{
        "file_path":"operators/crier.json",
        "functions":[cast_to_farcaster],
        "agent": None
        },
}

# alderman agent (triage)
def alderman_agent():
    """
    Alderman agent (triage)
    """
    file_json = get_character_json(operator_agent_list["alderman"]["file_path"], character_type="OPERATOR")
    instructions = get_instructions_from_json(file_json, character_type="OPERATOR")
    return Agent(
        name="Alderman",
        instructions=instructions,
        model="gpt-4o-mini",
        functions=operator_agent_list["alderman"]["functions"]
    )

# dao agent (general purpose)
def dao_agent(instructions: str ): 
    return Agent(
    name="Agent",
    instructions=instructions,
    model="gpt-4o-mini",
    functions=[
        get_balance,
        get_agent_address,
        generate_art,  # Uncomment this line if you have configured the OpenAI API
        cast_to_farcaster,
        check_cast_replies,
        check_recent_unacted_cast_notifications,
        check_all_past_notifications,
        mark_notification_as_acted,
        cast_reply,
        check_recent_agent_casts,
        check_recent_user_casts,
        check_user_profile,
        submit_dao_proposal_onchain,
        vote_onchain,
        # get_current_proposal_count
        get_dao_proposals,
        get_passed_dao_proposals,
        get_dao_proposal,
        get_proposal_count,
        get_proposal_votes_data,
        summon_meme_token_dao,
        summon_crowd_fund_dao,
        commit_memory,
        get_all_memories,
        get_knowledge_by_keywords

    ],
    )

# gm agent (game master)
def gm_agent(instructions: str, name: str = "GM", off_chain: bool = True): 
    print(f"\033[93mGame master:\033[0m\n{instructions}")
    on_chain_functions = [
        get_dao_proposals,
        get_dao_proposal,
    ]
    functions = [generate_art] 
    if not off_chain:
        functions.extend(on_chain_functions)
    return Agent(
        name=name,
        instructions=instructions,
        model="gpt-4o-mini",
        functions=functions
    )

# player agent (player)
def player_agent(instructions: str, name: str = "Player", off_chain: bool = True): 
    on_chain_functions = [
        submit_dao_proposal_onchain,
        vote_onchain,
    ]
    functions = [generate_art] 
    if not off_chain:
        functions.extend(on_chain_functions)
    return Agent(
        name=name,
        instructions=instructions,
        model="gpt-4o-mini",
        functions=functions,
    )



    
