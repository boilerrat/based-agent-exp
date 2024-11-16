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
    calculated_shaman_address = calculate_meme_shaman_address(salt_nonce)
    start_date = int(time.time()) + DEFAULT_START_DATE_OFFSET
    

    calculated_dao_address = calculate_dao_address(salt_nonce)
    calculated_treasury_address = calculate_create_proxy_with_nonce_address(salt_nonce)

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

    print(
        ">>>>> summon args",
        initialization_loot_token_params,
        initialization_share_token_params,
        initialization_shaman_params,
        post_initialization_actions,
    )

    tx_args = [
        initialization_loot_token_params,
        initialization_share_token_params,
        initialization_shaman_params,
        post_initialization_actions,
        salt_nonce,
    ]

    print("txArgs", tx_args)

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

    print("defaultValues", default_values)

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
    print("encodedValues", encoded_values)
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
    
    print("POSTER", poster_address)

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
    print("metadata", metadata)
    encoded = encode_function(baal_abi, "executeAsBaal", [poster_address, 0, Web3.to_bytes(hexstr=metadata)])
    if is_string(encoded):
        return encoded
    raise ValueError("Encoding Error")

def shaman_module_config_tx(calculated_shaman_address, calculated_treasury_address, salt_nonce, chain_id):

    print("calculatedShamanAddress", calculated_shaman_address, calculated_treasury_address)

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
    print("execTxFromModule", exec_tx_from_module)
    
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

def assemble_meme_yeeter_shaman_params(start_date: int = int(time.time()) + DEFAULT_START_DATE_OFFSET, chain_id = DEFAULT_CHAIN_ID):
    
    meme_yeeter_shaman_singleton = SUMMON_CONTRACTS["YEET24_SINGLETON"].get(chain_id)
    non_fungible_position_manager = SUMMON_CONTRACTS["UNISWAP_V3_NF_POSITION_MANAGER"].get(chain_id)
    weth9 = SUMMON_CONTRACTS["WETH"].get(chain_id)
    yeet24_claim_module = SUMMON_CONTRACTS["YEET24_CLAIM_MODULE"].get(chain_id)

    print("assemble_meme_yeeter_shaman_params >>>>>>????", meme_yeeter_shaman_singleton)
    print("assemble_meme_yeeter_shaman_params >>>>>>????", non_fungible_position_manager, weth9)

    if not start_date:
        raise ValueError("startDate is required")
    
    print("assemble_meme_yeeter_shaman_params start date >>>>>>????", start_date)

    end_date_time = start_date + DEFAULT_DURATION

    print("assemble_meme_yeeter_shaman_params >>>>>>????", start_date, end_date_time)


    print("assemble_meme_yeeter_shaman_params >>>>>>????", start_date, end_date_time)

    if (
        not meme_yeeter_shaman_singleton or
        not non_fungible_position_manager or
        not weth9 or
        not end_date_time or
        not yeet24_claim_module
    ):
        print(
            "assembleMemeYeeterShamanParams ERROR:",
            meme_yeeter_shaman_singleton,
            non_fungible_position_manager,
            weth9
        )
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

    print("??????????", price, member_address, yeeter_shaman_singleton, multiplier)

    meme_yeeter_shaman_data = assemble_meme_yeeter_shaman_params()
    meme_yeeter_shaman_singleton = meme_yeeter_shaman_data["shamanSingleton"]
    meme_yeeter_shaman_permission = meme_yeeter_shaman_data["shamanPermission"]
    meme_yeeter_shaman_params = meme_yeeter_shaman_data["shamanInitParams"]
    print("memeYeeterShamanData", meme_yeeter_shaman_data)

    if not yeeter_shaman_singleton or not meme_yeeter_shaman_singleton:
        raise ValueError("assembleShamanParams received arguments in the wrong shape or type")


    if not start_date:
        raise ValueError("startDate is required")

    end_date_time = int(start_date) + DEFAULT_DURATION

    # Encoding the parameters for yeeterShaman
    yeeter_shaman_params = encode_abi(
        [
            "uint256",
            "uint256",
            "bool",
            "uint256",
            "uint256",
            "uint256",
            "address[]",
            "uint256[]",
        ],
        [
            int(start_date),
            end_date_time,
            DEFAULT_YEETER_VALUES["isShares"],
            int(price),
            int(multiplier),
            DEFAULT_YEETER_VALUES["minThresholdGoal"],
            [
                *DEFAULT_YEETER_VALUES["feeRecipients"],
                calculated_shaman_address,
            ],
            [
                *DEFAULT_YEETER_VALUES["feeAmounts"],
                DEFAULT_MEME_YEETER_VALUES["boostRewardFees"],
            ],
        ]
    )

    shaman_singletons = [meme_yeeter_shaman_singleton, yeeter_shaman_singleton]
    shaman_permissions = [meme_yeeter_shaman_permission, MEME_SHAMAN_PERMISSIONS]
    shaman_init_params = [meme_yeeter_shaman_params, yeeter_shaman_params]

    print("shaman vals", [shaman_singletons, shaman_permissions, shaman_init_params])

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
            Web3.solidityKeccak(['bytes'], [initialize_params]),
            int(salt_nonce)
        ]
    )
    return Web3.toHex(Web3.solidityKeccak(['bytes'], [encoded_values]))

