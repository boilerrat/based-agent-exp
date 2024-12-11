import os
import json

from decimal import Decimal
from typing import Union

from openai import OpenAI
from swarm import Agent
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account


from farcaster_utils import FarcasterBot
from graph_utils import DaohausGraphData
from image_utils import ImageThumbnailer
from memory_retention_utils import MemoryRetention

from dao_summon_helpers import assemble_meme_summoner_args, calculate_dao_address, assemble_yeeter_summoner_args

# Load the ENS registrar and resolver ABIs
with open("abis/registrar_abi.json", "r") as abi_file:
    registrar_abi = json.load(abi_file)

with open("abis/baal_abi.json", "r") as abi_file:
    baal_abi = json.load(abi_file)

with open("abis/yeet24_hos_summoner_abi.json", "r") as abi_file:
    yeet24_hos_summoner_abi = json.load(abi_file)

with open("abis/gnosis_multisend_abi.json", "r") as abi_file:
    gnosis_multisend_abi = json.load(abi_file)


from constants_utils import (
    SUMMON_CONTRACTS,
)


from dotenv import dotenv_values

config = dotenv_values(".env")

PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY", "").replace('\\n', '\n')
TARGET_CHAIN = os.getenv("TARGET_CHAIN", "0x2105")

if not PRIVATE_KEY:
    raise EnvironmentError("The environment variable 'PRIVATE_KEY' is not set.")

# Initialize Web3 (connect to Ethereum network, e.g., Infura or local node)
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI")
print(f"Connecting to Web3 provider: {WEB3_PROVIDER_URI}")
if not WEB3_PROVIDER_URI:
    raise EnvironmentError("The environment variable 'WEB3_PROVIDER_URI' is not set.")

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

# Ensure Web3 connection is established
if not w3.is_connected():
    raise ConnectionError("Web3 provider connection failed.")

# Load the wallet
agent_wallet = Account.from_key(PRIVATE_KEY)

# Print wallet details
print(f"Wallet Address: {agent_wallet.address}")


# Function to get the balance of a specific asset
def get_balance(context_variables):
    """
    Get the eth balance of a specific asset in the agent's wallet.
    
    Returns:
        str: A message showing the current balance of the specified asset
    """

    balance = w3.eth.get_balance(agent_wallet.address)
    eth_balance = Web3().from_wei(balance, "ether")
        
    return f"Current eth balance: {eth_balance}"

# Function to get the address of the current agent
def get_agent_address():
    """
    Get the address of the current agent's wallet.

    Returns:
        str: The address of the agent
    """
    address = agent_wallet.address
    return f"Current address: {address}"

# Function to generate art using DALL-E (requires separate OpenAI API key)
def generate_art(prompt):
    """
    Generate art using DALL-E based on a text prompt.
    
    Args:
        prompt (str): Text description of the desired artwork
    
    Returns:
        str: Status message about the art generation, including the image URL if successful
    """
    try:
        client = OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url

        if os.getenv("IMG_BB_API_KEY"):
            # save image to imgbb

            image = ImageThumbnailer()
            image_url = image.upload_image(image_url)

        return f"Generated artwork available at: {image_url}"

    except Exception as e:
        return f"Error generating artwork: {str(e)}"

# functions to interact with daos
def vote_on_dao_proposal(proposal_id: str, vote: bool) -> str:
    """
    Vote on a DAO proposal.

    Args:
        proposal_id (str): The proposal ID.
        vote (bool): The vote.

    Returns:
        str: Success or error message.
    """
    dao_address = os.getenv("TARGET_DAO")
    if not isinstance(dao_address, str) or not isinstance(proposal_id, str) or not isinstance(vote, bool):
        return "Invalid input types"

    try:
        # Convert proposal_id to integer if necessary
        proposal_id_int = int(proposal_id)

        # Load the DAO contract
        dao_contract = w3.eth.contract(address=Web3.to_checksum_address(dao_address), abi=baal_abi)

        # Get the current gas price
        gas_price = w3.eth.gas_price  # Automatically fetches the current network gas price

        # Estimate the gas required for the transaction
        try:
            estimated_gas = dao_contract.functions.submitVote(proposal_id_int, vote).estimate_gas({
                "from": agent_wallet.address,
            })
        except Exception as e:
            return f"Error estimating gas: {str(e)}"

        # Prepare transaction
        tx = dao_contract.functions.submitVote(proposal_id_int, vote).build_transaction({
            "from": agent_wallet.address,
            "nonce": w3.eth.get_transaction_count(agent_wallet.address),
            "gas": estimated_gas,
            "gasPrice": gas_price,
        })

        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Wait for transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return f"Successfully voted on proposal id {proposal_id} for dao address {dao_address}, tx hash: {tx_hash.hex()}"

    except Exception as e:
        return f"Error Voting in DAO: {str(e)}"

