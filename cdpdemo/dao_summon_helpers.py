import os
import random
import json
import time


from web3 import Web3
from web3.exceptions import ContractLogicError

from eth_abi import encode as encode_abi

from helpers import get_salt_nonce, is_eth_address, encode_values, encode_function, is_numberish, is_string

from dotenv import load_dotenv

load_dotenv()

with open("abis/l2_resolver_abi.json", "r") as abi_file:
    l2_resolver_abi = json.load(abi_file)

with open("abis/safe_factory_abi.json", "r") as abi_file:
    safe_factory_abi = json.load(abi_file)

with open("abis/basic_HOS_summoner.json", "r") as abi_file:
    basic_hos_summoner_abi = json.load(abi_file)

with open("abis/yeet24_hos_summoner_abi.json", "r") as abi_file:
    yeet24_hos_summoner_abi = json.load(abi_file)

with open("abis/baal_abi.json", "r") as abi_file:
    baal_abi = json.load(abi_file)

with open("abis/poster_abi.json", "r") as abi_file:
    poster_abi = json.load(abi_file)

with open("abis/safe_L2_abi.json", "r") as abi_file:
    safe_L2_abi = json.load(abi_file)


from constants_utils import (
    SUMMON_CONTRACTS,
    DEFAULT_CHAIN_ID,
    DEFAULT_DAO_PARAMS,
    DEFAULT_START_DATE_OFFSET,
    DEFAULT_DURATION,
    DEFAULT_MEME_YEETER_VALUES,
    MEME_SHAMAN_PERMISSIONS,
    YEET_SHAMAN_PERMISSIONS,
    DEFAULT_YEETER_VALUES,
    DEFAULT_SUMMON_VALUES,
)

# internal summon helper functions
    

def assemble_meme_summoner_args(dao_name, token_symbol, image, description, agent_wallet_address, chain_id = DEFAULT_CHAIN_ID):
    """
    Assembles the transaction arguments for meme summoner.

    Args:
        dao_name (str): The name of the DAO.
        token_symbol (str): The symbol of the token.
        image (str): The image URL. use generate_art() to generate an image.
        description (str): The description of the DAO.
        agent_wallet_address (str): The address of the agent's wallet.
        chain_id (str): The chain ID.
        

    Returns:
        list: Transaction arguments to be used in the contract call.
    """



    # get salt nonce
    salt_nonce = get_salt_nonce()

    member_address = agent_wallet_address


    price = DEFAULT_YEETER_VALUES["price"]
    multiplier = DEFAULT_YEETER_VALUES["multiplier"]
    start_date = int(time.time()) + DEFAULT_START_DATE_OFFSET
    

    calculated_dao_address = calculate_dao_address(salt_nonce)
    calculated_treasury_address = calculate_create_proxy_with_nonce_address(salt_nonce)

    mm_shaman_data = assemble_mm_shaman_params(start_date)
    mm_shaman_singleton = mm_shaman_data["shamanSingleton"]
    mm_shaman_permission = mm_shaman_data["shamanPermission"]
    mm_shaman_params = mm_shaman_data["shamanInitParams"]
    mm_salt_nonce = generate_shaman_salt_nonce(calculated_dao_address, 0, mm_shaman_params, salt_nonce, mm_shaman_permission, mm_shaman_singleton)

    calculated_shaman_address = calculate_meme_shaman_address(mm_salt_nonce)

    # Assemble the initialization parameters
    initialization_loot_token_params = assemble_token_params(
        dao_name + " LOOT",
        token_symbol + "-LOOT",
    )

    initialization_share_token_params = assemble_token_params(
        dao_name,
        token_symbol,
    )

    initialization_shaman_params = assemble_shaman_params(
        price,
        multiplier,
        member_address,
        calculated_shaman_address,
        start_date,
        chain_id,
    )

    post_initialization_actions = assemble_init_actions(
        image,
        description,
        calculated_dao_address,
        calculated_shaman_address,
        calculated_treasury_address,
        dao_name,
        member_address,
        chain_id,
        salt_nonce,
    )

    tx_args = [
        initialization_loot_token_params,
        initialization_share_token_params,
        initialization_shaman_params,
        post_initialization_actions,
        salt_nonce,
    ]


    return tx_args