def calculate_meme_shaman_address(salt_nonce: int, chain_id = DEFAULT_CHAIN_ID):
    yeet24_singleton = SUMMON_CONTRACTS["YEET24_SINGLETON"].get(chain_id, "0x0000000000000000000000000000000000000000")
    yeet24_shaman_summoner = SUMMON_CONTRACTS["YEET24_SUMMONER"].get(chain_id, "0x0000000000000000000000000000000000000000")
    print("yeet24 Shaman", yeet24_singleton, yeet24_shaman_summoner, chain_id)

    yeet24_singleton = Web3.to_checksum_address(yeet24_singleton)
    yeet24_shaman_summoner = Web3.to_checksum_address(yeet24_shaman_summoner)

    if not is_eth_address(yeet24_singleton) or not is_eth_address(yeet24_shaman_summoner):
        raise ValueError("Invalid address")
    
    w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC")))

    # Create contract instance
    hos = w3.eth.contract(address=yeet24_shaman_summoner, abi=yeet24_hos_summoner_abi)
    
    expected_shaman_address = "0x0000000000000000000000000000000000000000"

    print("saltNonce calculateMemeShamanAddress", salt_nonce)
    print("yeet24Singleton", yeet24_singleton)

    try:
        # Simulate the contract call to predict the deterministic Shaman address
        print("hos", hos)
        print("hos.functions", hos.functions)
        print("hos.functions.predictDeterministicShamanAddress", hos.functions.predictDeterministicShamanAddress)
        print("yeet24_singleton, salt_nonce", yeet24_singleton, salt_nonce)
        expected_shaman_address = hos.functions.predictDeterministicShamanAddress(yeet24_singleton, int(salt_nonce)).call()
        print("***>>>>>>>>>>>>>> expectedShamanAddress", expected_shaman_address)
    except ContractLogicError as e:
        print("expectedShamanAddress error", e)

    return Web3.to_checksum_address(expected_shaman_address)

def calculate_dao_address(salt_nonce: int, chain_id = DEFAULT_CHAIN_ID):
    yeet24_summoner = SUMMON_CONTRACTS["YEET24_SUMMONER"].get(chain_id, "0x0000000000000000000000000000000000000000")
    
    print("yeet24Summoner", yeet24_summoner, chain_id)

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

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>expectedDAOAddress", expected_dao_address, Web3.to_checksum_address(expected_dao_address))

    return Web3.to_checksum_address(expected_dao_address)

