import os
import json

from decimal import Decimal
from typing import Union

from cdp.errors import UnsupportedAssetError
from cdp import Cdp, Wallet
from openai import OpenAI
from swarm import Agent
from web3 import Web3
from web3.exceptions import ContractLogicError
from farcaster_utils import FarcasterBot
from prompt_helpers import instructions

# Load the ENS registrar and resolver ABIs
with open("abis/registrar_abi.json", "r") as abi_file:
    registrar_abi = json.load(abi_file)

with open("abis/baal_abi.json", "r") as abi_file:
    baal_abi = json.load(abi_file)

with open("abis/gnosis_multisend_abi.json", "r") as abi_file:
    gnosis_multisend_abi = json.load(abi_file)

from helpers import get_salt_nonce, is_eth_address, encode_values, encode_function



from constants_utils import (
    BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_MAINNET,
    BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_TESTNET,
    L2_RESOLVER_ADDRESS_MAINNET,
    L2_RESOLVER_ADDRESS_TESTNET,
)


from dotenv import dotenv_values

config = dotenv_values(".env")

# Get configuration from environment variables
API_KEY_NAME = os.getenv("CDP_API_KEY_NAME")
PRIVATE_KEY = os.getenv("CDP_PRIVATE_KEY", "").replace('\\n', '\n')

# Configure CDP with environment variables
Cdp.configure(API_KEY_NAME, PRIVATE_KEY)

# Create a new wallet on the Base Sepolia testnet
# You could make this a function for the agent to create a wallet on any network
# If you want to use Base Mainnet, change Wallet.create() to Wallet.create(network_id="base-mainnet")
# see https://docs.cdp.coinbase.com/mpc-wallet/docs/wallets for more information
# agent_wallet = Wallet.create(network_id="base-mainnet")

# NOTE: the wallet is not currently persisted, meaning that it will be deleted after the agent is stopped. To persist the wallet, see https://docs.cdp.coinbase.com/mpc-wallet/docs/wallets#developer-managed-wallets
# Here's an example of how to persist the wallet:
# WARNING: This is for development only - implement secure storage in production!

# Export wallet data (contains seed and wallet ID)
# wallet_data = agent_wallet.export_data()
# wallet_dict = wallet_data.to_dict()

# Example of saving to encrypted local file
# file_path = "base_wallet_seed.json"
# agent_wallet.save_seed(file_path, encrypt=True)
# print(f"Seed for wallet {agent_wallet.id} saved to {file_path}")

# Example of loading a saved wallet:
# 1. Fetch the wallet by ID
# agent_wallet = Wallet.fetch("278ecde2-f10c-42db-9fda-fb4db022fcca") # testnet
agent_wallet = Wallet.fetch("6dafdeee-a356-408f-9d27-e55abbb1ea64") # mainnet
# 2. Load the saved seed
agent_wallet.load_seed("base_wallet_seed.json")

# Example of importing previously exported wallet data:
# imported_wallet = Wallet.import_data(wallet_dict)

# Request funds from the faucet (only works on testnet)
# faucet = agent_wallet.faucet()
# print(f"Faucet transaction: {faucet}")
# print(f"Agent wallet address: {agent_wallet.default_address.address_id}")





# Function to create a new ERC-20 token
def create_token(name, symbol, initial_supply):
    """
    Create a new ERC-20 token.
    
    Args:
        name (str): The name of the token
        symbol (str): The symbol of the token
        initial_supply (int): The initial supply of tokens
    
    Returns:
        str: A message confirming the token creation with details
    """
    deployed_contract = agent_wallet.deploy_token(name, symbol, initial_supply)
    deployed_contract.wait()
    return f"Token {name} ({symbol}) created with initial supply of {initial_supply} and contract address {deployed_contract.contract_address}"


