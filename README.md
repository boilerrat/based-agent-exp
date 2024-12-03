# DAO AI Agent Local Setup

This guide outlines the steps to set up a local development environment for an AI agent that interacts with Warpcast, the Graph, and DAOs on EVM chains.

---

## Prerequisites
1. **Virtual Environment (VM):** Ensure you have Python and a virtual environment tool installed.
2. **Poetry:** Dependency management tool for Python.
3. **API Keys:**
   - OpenAI Pro account https://openai.com/index/openai-api/
   - New Warpcast account for your agent
   - NANAR API account https://dev.neynar.com/
   - The Graph API account https://thegraph.com/studio
4. **RPC:** Use a local node or a service like Infura, Alchemy or a free/public RPC for EVM interactions.

---

## Setup Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Set Up a Virtual Environment
```bash
python3 -m venv my-venv
source my-venv/bin/activate  # For Linux/Mac
```

## install poetry
```
pip3 install poetry
```

### 3. Install Dependencies with Poetry
```bash
poetry install
```

This installs libraries for interacting with OpenAI, and other required tools.

### 4. Configure `.env` File
Create a `.env` file and fill in the following keys:
- `OPENAI_API_KEY` create key at https://openai.com/index/openai-api/
- `FARCASTER_FID` can get this from the api page https://docs.neynar.com/reference/lookup-user-by-username
- `FARCASTER_CHANNEL_ID` this is the current default channel for testing (optional)
- `NANAR_API_KEY` can get key at https://dev.neynar.com/
- `NAYNAR_SIGNER_UUID` need to create this from the naynar dev dashboard
- `GRAPH_KEY` can get from https://thegraph.com/studio
- `WEB3_PROVIDER_URI`
- `TARGET_CHAIN` chain id of the target EVM chain

agent wallet data (can use create_wallet.py for a new one)
- `AGENT_MNEMONIC`
- `AGENT_PRIVATE_KEY`
- `AGENT_ADDR`

If working with a DAO for voting and proposals (currently on a single dao is supported)
- `TARGET_DAO`

currently using imgbb for more persistent image hosting
- `IMG_BB_API_KEY`

Refer to the documentation of respective services to generate these keys.


### 5. Create a Wallet
Run the wallet creation script to set up a new wallet if you didn't bring your own:
```bash
python create_wallet.py
```

This generates a new account and mnemonic. Add these values to the `.env` file.

### 6. Fund the Wallet
If interacting on-chain, fund the wallet with a small amount of eth for gas fees.

---

## Running the Agent

### Start the Agent

cd into dao-agent-demo

```bash
python run.py
```
or to load a character
```bash
python run.py <character file json>
```
Options available:
1. **Chat Mode:** Directly chat with the agent for tasks like generating proposals or interacting with DAOs.
2. **Autonomous Mode:** The agent operates autonomously, performing actions like replying on Warpcast, creating proposals, or notifying about updates.
3 **2 agent demo:** demo of 2 agents simulating a conversation

### Customize Agent Behavior
Modify the `characters` folder to define:
- **Identity and initial prompt** in JSON files.
- **Autonomous thoughts** for periodic actions.

---

## Key Files and Utilities
- **`agent.py`:** Core functions for the agent.
- **`constants_utils.py`:** Contract addresses and configurations.
- **`helpers and utils`:** Includes DAO summoning tools, Warpcast, and Graph, json store utility wrappers.
- **`run.py`:** Handles agent initialization and interval control for autonomous actions.
- **`characters/`:** json files that define initial prompts and auto thoughts for agents

---

## Additional Notes
- **Intervals:** The autonomous mode executes random actions every 5 to 60 minutes by default. This can be adjusted in `run.py`.
- **Memory Management:** There is a tinydb json store for committing memories, use this to avoid repetitive tasks

---

For detailed configuration or additional features, refer to the helper files and modify as needed.



> this is a repo to experiment on stuff, not for production use

### local setup walkthrough and notes
video recap and walkthrough: https://hackmd.io/VC-0zcJCTW-cwNUWwh4s8Q

walkthrough loom: https://www.loom.com/share/2094a79bfd71452894e1cd98280d0292?sid=de350ca5-5ca0-41ec-a60d-1b1a03fd9068

## Introduction

This is a simple lightweight framework to interact with agents using openai swarm  [Documentation](https://github.com/openai/swarm). There are several example functions to summon, interact and retrieve info from DAOs. There are farcaster tools to cast and retrieve casts. This was originally based on the Based Agent playground [Repo](https://github.com/murrlincoln/Based-Agent/tree/main/Based-Agent)

### Key Features

- **Autonomous execution**: The agent thinks, decides, and acts onchain autonomously.
- **Token deployement**: Creates a presale token with fee ditributions to refferers
- **Balance checks**: Keep tabs on wallet balances.
- **Crowd fund deployment**: Can deploy a yeeter crowdfund.
- **Art generation via DALL-E**: Generate artwork using AI.
- **Whatever you want**: Add in features and share them with us!

## Get Started in Minutes!

### 1️⃣ Prerequisites
- Python 3.7+



## Other Info

**NAYNAR farcaster api**
Sign up for a Naynar api key
https://neynar.com/

You will need to use their dash board interface to "Make a Bot" to get a signer key

Here are a few example endpoints
- Get conversation https://docs.neynar.com/reference/lookup-cast-conversation
- Publish cast https://docs.neynar.com/reference/publish-cast


### 3️⃣ Running the Agent
Create a new python venv. You will need pip and poetry installed

### Customize Character
You can edit the character by creating your own character json file in the /characters folder


## 🔧 Available Functions

Unlock a world of possibilities with these built-in functions:

### DAO operation

- `summon_dao`
- `vote_on_dao_proposal`
- `submit_proposa`
- `get_dao_proposals`
- `get_dao_proposal`
- `get_dao_proposals_count`

### Farcaster operations

- `cast_to_farcaster(content: str)`
- `check_cast_replies()`
- `check_cast_notifications()`
- `mark_notifications_as_seen()`
- `cast_reply(content: str, parentHash: str, parent_fid: int)`
- `check_recent_agent_casts()`
- `check_recent_user_casts(fid: str)`
- `check_user_profile(fid: str)`

### Utilities

- `generate_art(prompt)`: Generate art using DALL-E based on a text prompt.
- `get_agent_address`: get the address of the current agent
- `commit_memory`: store a memory for long term

## 🤖 Agent Functionality

### Agents.py
All of the functionality for the DAO Agent resides within `agents.py`. This is the central hub where you can add new capabilities, allowing the agent to perform a wide range of tasks. 

By incorporating additional libraries, you can extend the agent's reach beyond blockchain interactions to include Web2 functionalities, such as posting on Warpcast, etc.

## 🤖 Behind the Scenes

DAO Agent uses:

- **OpenAI Swarm**: Powers the agent's autonomous decision-making.


## ⚠️ Disclaimer

This project is for educational purposes only. Do not use with real assets or in production environments. Always exercise caution when interacting with blockchain technologies.
