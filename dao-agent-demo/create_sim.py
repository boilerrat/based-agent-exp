import json
import os
import sys
import re
from pathlib import Path

from typing import Union, List, Dict, TypedDict

from openai import OpenAI

from dotenv import dotenv_values, load_dotenv

config = dotenv_values(".env")
load_dotenv()

def generate_world_json(prompt):
    openai_client = OpenAI()
    system_prompt = {
            "role": "system",
            "content": f"you are a AI that only replies in json format."
        }

    # Load the prompt
    input_prompt = {
        "role": "user",
        "content": ("Generate a world JSON for a game based on the prompt." 
              f"Prompt: {prompt}\n"
              "Your response should be in the following json format:\n"
            "{\n"
                '"Name": "The name of the world.",\n'
                '"Description": "The description of the world.",\n'
                '"KeyChallenges: ["Challenge 1", "Challenge 2", "Challenge 3"],\n'
            "}\n"
            "Do not include any additional text or explanations. Only provide the response in this format.")}


    response = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=[system_prompt, input_prompt]

    )
    message = response.choices[0].message.content.strip()

    print("Message:", message)
    try:
        return json.loads(message)
    except Exception as e:
        raise f"Error generating world json: {str(e)}"

def generate_character_json(prompt):
    openai_client = OpenAI()
    system_prompt = {
            "role": "system",
            "content": f"you are a AI that only replies in json format."
        }

    # Load the prompt
    input_prompt = {
        "role": "user",
        "content": ("Generate 3 player characters based on the prompt." 
              f"Prompt: {prompt}\n"
              "Your response should be in the following json format:\n"
            "[\n"
                '{"Name": "The name of the character 1.",\n'
                '"Identity": "The Identity of the character 1."\n'
                '"Functionality": "The functionality of the character 1.",\n'
                '"Communications": "The communications of the character 1.",\n'
                '"Platform": "The platform of the character 1.",\n'
                '"Goal": "The goal of the character 1."},\n'
                '},\n'
                '{"Name": "The name of the character 2.",\n'
                '"Identity": "The Identity of the character 2."\n'
                '"Functionality": "The functionality of the character 2.",\n'
                '"Communications": "The communications of the character 2.",\n'
                '"Platform": "The platform of the character 2.",\n'
                '"Goal": "The goal of the character 2."},\n'
                '},\n'
                '{"Name": "The name of the character 3.",\n'
                '"Identity": "The Identity of the character 3."\n'
                '"Functionality": "The functionality of the character 3.",\n'
                '"Communications": "The communications of the character 3.",\n'
                '"Platform": "The platform of the character 3.",\n'
                '"Goal": "The goal of the character 3."},\n'
                '},\n'
            "]\n"
            "Do not include any additional text or explanations. Only provide the response in this format.")}


    response = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=[system_prompt, input_prompt]

    )
    message = response.choices[0].message.content.strip()

    try:
        return json.loads(message)
    except Exception as e:
        raise f"Error generating character json: {str(e)}"

def generate_gm_json(prompt):
    openai_client = OpenAI()
    system_prompt = {
            "role": "system",
            "content": f"you are a AI that only replies in json format."
        }

    # Load the prompt
    input_prompt = {
        "role": "user",
        "content": ("Generate a gm character JSON for a game based on the prompt." 
              f"Prompt: {prompt}\n"
              "Your response should be in the following json format:\n"
            "{\n"
                '"Name": "The name of the gm.",\n'
                '"Identity": "The identity of the gm.",\n'
                '"Functionality": "The functionality of the gm.",\n'
                '"ScenarioBuildingRules": "The scenario building rules of the gm.",\n'
                '"NarrativeFocus": "The narrative focus of the gm.",\n'
                '"Platform": "The platform of the gm.",\n'
                '"Extra": "Extra information about the gm."\n'
            "}\n"
            "Do not include any additional text or explanations. Only provide the response in this format.")}


    response = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=[system_prompt, input_prompt]

    )
    message = response.choices[0].message.content.strip()

    # try to load the json into a dict
    try:
        return json.loads(message)
    except Exception as e:
        raise f"Error generating gm json: {str(e)}"

def slugify(value):
    value = str(value)
    value = re.sub(r'[^a-zA-Z0-9\s-]', '', value)
    value = value.strip().lower()
    value = re.sub(r'[-\s]+', '_', value)
    return value

class PlayerConfig(TypedDict):
    Name: str
    Identity: str
    Functionality: str
    Communications: str
    Platform: str
    Goal: str