# Function to transfer assets
def transfer_asset(amount, asset_id, destination_address):
    """
    Transfer an asset to a specific address.
    
    Args:
        amount (Union[int, float, Decimal]): Amount to transfer
        asset_id (str): Asset identifier ("eth", "usdc") or contract address of an ERC-20 token
        destination_address (str): Recipient's address
    
    Returns:
        str: A message confirming the transfer or describing an error
    """
    try:
        # Check if we're on Base Mainnet and the asset is USDC for gasless transfer
        is_mainnet = agent_wallet.network_id == "base-mainnet"
        is_usdc = asset_id.lower() == "usdc"
        gasless = is_mainnet and is_usdc

        # For ETH and USDC, we can transfer directly without checking balance
        if asset_id.lower() in ["eth", "usdc"]:
            transfer = agent_wallet.transfer(amount,
                                             asset_id,
                                             destination_address,
                                             gasless=gasless)
            transfer.wait()
            gasless_msg = " (gasless)" if gasless else ""
            return f"Transferred {amount} {asset_id}{gasless_msg} to {destination_address}"

        # For other assets, check balance first
        try:
            balance = agent_wallet.balance(asset_id)
        except UnsupportedAssetError:
            return f"Error: The asset {asset_id} is not supported on this network. It may have been recently deployed. Please try again in about 30 minutes."

        if balance < amount:
            return f"Insufficient balance. You have {balance} {asset_id}, but tried to transfer {amount}."

        transfer = agent_wallet.transfer(amount, asset_id, destination_address)
        transfer.wait()
        return f"Transferred {amount} {asset_id} to {destination_address}"
    except Exception as e:
        return f"Error transferring asset: {str(e)}. If this is a custom token, it may have been recently deployed. Please try again in about 30 minutes, as it needs to be indexed by CDP first."


# Function to get the balance of a specific asset
def get_balance(asset_id):
    """
    Get the balance of a specific asset in the agent's wallet.
    
    Args:
        asset_id (str): Asset identifier ("eth", "usdc") or contract address of an ERC-20 token
    
    Returns:
        str: A message showing the current balance of the specified asset
    """
    balance = agent_wallet.balance(asset_id)
    return f"Current balance of {asset_id}: {balance}"

# Function to get the address of the current agent
def get_agent_address():
    """
    Get the address of the current agent's wallet.

    Returns:
        str: The address of the agent
    """
    address = agent_wallet.default_address.address_id
    return f"Current address: {address}"

# Function to request ETH from the faucet (testnet only)
def request_eth_from_faucet():
    """
    Request ETH from the Base Sepolia testnet faucet.
    
    Returns:
        str: Status message about the faucet request
    """
    if agent_wallet.network_id == "base-mainnet":
        return "Error: The faucet is only available on Base Sepolia testnet."

    faucet_tx = agent_wallet.faucet()
    return f"Requested ETH from faucet. Transaction: {faucet_tx}"


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
        return f"Generated artwork available at: {image_url}"

    except Exception as e:
        return f"Error generating artwork: {str(e)}"


# Function to deploy an ERC-721 NFT contract
def deploy_nft(name, symbol, base_uri):
    """
    Deploy an ERC-721 NFT contract.
    
    Args:
        name (str): Name of the NFT collection
        symbol (str): Symbol of the NFT collection
        base_uri (str): Base URI for token metadata
    
    Returns:
        str: Status message about the NFT deployment, including the contract address
    """
    try:
        deployed_nft = agent_wallet.deploy_nft(name, symbol, base_uri)
        deployed_nft.wait()
        contract_address = deployed_nft.contract_address

        return f"Successfully deployed NFT contract '{name}' ({symbol}) at address {contract_address} with base URI: {base_uri}"

    except Exception as e:
        return f"Error deploying NFT contract: {str(e)}"


# Function to mint an NFT
def mint_nft(contract_address, mint_to):
    """
    Mint an NFT to a specified address.
    
    Args:
        contract_address (str): Address of the NFT contract
        mint_to (str): Address to mint NFT to
    
    Returns:
        str: Status message about the NFT minting
    """
    try:
        mint_args = {"to": mint_to, "quantity": "1"}

        mint_invocation = agent_wallet.invoke_contract(
            contract_address=contract_address, method="mint", args=mint_args)
        mint_invocation.wait()

        return f"Successfully minted NFT to {mint_to}"

    except Exception as e:
        return f"Error minting NFT: {str(e)}"


