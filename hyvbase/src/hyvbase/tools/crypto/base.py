from langchain.tools import BaseTool
from typing import Optional, List
import traceback
import asyncio
from dataclasses import dataclass
from starknet_py.net.client import Client
from starknet_py.net.models import StarknetChainId
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.net.client_models import Call, ResourceBounds
from starknet_py.net.full_node_client import FullNodeClient
from pydantic import BaseModel, Field
from starknet_py.contract import Contract
from decimal import Decimal
from starknet_py.hash.selector import get_selector_from_name

class StarknetConfig(BaseModel):
    """Configuration for Starknet tool"""
    private_key: str
    account_address: str
    rpc_url: str = "https://starknet-mainnet.public.blastapi.io"
    chain_id: StarknetChainId = StarknetChainId.MAINNET
    # L1 Resource bounds - adjusted for current gas prices
    l1_max_amount: int = int(1e3)  # 1,000 (keep the same amount)
    l1_max_price_per_unit: int = int(2.5e13)  # 25,000 Gwei (increased to handle current gas prices)

class StarknetTool(BaseTool):
    """Base tool for Starknet operations"""
    
    name: str = "starknet"
    description: str = "Execute operations on Starknet"
    config: StarknetConfig = None
    client: Client = None
    account: Account = None
    key_pair: KeyPair = None
    
    def __init__(self, private_key: str, account_address: str, rpc_url: Optional[str] = None, chain_id: Optional[StarknetChainId] = None):
        """Initialize Starknet tool"""
        super().__init__()
        
        if not private_key:
            raise ValueError("Private key is required")
        if not account_address:
            raise ValueError("Account address is required")
        
        # Validate account address format
        if account_address.startswith("0x"):
            account_address = account_address[2:]
        if len(account_address) > 64:
            raise ValueError("Invalid Starknet account address format. Address too long.")
        
        # Create config immediately with all parameters
        self.config = StarknetConfig(
            private_key=private_key,
            account_address=account_address,
            rpc_url=rpc_url or "https://starknet-mainnet.public.blastapi.io",
            chain_id=chain_id or StarknetChainId.MAINNET
        )
        self._initialize()

    def _initialize(self):
        """Initialize client and account"""
        try:
            if self.client and self.account:
                return  # Already initialized
            
            # Create key pair from private key
            self.key_pair = KeyPair.from_private_key(int(self.config.private_key, 16))
            
            # Initialize client
            self.client = FullNodeClient(node_url=self.config.rpc_url)
            
            # Initialize account
            self.account = Account(
                address=int(self.config.account_address, 16),
                client=self.client,
                key_pair=self.key_pair,
                chain=self.config.chain_id
            )
            
            # Verify account is deployed
            try:
                self.client.get_class_hash_at(int(self.config.account_address, 16))
            except Exception as e:
                if "Contract not found" in str(e):
                    raise ValueError(f"Account {self.config.account_address} is not deployed on {self.config.chain_id.name}")
                raise
            
        except Exception as e:
            raise ValueError(f"Failed to initialize StarknetTool: {str(e)}")

    def _run(self, command: str) -> str:
        """Execute Starknet operation"""
        raise NotImplementedError("StarknetTool only supports async operations")
    
    async def _arun(self, command: str) -> str:
        """Execute Starknet operation async"""
        raise NotImplementedError("Subclasses must implement _arun")
    
    async def get_contract(self, address: int) -> 'Contract':
        """Get contract instance asynchronously"""
        try:
            # Await the asynchronous call to load the contract
            contract = await Contract.from_address(
                address=address,
                provider=self.client,  # Use provider instead of client
            )
            return contract
        except Exception as e:
            raise ValueError(f"Failed to create contract: {str(e)}")

    async def sign_transaction(self, calls: List[Call]) -> dict:
        """Sign and execute a transaction"""
        try:
            # Configure L1 resource bounds with reasonable limits
            l1_resource_bounds = ResourceBounds(
                max_amount=self.config.l1_max_amount,
                max_price_per_unit=self.config.l1_max_price_per_unit
            )
            
            # Execute V3 transaction
            tx_response = await self.account.execute_v3(
                calls=calls,
                l1_resource_bounds=l1_resource_bounds
            )
            
            return tx_response
            
        except Exception as e:
            raise ValueError(f"Failed to process transaction: {str(e)}")

    async def send_transaction(self, tx) -> str:
        """Wait for transaction acceptance"""
        try:
            # Return the transaction hash immediately
            tx_hash_url = f"https://starkscan.co/tx/{hex(tx.transaction_hash)}"
            
            # Start waiting for transaction confirmation in background
            asyncio.create_task(self._monitor_transaction(tx.transaction_hash))
            
            return tx_hash_url
            
        except Exception as e:
            raise ValueError(f"Failed to send transaction: {str(e)}")

    async def _monitor_transaction(self, tx_hash: int):
        """Monitor transaction status in background"""
        try:
            await self.wait_until_tx_finished(tx_hash)
        except Exception:
            pass

    async def wait_until_tx_finished(self, tx_hash: int):
        """Wait until transaction is accepted on L2"""
        try:
            await asyncio.sleep(10)  # Initial delay
            
            retries = 30  # Maximum number of retries
            attempt = 0
            
            while attempt < retries:
                try:
                    tx_status = await self.client.get_transaction_status(tx_hash)
                    
                    # Exit loop if transaction is confirmed and succeeded
                    if (str(tx_status.finality_status) == "ACCEPTED_ON_L2" and 
                        str(tx_status.execution_status) == "SUCCEEDED"):
                        return

                    # Handle rejections and reverts
                    if str(tx_status.finality_status) == "REJECTED":
                        raise ValueError(f"Transaction {tx_hash} was rejected")
                    if (str(tx_status.finality_status) == "ACCEPTED_ON_L2" and 
                        str(tx_status.execution_status) == "REVERTED"):
                        raise ValueError(f"Transaction {tx_hash} was reverted on L2")
                    
                    attempt += 1
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    if "Transaction hash not found" in str(e) or "Transaction not found" in str(e):
                        attempt += 1
                        if attempt >= retries:
                            raise ValueError(f"Transaction {tx_hash} not found after {retries} attempts")
                        await asyncio.sleep(5)
                        continue
                    raise

            raise ValueError(f"Transaction {tx_hash} did not confirm within {retries} attempts")

        except Exception as e:
            raise ValueError(f"Failed waiting for transaction: {str(e)}")

    async def _get_balance(self) -> str:
        """Get account balance"""
        # Implementation for getting balance
        return f"Balance for {self.config.account_address}"
    
    async def _transfer(self, params: list) -> str:
        """Execute transfer"""
        if len(params) < 2:
            return "Invalid transfer parameters. Required: to_address amount"
        # Implementation for transfer
        return f"Transfer executed"

    async def execute_transfer(self, token: str, amount: float, recipient: str) -> str:
        """Execute token transfer on StarkNet"""
        try:
            # Get token contract address from registry
            token_address = self.get_token_address(token)
            if not token_address:
                raise ValueError(f"Token {token} not found in registry")
                
            # Convert amount to wei
            decimals = await self.get_token_decimals(token_address)
            amount_wei = int(amount * (10 ** decimals))
            
            # Prepare transfer call
            transfer_call = self.get_transfer_call(
                token_address=token_address,
                recipient=recipient,
                amount=amount_wei
            )
            
            # Execute transfer using account (not client)
            tx = await self.account.execute_v3(
                calls=[transfer_call],
                l1_resource_bounds=ResourceBounds(
                    max_amount=self.config.l1_max_amount,
                    max_price_per_unit=self.config.l1_max_price_per_unit
                )
            )
            
            # Start monitoring transaction
            asyncio.create_task(self._monitor_transaction(tx.transaction_hash))
            
            return f"Transaction hash: {hex(tx.transaction_hash)}"
            
        except Exception as e:
            raise Exception(f"Transfer execution failed: {str(e)}")
            
    def get_token_address(self, token: str) -> str:
        """Get token contract address from registry"""
        # Token address registry
        TOKEN_ADDRESSES = {
            "ETH": "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7",
            "USDC": "0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8",
            "USDT": "0x068f5c6a61780768455de69077e07e89787839bf8166decfbf92b645209c0fb8",
            "STARK": "0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d"
        }
        return TOKEN_ADDRESSES.get(token.upper())
        
    async def get_token_decimals(self, token_address: str) -> int:
        """Get token decimals from contract"""
        try:
            # Call decimals() on token contract
            result = await self.client.call_contract(
                call=Call(
                    to_addr=int(token_address, 16),
                    selector=get_selector_from_name("decimals"),
                    calldata=[]
                )
            )
            return result[0]
        except Exception:
            return 18  # Default to 18 decimals
            
    def get_transfer_call(self, token_address: str, recipient: str, amount: int) -> Call:
        """Create transfer call for token contract"""
        return Call(
            to_addr=int(token_address, 16),
            selector=get_selector_from_name("transfer"),
            calldata=[int(recipient, 16), amount, 0]  # recipient, amount low, amount high
        ) 