def summon_meme_token_dao(dao_name, token_symbol, image, description, agent_wallet_address):
    """
    Summon a meme token DAO.

    Args:
        dao_name (str): Name of the DAO.
        token_symbol (str): Token symbol for the DAO.
        image (str): Image URL for the DAO avatar.
        description (str): Description of the DAO.
        agent_wallet_address (str): Address of the agent wallet.

    Returns:
        str: Success or error message.
    """
    try:
        # Assemble arguments for summoning the DAO
        summon_args = assemble_meme_summoner_args(dao_name, token_symbol, image, description, agent_wallet_address, TARGET_CHAIN)

        initialization_loot_token_params = summon_args[0]
        initialization_share_token_params = summon_args[1]
        initialization_shaman_params = summon_args[2]
        post_initialization_actions = summon_args[3]
        salt_nonce = int(summon_args[4])

        summon_args_dict = {
            "initializationLootTokenParams": Web3.to_hex(initialization_loot_token_params),
            "initializationShareTokenParams": Web3.to_hex(initialization_share_token_params),
            "initializationShamanParams": Web3.to_hex(initialization_shaman_params),
            "postInitializationActions": post_initialization_actions,
            "saltNonce": salt_nonce,
        }

        # Load the summoner contract
        summoner_address = SUMMON_CONTRACTS['YEET24_SUMMONER'][TARGET_CHAIN]
        summoner_contract = w3.eth.contract(address=Web3.to_checksum_address(summoner_address), abi=yeet24_hos_summoner_abi)

        try:
            estimated_gas = summoner_contract.functions.summonBaalFromReferrer(
                summon_args_dict["initializationLootTokenParams"],
                summon_args_dict["initializationShareTokenParams"],
                summon_args_dict["initializationShamanParams"],
                summon_args_dict["postInitializationActions"],
                summon_args_dict["saltNonce"]
            ).estimate_gas({
                "from": agent_wallet.address,
            })
            print(f"Estimated gas: {estimated_gas}")
        except Exception as e:
            return f"Error estimating gas: {str(e)}"
        # Build the transaction
        tx = summoner_contract.functions.summonBaalFromReferrer(
            summon_args_dict["initializationLootTokenParams"],
            summon_args_dict["initializationShareTokenParams"],
            summon_args_dict["initializationShamanParams"],
            summon_args_dict["postInitializationActions"],
            summon_args_dict["saltNonce"]
        ).build_transaction({
            "from": agent_wallet.address,
            "nonce": w3.eth.get_transaction_count(agent_wallet.address),
            "gas": estimated_gas,
            "gasPrice": w3.eth.gas_price,
        })

        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for the transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # Return success message
        dao_address = calculate_dao_address(salt_nonce)
        return f"Successfully summoned DAO {dao_address}. You can view it at https://speedball.daohaus.club/"

    except Exception as e:
        # Truncate or simplify the error message
        error_message = str(e)
        truncated_message = error_message[:200] + "..." if len(error_message) > 200 else error_message
        return f"Error summoning DAO: {truncated_message}"

    