def calculate_create_proxy_with_nonce_address(salt_nonce, chain_id = DEFAULT_CHAIN_ID):
    gnosis_safe_proxy_factory_address = SUMMON_CONTRACTS["GNOSIS_SAFE_PROXY_FACTORY"].get(chain_id, "0x0000000000000000000000000000000000000000")
    master_copy_address = SUMMON_CONTRACTS["GNOSIS_SAFE_MASTER_COPY"].get(chain_id)
    initializer = "0x"

    print("gnosisSafeProxyFactoryAddress", gnosis_safe_proxy_factory_address, master_copy_address, chain_id)
    print("saltNonce calculateCreateProxyWithNonceAddress", salt_nonce)

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
        print("ContractLogicError", e)
        expected_safe_address = get_safe_address_from_revert_message(e)

    return expected_safe_address

    
def get_safe_address_from_revert_message(e):
    try:
        # Assuming the error message contains the reverted data with the address
        if isinstance(e.args, tuple) and len(e.args) > 1:
            data = e.args[1]  # Extract the data part of the error tuple
            print("data", data)
            if isinstance(data, str) and len(data) >= 178:
                return Web3.to_checksum_address(data[138:178])
    except Exception:
        messages = str(e).split(" ")
        for message in messages:
            if message.startswith("0x") and len(message) in [42, 44]:
                return message.replace(",", "")
    return "0x0000000000000000000000000000000000000000"




# Main entry point WIP
# would go in agents

# def summon_dao(dao_name, token_symbol, image, description, agent_wallet_address, chain_id=DEFAULT_CHAIN_ID):
#     """
#     Summon a DAO.

#     Args:
#         dao_name (str): Name of the DAO.
#         token_symbol (str): Token symbol for the DAO.
#         image (str): Image URL or path for the DAO.
#         description (str): Description of the DAO.
#         agent_wallet_address (str): Address of the agent wallet.
#         chain_id (int): Blockchain network ID.

#     Returns:
#         str: Success or error message.
#     """
#     try:
#         # Assemble arguments for summoning the DAO
#         summon_args = assemble_meme_summoner_args(dao_name, token_symbol, image, description, agent_wallet_address, chain_id)
#         print("***************", summon_args)

#         # Convert summon_args[3] (bytes[]) and summon_args[4] (uint256)
#         # summon_args[3] = [
#         #     action.encode('utf-8') if isinstance(action, str) else action for action in summon_args[3]
#         # ]
#         summon_args[4] = int(summon_args[4])

#         print("Processed arguments:", summon_args)

#         # Export wallet data (contains seed and wallet ID)
#         wallet_data = agent_wallet.export_data()
#         print("Wallet data:", wallet_data)


#         w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC")))
#         w3.eth.handle_revert = True

#         if not w3.is_connected():
#             raise Exception("Web3 is not connected. Check your provider URL.")

#         # Encode the function call data
#         current_gas_price = w3.eth.gas_price
#         print("Current gas price:", current_gas_price, w3.from_wei(current_gas_price, 'gwei')) # <1 gwei
#         contract = w3.eth.contract(
#             address=SUMMON_CONTRACTS['YEET24_SUMMONER'][DEFAULT_CHAIN_ID],
#             abi=yeet24_hos_summoner_abi,
#         )
#         tx_data = contract.functions.summonBaalFromReferrer(
#             *summon_args  # Unpack arguments
#         ).build_transaction({
#             'chainId': DEFAULT_CHAIN_ID,
#             # 'gas': 3000000000000000,  # Adjust as needed
#             'gasPrice': "1", # in gwei
#             'nonce': str(w3.eth.get_transaction_count(agent_wallet_address)),
#         })


#         current_gas_price = w3.eth.gas_price
#         estimated_gas = w3.eth.estimate_gas(tx_data)
#         print(f"Estimated gas: {estimated_gas}")
#         tx_data['gas'] = str(estimated_gas) 
#         # print("Transaction data:", tx_data)

#         # Sign the transaction

#         tx_data['chainId'] = str(int(tx_data['chainId'], 16)) 


#         if isinstance(tx_data['data'], bytes):
#             tx_data['data'] = Web3.to_hex(tx_data['data']) 

