import json
import random

character_file_json = {}

def roll_d20():
    """
    Rolls a d20 to determine the outcome of a proposal.
    
    Returns:
        int: The roll result (1-20).
    """
    return random.randint(1, 20)

def set_character_file(file):
    global character_file_json
    print(f"loaded characters/{file}")
    with open(f"characters/{file}", "r") as character_file:
        character_file_json = json.load(character_file)
        validate_character_json(character_file_json)

def get_character_json():
    return character_file_json

def get_sim_character_json(file) -> dict:
    sim_character_file_json = {}
    print(f"loaded characters/{file}")
    with open(f"characters/{file}", "r") as character_file:
        sim_character_file_json = json.load(character_file)
        validate_character_json(character_file_json)
    return sim_character_file_json

def get_instructions():
    return f"""
    Identity: {character_file_json["Identity"]}
    Functionality: {character_file_json["Functionality"]}
    Communications: {character_file_json["Communications"]}
    Friends: {character_file_json["Friends"]}
    Interests: {character_file_json["Interests"]}
    Platform: {character_file_json["Platform"]}
    Extra: {character_file_json["Extra"]}
    """

def get_thoughts():
    return f"""
    {character_file_json["pre_autonomous_thought"]}
    {character_file_json["autonomous_thoughts"]}
    {character_file_json["post_autonomous_thought"]}
    """ 

def validate_character_json(character_json):
    required_fields = [
        "Name", "Identity", "Functionality", "Communications", "Friends",
        "Interests", "Platform", "Extra", "pre_autonomous_thought",
        "autonomous_thoughts", "post_autonomous_thought"
    ]
    for field in required_fields:
        if field not in character_json:
            raise ValueError(f"Missing required field: {field}")
        
def dao_simulation_setup() -> tuple:
    """
    Returns a tuple of initial_context, players, gm
    """

    # todo: load from file
    initial_context = {
        "resources": {"total": 100, "allocated": 0},
        "relationships": {
            "player1-player2": 0,
            "player1-player3": 0,
            "player2-player3": 0,
            "player2-player1": 0,
            "player3-player1": 0,
            "player3-player2": 0,
        },
        "gm": "gm.json",
        "players": ["player1.json", "player2.json", "player3.json"],
        "turn_order": [0, 1, 2],  # Corresponds to player indices
        "current_proposal": None,
        "round": 0,
        "narrative": []  # Initialize narrative log
    }

    players = [get_sim_character_json(file) for file in initial_context["players"]]
    gm = get_sim_character_json(initial_context["gm"])
    
    return initial_context, players, gm

def check_alignment(soft_signals):
    """
    Checks if there is alignment among players based on soft signals.

    Args:
        soft_signals (dict): A dictionary of player signals, where each key is a player name
                             and each value is a dictionary of "For" or "Against" evaluations 
                             for each suggestion.

    Returns:
        bool: True if alignment exists, False otherwise.
    """
    suggestion_support = {}

    # Aggregate support counts
    for player_signals in soft_signals.values():
        for suggestion, vote in player_signals.items():
            if suggestion not in suggestion_support:
                suggestion_support[suggestion] = {"For": 0, "Against": 0}
            if vote.lower() == "for":
                suggestion_support[suggestion]["For"] += 1
            elif vote.lower() == "against":
                suggestion_support[suggestion]["Against"] += 1

    # Check if any suggestion has majority support
    for suggestion, counts in suggestion_support.items():
        if counts["For"] > counts["Against"]:
            return True  # Found alignment on this suggestion

    return False  # No alignment found


def extract_vote(vote_text):
    """
    Extracts the vote ('Yes', 'No', or 'Abstain') from a verbose response.

    Args:
        vote_text (str): The full vote text.

    Returns:
        str: The extracted vote ('Yes', 'No', or 'Abstain').
    """
    if "yes" in vote_text.lower():
        return "Yes"
    elif "no" in vote_text.lower():
        return "No"
    elif "abstain" in vote_text.lower():
        return "Abstain"
    return "Unknown"  # Default if vote is unclear

def update_narrative(game_context, proposer_name=None, proposal=None, outcome=None, gm_situation=None) -> dict:
    """
    Updates the narrative log based on GM situations or player actions.

    Args:
        game_context (dict): Current game state.
        proposer_name (str): Name of the proposer (if applicable).
        proposal (str): The proposal text (if applicable).
        outcome (str): Outcome of the proposal ("Proposal Passed" or "Proposal Failed") (if applicable).
        gm_situation (str): Situation introduced by the GM (if applicable).

    Returns:
        dict: The updated game context with the narrative log
    """
    if gm_situation:
        # Log GM-introduced situations
        event_description = (
            f"Round {game_context['round']}: New Element Introduced by GM.\n"
            f"Situation: {gm_situation}\n"
            "This element sets the stage for the colony's next decisions."
        )
        game_context["narrative"].append({"tag": "GM_ELEMENT", "description": event_description})
        return game_context
    
    if proposal and outcome:
        # Log the results of a player's proposal
        if outcome == "Proposal Passed":
            event_description = (
                f"Round {game_context['round']}: {proposer_name}'s proposal passed.\n"
                f"Proposal: {proposal}\n"
                f"This decision has reshaped the future of Artemis Base, addressing the current challenges."
            )
        else:
            event_description = (
                f"Round {game_context['round']}: {proposer_name}'s proposal failed.\n"
                f"Proposal: {proposal}\n"
                f"Factional tensions rise as no consensus could be reached."
            )
        game_context["narrative"].append({"tag": "Outcome", "description": event_description})
        return game_context