def summon_crowd_fund_dao(dao_name, token_symbol, image, description, verified_eth_addresses):
    """
    Summon a crowdfund DAO.

    Args:
        dao_name (str): Name of the DAO.
        token_symbol (str): Token symbol for the DAO.
        image (str): Image URL for the dao avatar
        description (str): Description of the DAO.
        verified_eth_addresses (str):  The verified eth addresses for the summoner.

    Returns:
        str: Success or error message.
    """
    try:
        # Assemble arguments for summoning the DAO
        summon_args = assemble_yeeter_summoner_args(dao_name, token_symbol, image, description, verified_eth_addresses, TARGET_CHAIN)


        initialization_loot_token_params = summon_args[0]
        initialization_share_token_params = summon_args[1]
        initialization_shaman_params = summon_args[2]
        post_initialization_actions = summon_args[3]
        salt_nonce = int(summon_args[4])

        summon_args_dict = {
            "initializationLootTokenParams": Web3.to_hex(initialization_loot_token_params),
            "initializationShareTokenParams": Web3.to_hex(initialization_share_token_params),
            "initializationShamanParams": Web3.to_hex(initialization_shaman_params),
            "postInitializationActions": post_initialization_actions,
            "saltNonce": str(salt_nonce),
        }

        print("Summoning crowdfund DAO at https://yeet.haus/ on Base...")

        # Load the summoner contract
        summoner_address = SUMMON_CONTRACTS['YEET24_SUMMONER'][TARGET_CHAIN]
        summoner_contract = w3.eth.contract(address=Web3.to_checksum_address(summoner_address), abi=yeet24_hos_summoner_abi)

        try:
            estimated_gas = summoner_contract.functions.summonBaalFromReferrer(
                summon_args_dict["initializationLootTokenParams"],
                summon_args_dict["initializationShareTokenParams"],
                summon_args_dict["initializationShamanParams"],
                summon_args_dict["postInitializationActions"],
                summon_args_dict["saltNonce"]
            ).estimate_gas({
                "from": agent_wallet.address,
            })
            print(f"Estimated gas: {estimated_gas}")
        except Exception as e:
            return f"Error estimating gas: {str(e)}"
        # Build the transaction
        tx = summoner_contract.functions.summonBaalFromReferrer(
            summon_args_dict["initializationLootTokenParams"],
            summon_args_dict["initializationShareTokenParams"],
            summon_args_dict["initializationShamanParams"],
            summon_args_dict["postInitializationActions"],
            summon_args_dict["saltNonce"]
        ).build_transaction({
            "from": agent_wallet.address,
            "nonce": w3.eth.get_transaction_count(agent_wallet.address),
            "gas": estimated_gas,
            "gasPrice": w3.eth.gas_price,
        })

        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for the transaction receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # Return success message
        dao_address = calculate_dao_address(salt_nonce)
        return f"Successfully summoned DAO {dao_address}. You can view it at https://yeet.haus"


    except Exception as e:
        return f"Error summoning DAO: {str(e)}"


# function to submit a proposal
def submit_dao_proposal_onchain(proposal_title: str, proposal_description: str, proposal_link: str) -> str:
    """
    Submit a DAO Proposal. 

    Args:
        proposal_title (str): The proposal title.
        proposal_description (str): The proposal description.
        proposal_link (str): The proposal link.

    Returns:
        str: Success or error message.
    """
    dao_address = os.getenv("TARGET_DAO")
    if not isinstance(dao_address, str) or not isinstance(proposal_title, str):
        return "Invalid input types"

    # Prepare the proposal details
    proposal_details = {
        "title": proposal_title,
        "description": proposal_description,
        "contentURI": proposal_link,
        "contentURIType": {"type": "static", "value": "url"},
        "proposalType": {"type": "static", "value": "SIGNAL"},
    }

    proposal = json.dumps(proposal_details)
    print("***", proposal)

    try:
        # Load the DAO contract
        dao_contract = w3.eth.contract(address=Web3.to_checksum_address(dao_address), abi=baal_abi)
        print(f"Submitting proposal for DAO address {dao_address}...")
        empty_bytes = "".encode('utf-8')
        # Convert integer arguments
        expiration = 0  # uint32
        baalGas = 0     # uint256

        try:
            estimated_gas =  dao_contract.functions.submitProposal(
            empty_bytes ,              # proposalData (empty string as per the original args_dict)
            expiration,             # expiration (default is "0")
            baalGas,             # baalGas (default is "0")
            proposal         # details (the serialized proposal details)
        ).estimate_gas({
                "from": agent_wallet.address,
            })
            print(f"Estimated gas: {estimated_gas}")
        except Exception as e:
            print(f"Error estimating gas: {str(e)}")
            return f"Error estimating gas: {str(e)}"

        
        # Prepare transaction arguments
        tx = dao_contract.functions.submitProposal(
            empty_bytes,     # proposalData (empty string as per the original args_dict)
            expiration,             # expiration (default is "0")
            baalGas,             # baalGas (default is "0")
            proposal         # details (the serialized proposal details)
        ).build_transaction({
            "from": agent_wallet.address,
            "nonce": w3.eth.get_transaction_count(agent_wallet.address),
            "gas": estimated_gas,  
            "gasPrice": w3.eth.gas_price,  # Dynamic gas price
        })

        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return f"Successfully submitted proposal for DAO address {dao_address}. Transaction hash: {tx_hash.hex()}"

    except Exception as e:
        error_message = str(e)
        truncated_message = error_message[:200] + "..." if len(error_message) > 200 else error_message
        print(f"Error submitting proposal: {truncated_message}")
        return f"Error Submitting Proposal in DAO: {truncated_message}"

    
