import json

class AgentHandler:
    def __init__(self, instructions):
        self.instructions = instructions
        self.key = instructions["Key"]
        self.name = instructions["Name"]
        self.type = instructions["Type"]
        self.address = None
        self.agent = None

        

    def set_address(self, address):
        self.address = address
    
    def set_agent(self, agent):
        self.agent = agent

    def get_instructions_string(self):
        return ", ".join(f"{key}: {value}" for key, value in self.instructions.items())


    def get_instructions_from_json(self):
        if self.instructions["Type"] == "GM":
            gm_extra_instructions = f"""
            GovernanceStructure: "The governance structure is a DAO. 1 player has initiative to make a proposal each round. there are several phases of each round: "
            "gm introduces a scenario, players deliberate and negotiate, the player with initiative makes a proposal, all players vote on the proposal,"
            "the gm resolves the proposal and checks if the proposal actions were a success with a d20."
            """
            return json.dumps(self.instructions) + gm_extra_instructions
        else:
            player_extra_instructions = f"""
            Functionality: You have the ability to submit a proposal on chain and to generate art. But only do this if specifically prompted to do so.
            """
            return json.dumps(self.instructions) + player_extra_instructions
    def __repr__(self):
        return f"Agent(key={self.key}, name={self.name})"