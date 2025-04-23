# -*- coding: utf-8 -*-
from web3 import Web3

from django.conf import settings

# import os
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECHOME.settings')

class ChainContract:
    def __init__(self):
        self.infura_url = settings.INFURA_URL
        self.private_key = settings.PRIVATE_KEY
        self.wallet_address = settings.WALLET_ADDRESS
        self.contract_address = Web3.to_checksum_address(settings.CONTRACT_ADDRESS)
        self.w3 = Web3(Web3.HTTPProvider(self.infura_url))

        self.abi = [
            {
                "inputs": [
                    {"internalType": "string", "name": "_data", "type": "string"},
                    {"internalType": "uint256", "name": "delaySeconds", "type": "uint256"}
                ],
                "name": "storeWithDelay",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "markAndReturnExpired",
                "outputs": [
                    {"internalType": "string[]", "name": "", "type": "string[]"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "uint256", "name": "id", "type": "uint256"},
                    {"indexed": False, "internalType": "string", "name": "data", "type": "string"}
                ],
                "name": "MarkedExpired",
                "type": "event"
            }

        ]

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    def store_data(self, data, delay_seconds):
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        tx = self.contract.functions.storeWithDelay(data, delay_seconds).build_transaction({
            'chainId': 11155111,  # Replace with your chain ID
            'gas': 600000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print("decoded input")
        print("\n--- Storage Confirmation ---")
        print(f"Transaction hash: {self.w3.to_hex(tx_hash)}")
        print(f"Block number: {receipt['blockNumber']}")
        print(f"Gas used: {receipt['gasUsed']}")

        # Decode the transaction input to verify what was stored
        tx = self.w3.eth.get_transaction(tx_hash)
        decoded_input = self.contract.decode_function_input(tx['input'])
        function_args = decoded_input[1]
        print(f"Stored data: '{function_args['_data']}'")
        print(f"With expiration delay: {function_args['delaySeconds']} seconds")
        print("--- End of Confirmation ---\n")

        return receipt




    def get_expired_data(self):
        try:
            # Build and send transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            tx = self.contract.functions.markAndReturnExpired().build_transaction({
                'chainId': 11155111,  # Sepolia
                'gas': 600000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # KEY FIX: Properly parse logs for MarkedExpired events
            expired_cids = []
            event_abi = self.contract.events.MarkedExpired().abi

            for log in receipt['logs']:
                try:
                    # Decode each log entry
                    event_data = self.w3.eth.contract(abi=[event_abi]).events.MarkedExpired().process_log(log)
                    expired_cids.append(event_data['args']['data'])
                except:
                    continue  # Skip logs that aren't our event

            print(f"Found {len(expired_cids)} expired CIDs in transaction logs")
            return expired_cids

        except Exception as e:
            print(f"Error retrieving expired data: {str(e)}")
            return []