def get_dao_proposals() -> str:
    """
    Get all DAO proposals.

    Returns:
        str: DAO proposals data
    
    """

    try:
        # Construct the query
        proposals = dh_graph.get_proposals_data()
        return proposals
    except Exception as e:
        return f"Error getting DAO proposals: {str(e)}"
    
def get_passed_dao_proposals() -> str:
    """
    Get all passed DAO proposals.

    Returns:
        str: DAO passed proposals data
    
    """

    try:
        # Construct the query
        proposals = dh_graph.get_passed_proposals_data()
        return proposals
    except Exception as e:
        return f"Error getting DAO proposals: {str(e)}"

def get_dao_proposal(proposal_id: int) -> str:
    """
    Get a specific DAO proposal.

    Args:
        proposal_id (str): The proposal ID.

    Returns:
        str: DAO proposal data
    """
    try:
        # Construct the query
        proposal = dh_graph.get_proposal_data(proposal_id)
        return proposal
    except Exception as e:
        return f"Error getting DAO proposal: {str(e)}"

def get_proposal_votes_data(proposal_id: int) -> str:
    """
    Get proposal votes data

    Args:
        proposal_id (int): The proposal ID

    Returns:
        str: Proposal votes data
    """
    try:
        # Construct the query
        votes = dh_graph.get_proposal_votes_data(proposal_id)
        return votes
    except Exception as e:
        return f"Error getting proposal votes data: {str(e)}"

def get_proposal_count() -> str:
    """
    Get the current proposal count

    Returns:
        str: the count
    """
    try:
        # Construct the query
        proposals = dh_graph.get_proposal_count()
        return proposals
    except Exception as e:
        return f"Error getting proposals count: {str(e)}"

# function to cast to farcaster
def cast_to_farcaster(content: str, channel_id: str = None) -> str:
    """
    Cast a message to Warpcast.

    Args:
        content (str): The content to cast
        channel_id (Optional[str]): The channel ID

    Returns:
        str: Status message about the cast
    """
    return farcaster_bot.post_cast(content, channel_id)

def check_cast_replies():
    """
    Check recent farcaster replies.

    Returns:
        str: Formatted string of recent replies by user
    """
    replies = farcaster_bot.get_replies()
    if not replies:
        return "No recent mentions found"

    return replies

def check_all_past_notifications():
    """
    this will return all notification from farcaster
    """
    return farcaster_bot.get_notifications()

def check_recent_cast_notifications():
    """
    Check for a recent farcaster notification that is not acted on and not older than a day.

    wrapcast url will be in this format: (https://warpcast.com/<author>/<hash>) 

    Returns:
        str: Formatted string of recent notifications
    """
    all_notifications = farcaster_bot.get_notifications()
    if isinstance(all_notifications, str):  # If an error occurred
        return all_notifications
    acted_notifications = memory_retention.get_acted_notifications()
    print("acted notes", acted_notifications)
    # If no acted notifications exist, create an empty set
    acted_hashes = {item.get('hash') for item in acted_notifications if 'hash' in item} if acted_notifications else set()
    print("acted ahshes", acted_hashes)
    # Filter out already acted notifications
    new_notifications = [n for n in all_notifications if n['hash'] not in acted_hashes and n['age_in_sec'] <= 86400]
    print("new notes", new_notifications)
    # Return the oldest notification based on 'age_in_sec', or None if no notifications exist
    if new_notifications:
        print("oldest, latest", min(new_notifications, key=lambda n: n['age_in_sec']))
        return min(new_notifications, key=lambda n: n['age_in_sec'])
    else:
        return None