# Function to swap assets (only works on Base Mainnet)
def swap_assets(amount: Union[int, float, Decimal], from_asset_id: str,
                to_asset_id: str):
    """
    Swap one asset for another using the trade function.
    This function only works on Base Mainnet.

    Args:
        amount (Union[int, float, Decimal]): Amount of the source asset to swap
        from_asset_id (str): Source asset identifier
        to_asset_id (str): Destination asset identifier

    Returns:
        str: Status message about the swap
    """
    if agent_wallet.network_id != "base-mainnet":
        return "Error: Asset swaps are only available on Base Mainnet. Current network is not Base Mainnet."

    try:
        trade = agent_wallet.trade(amount, from_asset_id, to_asset_id)
        trade.wait()
        return f"Successfully swapped {amount} {from_asset_id} for {to_asset_id}"
    except Exception as e:
        return f"Error swapping assets: {str(e)}"



# Function to create registration arguments for Basenames
def create_register_contract_method_args(base_name: str, address_id: str,
                                         is_mainnet: bool) -> dict:
    """
    Create registration arguments for Basenames.
    
    Args:
        base_name (str): The Basename (e.g., "example.base.eth" or "example.basetest.eth")
        address_id (str): The Ethereum address
        is_mainnet (bool): True if on mainnet, False if on testnet
    
    Returns:
        dict: Formatted arguments for the register contract method
    """
    w3 = Web3()

    resolver_contract = w3.eth.contract(abi=l2_resolver_abi)

    name_hash = w3.ens.namehash(base_name)

    address_data = resolver_contract.encode_abi("setAddr",
                                                args=[name_hash, address_id])

    name_data = resolver_contract.encode_abi("setName",
                                             args=[name_hash, base_name])

    register_args = {
        "request": [
            base_name.replace(".base.eth" if is_mainnet else ".basetest.eth",
                              ""),
            address_id,
            "31557600",  # 1 year in seconds
            L2_RESOLVER_ADDRESS_MAINNET
            if is_mainnet else L2_RESOLVER_ADDRESS_TESTNET,
            [address_data, name_data],
            True
        ]
    }

    return register_args


# Function to register a basename
def register_basename(basename: str, amount: float = 0.002):
    """
    Register a basename for the agent's wallet.
    
    Args:
        basename (str): The basename to register (e.g. "myname.base.eth" or "myname.basetest.eth")
        amount (float): Amount of ETH to pay for registration (default 0.002)
    
    Returns:
        str: Status message about the basename registration
    """
    address_id = agent_wallet.default_address.address_id
    is_mainnet = agent_wallet.network_id == "base-mainnet"

    suffix = ".base.eth" if is_mainnet else ".basetest.eth"
    if not basename.endswith(suffix):
        basename += suffix

    register_args = create_register_contract_method_args(
        basename, address_id, is_mainnet)

    try:
        contract_address = (BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_MAINNET
                            if is_mainnet else
                            BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_TESTNET)

        invocation = agent_wallet.invoke_contract(
            contract_address=contract_address,
            method="register",
            args=register_args,
            abi=registrar_abi,
            amount=amount,
            asset_id="eth",
        )
        invocation.wait()
        return f"Successfully registered basename {basename} for address {address_id}"
    except ContractLogicError as e:
        return f"Error registering basename: {str(e)}"
    except Exception as e:
        return f"Unexpected error registering basename: {str(e)}"

# functions to interact with daos
def vote_on_dao_proposal(dao_address: str, proposal_id: str, vote: bool) -> str:
    """
    Summon a DAO.

    Args:
        dao_address (str): The DAO address.
        proposal_id (int): The proposal ID.
        vote (bool): The vote.

    Returns:
        str: Success or error message.
    """
    if not isinstance(dao_address, str) or not isinstance(proposal_id, str) or not isinstance(vote, bool):
        return "Invalid input types"

    try:

        args_dict = {
            "id": proposal_id,
            "approved": vote,
        }

        invocation = agent_wallet.invoke_contract(
            contract_address=dao_address,
            method="submitVote",
            args=args_dict,
            abi=baal_abi,
            # amount=amount,
            # asset_id="eth",
        )
        invocation.wait()
        return f"Successfully voted on proposal id {proposal_id} for dao address {dao_address}"


    except Exception as e:
        return f"Error Voting in DAO: {str(e)}"
    
