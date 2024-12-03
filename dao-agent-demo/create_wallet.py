from web3 import Web3
from eth_account import Account

def main():
    # Generate a new mnemonic (seed phrase)
    Account.enable_unaudited_hdwallet_features()
    account, mnemonic = Account.create_with_mnemonic()

    # Print the seed phrase and public address
    print("New Wallet:")
    print(f"AGENT_MNEMONIC=\"{mnemonic}\"")
    print(f"AGENT_PRIVATE_KEY=0x{account.key.hex()}")
    print(f"AGENT_ADDR={account.address}")
    print("Add these to your secrets(.env) file.")

if __name__ == "__main__":
    main()
