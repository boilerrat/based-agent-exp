import random

from eth_abi import encode as encode_abi
from eth_utils import function_signature_to_4byte_selector

from web3 import Web3
from web3.exceptions import ContractLogicError

def get_salt_nonce(length=32):
    possible = "0123456789"
    return ''.join(random.choice(possible) for _ in range(length))

def is_eth_address(address):
    return Web3.is_address(address)

def encode_values(types, values):
    from eth_abi import encode
    return encode(types, values)

def encode_function(abi, fn_name, function_args):
    """
    Encodes function data for a given ABI, function name, and arguments.

    Args:
        abi (list): The ABI of the contract.
        fn_name (str): The name of the function to encode.
        function_args (list): The arguments to pass to the function.

    Returns:
        str | dict: Encoded function data as a hex string, or an error dict if encoding fails.
    """
    try:
        if not abi or not isinstance(function_args, list):
            raise ValueError("Incorrect params passed to encode_function")

        # Find the function ABI in the provided ABI list
        function_abi = next(
            (item for item in abi if item.get("name") == fn_name and item["type"] == "function"),
            None,
        )

        if not function_abi:
            raise ValueError(f"Function {fn_name} not found in the ABI")

        # Get the types of the inputs from the function ABI
        input_types = [inp["type"] for inp in function_abi["inputs"]]

        # Encode the function signature and arguments
        function_signature = f"{fn_name}({','.join(input_types)})"
        selector = function_signature_to_4byte_selector(function_signature)
        encoded_args = encode_abi(input_types, function_args)
        encoded_data = selector + encoded_args

        # Return the encoded data as a hex string
        return Web3.to_hex(encoded_data)
    except Exception as error:
        print("Error:", error)
        return {
            "error": True,
            "message": "Could not encode transaction data with the values provided",
        }

def is_number_string(item):
    if isinstance(item, str):
        try:
            num = float(item)
            return num != float('inf') and num != float('-inf')
        except ValueError:
            return False
    return False

def is_number(item):
    return isinstance(item, (int, float))

def is_numberish(item):
    return is_number(item) or is_number_string(item)

def is_string(item):
    return isinstance(item, str)