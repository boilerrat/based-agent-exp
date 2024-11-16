import os
import json

from web3 import Web3
from web3.exceptions import ContractLogicError

with open("abis/baal_abi.json", "r") as abi_file:
    baal_abi = json.load(abi_file)