# function to submit a proposal
def submit_dao_proposal(dao_address: str, proposal_title: str, proposal_description: str, proposal_link: str) -> str:
    """
    Summon a DAO.

    Args:
        dao_address (str): The DAO address.
        proposal_title (str): The proposal title.
        proposal_description (str): The proposal description.
        proposal_link (str): The proposal link.

    Returns:
        str: Success or error message.
    """
    if not isinstance(dao_address, str) or not isinstance(proposal_title, str):
        return "Invalid input types"
    
    proposal_details = {
    "title": proposal_title,
    "description": proposal_description,
    "contentURI": proposal_link,
    "contentURIType": {"type": "static", "value": "url"},
    "proposalType": {"type": "static", "value": "Signal"},  
    }

    proposal = json.dumps(proposal_details)


    try:

        args_dict = {
            "proposalData": "0x",
            "expiration": "0",
            "baalGas": "0",
            "details": proposal
        }

        invocation = agent_wallet.invoke_contract(
            contract_address=dao_address,
            method="submitProposal",
            args=args_dict,
            abi=baal_abi,
            # amount=amount,
            # asset_id="eth",
        )
        invocation.wait()
        return f"Successfully submitted proposal for dao address {dao_address}"


    except Exception as e:
        return f"Error Submitting Proposal in DAO: {str(e)}"
    


# function to cast to warpcast
def cast_to_warpcast(content: str):
    """
    Cast a message to Warpcast.

    Args:
        content (str): The content to cast

    Returns:
        str: Status message about the cast
    """
    return farcaster_bot.post_cast(content)

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

def check_cast_notifications():
    """
    Check recent farcaster notifications.

    wrapcast url will be in this format **Hash**: (https://warpcast.com/<author>/<hash>) 

    Returns:
        str: Formatted string of recent notifications
    """
    response = farcaster_bot.get_notifications()

    return response

def cast_reply(content: str, parentHash: str):
    """
    Cast a message to Warpcast as a reply to another cast.
    uses parentHash to reply 

    Args:
        content (str): The content to cast
        parentHash (str): The parent cast hash (for reply)

    Returns:
        str: Status message about the cast
    """
    response = farcaster_bot.post_cast(content, parent=parentHash)
    return response



# Create the Based Agent with all available functions
based_agent = Agent(
    name="Based Agent",
    instructions=instructions,
    functions=[
        create_token,
        transfer_asset,
        get_balance,
        get_agent_address,
        request_eth_from_faucet,
        generate_art,  # Uncomment this line if you have configured the OpenAI API
        deploy_nft,
        mint_nft,
        swap_assets,
        register_basename,
        cast_to_warpcast,
        check_cast_replies,
        check_cast_notifications,
        cast_reply,
        submit_dao_proposal,
        vote_on_dao_proposal,
    ],
)

# add the following import to the top of the file, add the code below it, and add the new functions to the based_agent.functions list

# from farcaster_utils import FarcasterBot

# # Initialize FarcvasterBot with your credentials
farcaster_bot = FarcasterBot()
    

# To add a new function:
# 1. Define your function above (follow the existing pattern)
# 2. Add appropriate error handling
# 3. Add the function to the based_agent's functions list
# 4. If your function requires new imports or global variables, add them at the top of the file
# 5. Test your new function thoroughly before deploying

# Example of adding a new function:
# def my_new_function(param1, param2):
#     """
#     Description of what this function does.
#
#     Args:
#         param1 (type): Description of param1
#         param2 (type): Description of param2
#
#     Returns:
#         type: Description of what is returned
#     """
#     try:
#         # Your function logic here
#         result = do_something(param1, param2)
#         return f"Operation successful: {result}"
#     except Exception as e:
#         return f"Error in my_new_function: {str(e)}"

# Then add to based_agent.functions:
# based_agent = Agent(
#     ...
#     functions=[
#         ...
#         my_new_function,
#     ],
# )