def assemble_init_actions(image, description, calculated_dao_address, calculated_shaman_address, calculated_treasury_address, dao_name, member_address, chain_id, salt_nonce):
    poster = SUMMON_CONTRACTS["POSTER"].get(chain_id).lower()
    

    init_actions = [
        governance_config_tx(DEFAULT_SUMMON_VALUES),
        metadata_config_tx(image, description, calculated_dao_address, dao_name, member_address, poster),
        token_config_tx(),
        shaman_module_config_tx(calculated_shaman_address, calculated_treasury_address, salt_nonce, chain_id),
    ]

    return init_actions

def governance_config_tx(default_values):
    voting_period_in_seconds = default_values.get("votingPeriodInSeconds")
    grace_period_in_seconds = default_values.get("gracePeriodInSeconds")
    new_offering = default_values.get("newOffering")
    quorum = default_values.get("quorum")
    sponsor_threshold = default_values.get("sponsorThreshold")
    min_retention = default_values.get("minRetention")

    if not all(map(is_numberish, [voting_period_in_seconds, grace_period_in_seconds, new_offering, quorum, sponsor_threshold, min_retention])):
        raise ValueError("governanceConfigTX received arguments in the wrong shape or type")

    encoded_values = encode_abi(
        ["uint32", "uint32", "uint256", "uint256", "uint256", "uint256"],
        [
            voting_period_in_seconds,
            grace_period_in_seconds,
            new_offering,
            quorum,
            sponsor_threshold,
            min_retention,
        ]
    )
    encoded = encode_function(baal_abi, "setGovernanceConfig", [encoded_values])
    if is_string(encoded):
        return encoded
    raise ValueError("Encoding Error")

def token_config_tx():
    pause_vote_token = True
    pause_nv_token = True

    encoded = encode_function(baal_abi, "setAdminConfig", [pause_vote_token, pause_nv_token])
    if is_string(encoded):
        return encoded
    raise ValueError("Encoding Error")

def metadata_config_tx(image, description, calculated_dao_address, dao_name, member_address, poster_address):


    if not isinstance(dao_name, str):
        raise ValueError("metadataTX received arguments in the wrong shape or type")
    
    content = {
        "name": dao_name,
        "daoId": calculated_dao_address,
        "table": "daoProfile",
        "queryType": "list",
        "description": description or "",
        "avatarImg": image or "",
        "title": f"{dao_name} tst",
        "tags": ["YEET24", "AGENT"],
        "authorAddress": member_address,
    }

    metadata = encode_function(poster_abi, "post", [json.dumps(content), "daohaus.summoner.daoProfile"]) # TODO: set POSTER_TAGS
    encoded = encode_function(baal_abi, "executeAsBaal", [poster_address, 0, Web3.to_bytes(hexstr=metadata)])
    if is_string(encoded):
        return encoded
    raise ValueError("Encoding Error")

def shaman_module_config_tx(calculated_shaman_address, calculated_treasury_address, salt_nonce, chain_id):

    if not is_eth_address(calculated_shaman_address) or not is_eth_address(calculated_treasury_address):
        raise ValueError("shamanModuleConfigTX received arguments in the wrong shape or type")

    add_module = encode_function(safe_L2_abi, "enableModule", [calculated_shaman_address])
    # Convert `add_module` to bytes
    add_module_bytes = Web3.to_bytes(hexstr=add_module)

    exec_tx_from_module = encode_function(
        safe_L2_abi,
        "execTransactionFromModule",
        [
            calculated_treasury_address,
            0,
            add_module_bytes,
            0,
        ]
    )
    exec_tx_from_module_bytes = Web3.to_bytes(hexstr=exec_tx_from_module)
    
    encoded = encode_function(baal_abi, "executeAsBaal", [calculated_treasury_address, 0, exec_tx_from_module_bytes])
    if is_string(encoded):
        return encoded
    raise ValueError("Encoding Error")


def assemble_token_params(dao_name: str = DEFAULT_DAO_PARAMS.get("NAME"), token_symbol: str = DEFAULT_DAO_PARAMS.get("SYMBOL")):
    share_singleton = SUMMON_CONTRACTS["DH_TOKEN_SINGLETON"].get(DEFAULT_CHAIN_ID)
    
    if not share_singleton:
        print("ERROR: passed args")
        raise ValueError("assemble_share_token_params received arguments in the wrong shape or type")

    if not isinstance(dao_name, str) or not isinstance(token_symbol, str):
        raise ValueError("daoName and tokenSymbol must be strings")
    
    # Assuming you have a function to encode values similar to encodeValues in TypeScript
    share_params = encode_values(["string", "string"], [dao_name, token_symbol])
    
    return encode_values(["address", "bytes"], [share_singleton, share_params])