#         signed_tx = agent_wallet.sign_payload(tx_data)
#         print("Signed transaction.", signed_tx)

#         # Broadcast the transaction
#         tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

#         # Wait for transaction receipt
#         receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
#         if receipt.status == 1:
#             return f"Successfully summoned DAO. Transaction hash: {tx_hash.hex()}"
#         else:
#             return "Error summoning DAO: Transaction failed"

#     except Exception as e:
#         return f"Error summoning DAO: {str(e)}"
    
# def summon_dao_neg(dao_name, token_symbol, image, description, agent_wallet_address, chain_id=DEFAULT_CHAIN_ID):
#     """
#     Summon a DAO.

#     Args:
#         dao_name (str): Name of the DAO.
#         token_symbol (str): Token symbol for the DAO.
#         image (str): Image URL or path for the DAO.
#         description (str): Description of the DAO.
#         agent_wallet_address (str): Address of the agent wallet.
#         chain_id (int): Blockchain network ID.

#     Returns:
#         str: Success or error message.
#     """
#     try:
#         # Assemble arguments for summoning the DAO
#         summon_args = assemble_meme_summoner_args(dao_name, token_symbol, image, description, agent_wallet_address, chain_id)
#         # print("***************", summon_args)

        

#         initialization_loot_token_params = summon_args[0]
#         initialization_share_token_params = summon_args[1]
#         initialization_shaman_params = summon_args[2]
#         # TODO: this seems to fail because we can not json serialize bytes[] and still work with the contract abi
#         # post_initialization_actions = [
#         #     action.encode('utf-8') if isinstance(action, str) else action for action in list(summon_args[3])
#         # ]
#         # post_initialization_actions = [
#         #     action.encode('utf-8') if isinstance(action, str) else action for action in summon_args[3]
#         # ]
#         post_initialization_actions = summon_args[3]
#         salt_nonce = int(summon_args[4])

#         print("Type of post_initialization_actions:", type(post_initialization_actions))
#         print("Items in post_initialization_actions:", [type(a) for a in post_initialization_actions])


#         print("Processed arguments.")
#         print("Type of initialization_loot_token_params:", type(initialization_loot_token_params))
#         print("Type of initialization_share_token_params:", type(initialization_share_token_params))
#         print("Type of initialization_shaman_params:", type(initialization_shaman_params))
#         print("Type of post_initialization_actions:", type(post_initialization_actions), "Items:", [type(a) for a in post_initialization_actions])
#         print("Type of saltNonce:", type(salt_nonce))

#         # Create a dictionary with the correct structure
#         summon_args_dict = {
#             "initializationLootTokenParams": initialization_loot_token_params,
#             "initializationShareTokenParams": initialization_share_token_params,
#             "initializationShamanParams": initialization_shaman_params,
#             "postInitializationActions": post_initialization_actions,
#             "saltNonce": salt_nonce,
#         }

#         print("Final summon_args_dict:", summon_args_dict)
#         for key, value in summon_args_dict.items():
#             print(f"{key}: {value} (type: {type(value)})")

#         # print("Processed summon_args_dict:", summon_args_dict)

#         print("Summoning DAO...", SUMMON_CONTRACTS['YEET24_SUMMONER'][DEFAULT_CHAIN_ID])

#         # Invoke the contract
#         # TODO: this seems to have issues with serealizing a more complex abi data for cdp
#         # like the bytes[] that is needed with post_initialization_actions
#         # a contract wrapper/factory that simplifies the format might be able to be used
#         summon_invocation = agent_wallet.invoke_contract(
#             contract_address=SUMMON_CONTRACTS['YEET24_SUMMONER'][DEFAULT_CHAIN_ID],
#             method="summonBaalFromReferrer",
#             args=summon_args_dict,
#             abi=yeet24_hos_summoner_abi,
#             amount=None,
#             asset_id="eth",
#         )
#         summon_invocation.wait()

#         return "Successfully summoned DAO"

#     except Exception as e:
#         return f"Error summoning DAO: {str(e)}"