import dotenv
import os
import sys
from eth_account import Account
from eth_account.account import generate_mnemonic
from eth_account.types import Language


dotenv.load_dotenv(".env")


def main(prefix="PLAYER_"):

    Account.enable_unaudited_hdwallet_features()

    mnemonic = os.environ.get("AGENT_MNEMONIC")
    print(f"Current AGENT_MNEMONIC: {mnemonic}")
    if not mnemonic:
        num_words = 12
        mnemonic = generate_mnemonic(num_words=num_words, lang=Language.ENGLISH)
        print(f"New AGENT_MNEMONIC: {mnemonic}")
        dotenv.set_key(".env", key_to_set="AGENT_MNEMONIC", value_to_set=mnemonic)

    for i in range(3):
        account = Account.from_mnemonic(mnemonic, f"m/44'/60'/0'/0/{i}")
        # print(f"{prefix}{i}_AGENT_PRIVATE_KEY=0x{account.key.hex()}")
        dotenv.set_key(
            ".env",
            key_to_set=f"{prefix}{i}_AGENT_PRIVATE_KEY",
            value_to_set=f"0x{account.key.hex()}"
        )
        dotenv.set_key(
            ".env",
            key_to_set=f"{prefix}{i}_AGENT_ADDR",
            value_to_set=f"{account.address}"
        )
        print(f"{prefix}{i}_AGENT_ADDR={account.address}")
    
    print("Keys added to secrets(.env) file.")


if __name__ == "__main__":
    prefix = "PLAYER_"
    if len(sys.argv) > 1:
        prefix = sys.argv[1].lower().strip()
        
    main(prefix)

    