def assemble_mm_shaman_params(start_date: int = int(time.time()) + DEFAULT_START_DATE_OFFSET, chain_id = DEFAULT_CHAIN_ID):
    
    meme_yeeter_shaman_singleton = SUMMON_CONTRACTS["YEET24_SINGLETON"].get(chain_id)
    non_fungible_position_manager = SUMMON_CONTRACTS["UNISWAP_V3_NF_POSITION_MANAGER"].get(chain_id)
    weth9 = SUMMON_CONTRACTS["WETH"].get(chain_id)
    yeet24_claim_module = SUMMON_CONTRACTS["YEET24_CLAIM_MODULE"].get(chain_id)

    if not start_date:
        raise ValueError("startDate is required")


    end_date_time = start_date + DEFAULT_DURATION

    if (
        not meme_yeeter_shaman_singleton or
        not non_fungible_position_manager or
        not weth9 or
        not end_date_time or
        not yeet24_claim_module
    ):
        raise ValueError("assembleMemeYeeterShamanParams: config contracts not found")

    # Encoding the parameters
    meme_yeeter_shaman_params = encode_abi(
        ["address", "address", "address", "uint256", "uint256", "uint24"],
        [
            non_fungible_position_manager,
            weth9,
            yeet24_claim_module,
            DEFAULT_YEETER_VALUES["minThresholdGoal"],
            end_date_time,
            DEFAULT_MEME_YEETER_VALUES["poolFee"]
        ]
    )

    return {
        "shamanSingleton": meme_yeeter_shaman_singleton,
        "shamanPermission": MEME_SHAMAN_PERMISSIONS,
        "shamanInitParams": meme_yeeter_shaman_params
    }

def assemble_shaman_params(price, multiplier, member_address, calculated_shaman_address, start_date, chain_id = DEFAULT_CHAIN_ID):
    yeeter_shaman_singleton = SUMMON_CONTRACTS["YEETER_SINGLETON"].get(chain_id)


    mm_shaman_data = assemble_mm_shaman_params(start_date)
    mm_shaman_singleton = mm_shaman_data["shamanSingleton"]
    mm_shaman_permission = mm_shaman_data["shamanPermission"]
    mm_shaman_params = mm_shaman_data["shamanInitParams"]

    if not yeeter_shaman_singleton or not mm_shaman_singleton:
        raise ValueError("assembleShamanParams received arguments in the wrong shape or type")


    if not start_date:
        raise ValueError("startDate is required")

    end_date_time = int(start_date) + DEFAULT_DURATION

    types = [
            "uint256",
            "uint256",
            "bool",
            "uint256",
            "uint256",
            "uint256",
            "address[]",
            "uint256[]",
        ]
    

    # Prepare the fee recipients list
    fee_recipients = [
        *DEFAULT_YEETER_VALUES["feeRecipients"],
        calculated_shaman_address,
    ]

    fee_amounts = [
        *DEFAULT_YEETER_VALUES["feeAmounts"],
        DEFAULT_MEME_YEETER_VALUES["boostRewardFees"],
    ]

    # Conditionally add the agent to fee recipients if it exists
    if member_address:
        fee_recipients.append(member_address)
        fee_amounts.append(DEFAULT_YEETER_VALUES["feeAmounts"][0])

    values = [
        int(start_date),
        end_date_time,
        DEFAULT_YEETER_VALUES["isShares"],
        int(price),
        int(multiplier),
        DEFAULT_YEETER_VALUES["minThresholdGoal"],
        fee_recipients,
        fee_amounts,
    ]

    # Encoding the parameters for yeeterShaman
    yeeter_shaman_params = encode_abi(
        types,
        values
    )

    shaman_singletons = [mm_shaman_singleton, yeeter_shaman_singleton]
    shaman_permissions = [mm_shaman_permission, YEET_SHAMAN_PERMISSIONS]
    shaman_init_params = [mm_shaman_params, yeeter_shaman_params]

    return encode_abi(
        ["address[]", "uint256[]", "bytes[]"],
        [shaman_singletons, shaman_permissions, shaman_init_params]
    )

def generate_shaman_salt_nonce(baal_address, index, initialize_params, salt_nonce, shaman_permissions, shaman_template):
    encoded_values = encode_values(
        ["address", "uint256", "address", "uint256", "bytes32", "uint256"],
        [
            baal_address,
            int(index),
            shaman_template,
            int(shaman_permissions),
            Web3.solidity_keccak(['bytes'], [initialize_params]),
            int(salt_nonce)
        ]
    )
    return Web3.to_hex(Web3.solidity_keccak(['bytes'], [encoded_values]))