def mark_notification_as_acted(notification_hash: str):

    """
    Mark notifications as acted.

    Returns:
        bool: Status message about the cast
    """
    return memory_retention.mark_notification_as_acted(notification_hash)

def cast_reply(content: str, parentHash: str, parent_fid: int):
    """
    Cast a message to Warpcast as a reply to another cast.
    uses parentHash to reply and parent author fid

    Args:
        content (str): The content to cast
        parentHash (str): The parent cast hash (for reply)

    Returns:
        str: Status message about the cast
    """
    response = farcaster_bot.post_cast(content, parent=parentHash, parent_fid=parent_fid)
    return response

def check_recent_agent_casts():
    """
    Get recent casts from the agent.

    Returns:
        str: Formatted string of recent casts
    """
    response = farcaster_bot.get_casts()
    return response

def check_recent_user_casts(fid: str):
    """
    Get recent casts from the agent.

    Returns:
        str: Formatted string of recent casts
    """
    response = farcaster_bot.get_casts(fid)
    return response

def check_user_profile(fid: str):
    """
    Get user profile.

    Returns:
        str: Formatted string of user profile (exclude @ sign)
    """
    response = farcaster_bot.get_user_by_username(fid)
    return response

# Functions to interact with memory retention
# def store_memory(self, memory: Dict) -> str:
def commit_memory(memory:str):
    """
    Store a memory
    """
    return memory_retention.store_memory({"type": "memory", "content": memory})
def get_all_memories():
    """
    Get all memories
    """
    return memory_retention.get_all_memories()
def get_memories(query):
    """
    Get memories
    """
    return memory_retention.get_memories(query)
def delete_memory(query):
    """
    Delete a memory
    """
    return memory_retention.delete_memory(query)
def get_memory_count():
    """
    Get the count of memories
    """
    return memory_retention.get_memory_count()
def get_knowledge_by_keywords(keywords: str) -> str:
    """
    get knowledge content from keywords
    
    Args:
        keywords (str): A list of keywords to search for in the knowledge base.

    Returns:
        str: a concatenated list of content
    """
    print(keywords.lower().strip().split())
    return memory_retention.query_by_keywords(keywords.lower().strip().split())
# Create the DAO Agent with all available functions

print("Creating Agent...")

def dao_agent(instructions: str ): 
    return Agent(
    name="Agent",
    instructions=instructions,
    model="o1-mini",
    functions=[
        get_balance,
        get_agent_address,
        generate_art,  # Uncomment this line if you have configured the OpenAI API
        cast_to_farcaster,
        check_cast_replies,
        check_recent_cast_notifications,
        check_all_past_notifications,
        mark_notification_as_acted,
        cast_reply,
        check_recent_agent_casts,
        check_recent_user_casts,
        check_user_profile,
        submit_dao_proposal_onchain,
        vote_on_dao_proposal,
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

def gm_agent(instructions: str, name: str = "GM" ): 
    print(instructions)
    return Agent(
    name=name,
    instructions=instructions,
    model="gpt-3.5-turbo",
    functions=[
        generate_art,  # Uncomment this line if you have configured the OpenAI API
        cast_to_farcaster,
        check_cast_replies,
        check_recent_cast_notifications,
        check_all_past_notifications,
        mark_notification_as_acted,
        cast_reply,
        check_recent_agent_casts,
        check_recent_user_casts,
        check_user_profile,
        get_dao_proposals,
        get_passed_dao_proposals,
        get_dao_proposal,
        get_proposal_count,
        get_proposal_votes_data,
        get_all_memories,
        get_knowledge_by_keywords

    ],
)

def player_agent(instructions: str, name: str = "Player" ): 
    return Agent(
    name=name,
    instructions=instructions,
    model="gpt-3.5-turbo",
    functions=[
        # get_balance,
        # get_agent_address,
        # generate_art,  # Uncomment this line if you have configured the OpenAI API
        # submit_dao_proposal_onchain,
        # vote_on_dao_proposal,
        # get_dao_proposal,
        # get_all_memories,
        # get_knowledge_by_keywords

    ],
)


# Initialize FarcvasterBot with your credentials
farcaster_bot = FarcasterBot()
# init the graph
# dh_graph = DaohausGraphData()
dh_graph = None
# init memory retention
memory_retention = MemoryRetention()
    
