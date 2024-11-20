import json

character_file_json = {}

def set_character_file(file):
    global character_file_json
    with open(f"characters/{file}", "r") as character_file:
        character_file_json = json.load(character_file)

def get_character_json():
    return character_file_json

def get_instructions():
    return f"""
    Identity: {character_file_json["Identity"]}
    Functionality: {character_file_json["Functionality"]}
    Communications: {character_file_json["Communications"]}
    Friends: {character_file_json["Friends"]}
    Interests: {character_file_json["Interests"]}
    Extra: {character_file_json["Extra"]}
    """

def get_thoughts():
    return f"""
    {character_file_json["pre_autonomous_thought"]}
    {character_file_json["autonomous_thoughts"]}
    {character_file_json["post_autonomous_thought"]}
    """ 