def calculate_meme_shaman_address(salt_nonce: int, chain_id = DEFAULT_CHAIN_ID):
    yeet24_singleton = SUMMON_CONTRACTS["YEET24_SINGLETON"].get(chain_id, "0x0000000000000000000000000000000000000000")
    yeet24_shaman_summoner = SUMMON_CONTRACTS["YEET24_SUMMONER"].get(chain_id, "0x0000000000000000000000000000000000000000")

    yeet24_singleton = Web3.to_checksum_address(yeet24_singleton)
    yeet24_shaman_summoner = Web3.to_checksum_address(yeet24_shaman_summoner)

    if not is_eth_address(yeet24_singleton) or not is_eth_address(yeet24_shaman_summoner):
        raise ValueError("Invalid address")
    
    w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC")))

    # Create contract instance
    hos = w3.eth.contract(address=yeet24_shaman_summoner, abi=yeet24_hos_summoner_abi)
    
    expected_shaman_address = "0x0000000000000000000000000000000000000000"

    try:
        # Simulate the contract call to predict the deterministic Shaman address
        
        expected_shaman_address = hos.functions.predictDeterministicShamanAddress(yeet24_singleton, int(salt_nonce, 16)).call()
    except ContractLogicError as e:
        print("expectedShamanAddress error", e)

    # print("expectedShamanAddress", expected_shaman_address)
    return Web3.to_checksum_address(expected_shaman_address)

def calculate_dao_address(salt_nonce: int, chain_id = DEFAULT_CHAIN_ID):
    yeet24_summoner = SUMMON_CONTRACTS["YEET24_SUMMONER"].get(chain_id, "0x0000000000000000000000000000000000000000")
    
    if not is_eth_address(yeet24_summoner):
        raise ValueError("Invalid address")
    
    # Create a Web3 instance (Assuming you have an endpoint URL)
    w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC")))

    # Create contract instance
    hos = w3.eth.contract(address=yeet24_summoner, abi=basic_hos_summoner_abi)
    
    try:
        # Simulate the contract call to calculate the DAO address
        expected_dao_address = hos.functions.calculateBaalAddress(int(salt_nonce)).call()
    except ContractLogicError as e:
        print("Error calculating DAO address", e)
        expected_dao_address = "0x0000000000000000000000000000000000000000"

    return Web3.to_checksum_address(expected_dao_address)

def calculate_create_proxy_with_nonce_address(salt_nonce, chain_id = DEFAULT_CHAIN_ID):
    gnosis_safe_proxy_factory_address = SUMMON_CONTRACTS["GNOSIS_SAFE_PROXY_FACTORY"].get(chain_id, "0x0000000000000000000000000000000000000000")
    master_copy_address = SUMMON_CONTRACTS["GNOSIS_SAFE_MASTER_COPY"].get(chain_id)
    initializer = "0x"

    if not is_eth_address(gnosis_safe_proxy_factory_address) or not is_eth_address(master_copy_address):
        raise ValueError("Invalid address")

    # Simulating the process to estimate gas and determine expected address
    expected_safe_address = "0x0000000000000000000000000000000000000000"

    w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC")))

    # Create contract instance
    gnosis_safe_proxy_factory = w3.eth.contract(
        address=gnosis_safe_proxy_factory_address,
        abi=safe_factory_abi
    )

    try:
        # Simulate the contract call to estimate the address
        expected_safe_address = gnosis_safe_proxy_factory.functions.calculateCreateProxyWithNonceAddress(
            master_copy_address, initializer, int(salt_nonce)
        ).call()
    except ContractLogicError as e:
        # print("ContractLogicError", e)
        expected_safe_address = get_safe_address_from_revert_message(e)

    return expected_safe_address

    
def get_safe_address_from_revert_message(e):
    try:
        # Assuming the error message contains the reverted data with the address
        if isinstance(e.args, tuple) and len(e.args) > 1:
            data = e.args[1]  # Extract the data part of the error tuple
            if isinstance(data, str) and len(data) >= 178:
                return Web3.to_checksum_address(data[138:178])
    except Exception:
        messages = str(e).split(" ")
        for message in messages:
            if message.startswith("0x") and len(message) in [42, 44]:
                return message.replace(",", "")
    return "0x0000000000000000000000000000000000000000"
