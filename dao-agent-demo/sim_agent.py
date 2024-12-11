class SimAgent:
    def __init__(self, instructions):
        self.instructions = instructions
        self.key = instructions["Key"]
        self.name = instructions["Name"]
        self.private_key = None
        self.agent = None

        

    def set_private_key(self, private_key):
        self.private_key = private_key
    
    def set_agent(self, agent):
        self.agent = agent

    def get_instructions_string(self):
        return ", ".join(f"{key}: {value}" for key, value in self.instructions.items())


    def __repr__(self):
        return f"Agent(key={self.key}, name={self.name})"