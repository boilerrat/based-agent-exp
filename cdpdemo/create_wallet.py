
import os
from cdp import Cdp, Wallet

from dotenv import load_dotenv
load_dotenv()

file_path = "base_wallet_seed.json"
# Check if the file already exists
if os.path.exists(file_path):
    # Option 1: Raise an error
    raise FileExistsError(f"The file {file_path} already exists and will not be overwritten.")


# Get configuration from environment variables
API_KEY_NAME = os.getenv("CDP_API_KEY_NAME")
PRIVATE_KEY = os.getenv("CDP_PRIVATE_KEY", "").replace('\\n', '\n')

# Configure CDP with environment variables
Cdp.configure(API_KEY_NAME, PRIVATE_KEY)


def main():
    agent_wallet = Wallet.create(network_id="base-mainnet")
    wallet_data = agent_wallet.export_data()
    # wallet_dict = wallet_data.to_dict()
    agent_wallet.save_seed(file_path, encrypt=True)
    print(f"Seed for wallet {agent_wallet.id} saved to {file_path}\n")
    print(f"Agent wallet address: {agent_wallet.default_address.address_id}\n")
    print(f"Update .env with the following values:")
    print(f"TARGET_AGENT_WALLET_ID=\"{agent_wallet.id}\"")
    print(f"TARGET_AGENT_WALLET_ADDRESS=\"{agent_wallet.default_address.address_id}\"")


if __name__ == "__main__":

    print(f"Creating wallet...")
    main()