class GmConfig(TypedDict):
    Name: str
    Identity: str
    Functionality: str
    ScenarioBuildingRules: str
    NarrativeFocus: str
    Platform: str
    Extra: str

class WorldConfig(TypedDict):
    Name: str
    Description: str
    KeyChallenges: List[str]

def generate_world_simulation(
    world_config: WorldConfig,
    gm_config: GmConfig,
    player_configs: List[PlayerConfig],  # Using PlayerConfig TypedDict,
    phases: List[str] = [
        "generate_summary",
        "introduce_scenario",
        "deliberation",
        "soft_signal",
        "negotiation",
        "submit_proposal",
        "voting",
        "resolve_round",
        "round_resolution"
    ]
) -> str:
    """
    Generates a world file and 4 character files (3 players, 1 GM) for a new simulation

    Args:
        world_config (WorldConfig): The configuration for the world simulation
        gm_config (GmConfig): The configuration for the GM character
        player_configs (List[PlayerConfig]): The configurations for the player characters
        phases (List[str]): The phases of the simulation

    Returns:
        str: The status message
    """

    world_dir = Path("worlds")

    world_slug = slugify(world_config["Name"])
    character_dir = Path(f"characters/{world_slug}")
    world_dir.mkdir(parents=True, exist_ok=True)
    character_dir.mkdir(parents=True, exist_ok=True)

    # Generate and save world file
    world_data = {
        "Type": "World",
        "Name": world_config["Name"],
        "World": {
            "name": world_config["Name"],
            "description": world_config["Description"],
            "key_challenges": world_config["KeyChallenges"]
        },
        "Phases": phases,
        "Initial": {
            "resources": {},
            "population": {},
            "relationships": {},
            "gm": "",
            "players": [],
            "turn_order": [],
            "current_proposal": "",
            "current_turn": 0,
            "round": 0,
            "narrative": []
        }
    }
    world_file_path = f"{world_dir}/{world_slug}.json"

    # Generate and save GM character file
    gm_data = {
        "Type": "GM",
        "Name": gm_config["Name"],
        "Key": "GM_0",
        "Identity": gm_config["Identity"],
        "Functionality": gm_config["Functionality"],
        "ScenarioBuildingRules": gm_config["ScenarioBuildingRules"],
        "NarrativeFocus": gm_config["NarrativeFocus"],
        "Platform": gm_config["Platform"],
        "Extra": gm_config["Extra"]
    }
    gm_file_path = f"{character_dir}/{slugify(gm_config['Name'])}.json"

    try:
        print("creating files")
        # Generate and save player character files
        for player in player_configs:
            character_slug = slugify(player['Name'])
            player["Key"] = f"PLAYER_{player_configs.index(player)}"
            player["Type"] = "Player"

            player_file_path = f"{character_dir}/{character_slug}.json"
            with open(player_file_path, "w") as player_file:
                try:
                    json.dump(player, player_file, indent=4)
                    print(f"Player file saved to {player_file_path}")
                    world_player_file_path = f"{world_slug}/{character_slug}.json"
                    world_data["Initial"]["players"].append(world_player_file_path)
                except Exception as e:
                    print(f"Error generating character simulation: {str(e)}")
                    return f"Error generating character simulation: {str(e)}"
            print(f"Player file saved to {player_file_path}")
        
        world_data["Initial"]["turn_order"] = list(range(len(player_configs)))    
        world_gm_file_path = f"{world_slug}/{slugify(gm_config['Name'])}.json"
        world_data["Initial"]["gm"] = world_gm_file_path

        with open(world_file_path, "w") as world_file:
            json.dump(world_data, world_file, indent=4)
        print(f"World file saved to {world_file_path}")
        with open(gm_file_path, "w") as gm_file:
            json.dump(gm_data, gm_file, indent=4)
        print(f"GM file saved to {gm_file_path}")

    except Exception as e:
        return f"Error generating world simulation: {str(e)}"

    print(f"GM file saved to {gm_file_path}")
    return f"Simulation files saved to {world_file_path}"



def main(): 

    user_input = input(
            "\nEnter a prompt to generate the simulation files: "
        )
    
    world_config = generate_world_json(user_input)
    player_configs = generate_character_json(user_input)
    gm_config = generate_gm_json(user_input)

    generate_world_simulation(world_config, gm_config, player_configs)

if __name__ == "__main__":
    main()