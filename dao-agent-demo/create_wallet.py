import sys
from web3 import Web3
from eth_account import Account

def main(prefix=""):

    Account.enable_unaudited_hdwallet_features()

    for i in range(5):
        account, mnemonic = Account.create_with_mnemonic()
        print(f"{prefix}{i}_AGENT_MNEMONIC=\"{mnemonic}\"")
        print(f"{prefix}{i}_AGENT_PRIVATE_KEY=0x{account.key.hex()}")
        print(f"{prefix}{i}_AGENT_ADDR={account.address}")
    
    account, mnemonic = Account.create_with_mnemonic()


    print("Add these to your secrets(.env) file.")



if __name__ == "__main__":
    if len(sys.argv) > 1:
        prefix = sys.argv[1].lower().strip()
        
    main(prefix)

    
