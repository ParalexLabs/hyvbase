from typing import Optional, Dict, Any, List
from starknet_py.net.account.account import Account
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models.chains import StarknetChainId
from starknet_py.contract import Contract
from ..base import SwarmBaseTool
import asyncio
import json
import os
import random

class StarkNetConfig:
    """StarkNet configuration and constants."""
    
    # Token addresses
    ETH_ADDRESS = 0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7
    USDC_ADDRESS = 0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8
    USDT_ADDRESS = 0x068f5c6a61780768455de69077e07e89787839bf8166decfbf92b645209c0fb8
    
    # DEX addresses
    JEDISWAP_ROUTER = "0x041fd22b238fa21cfcf5dd45a8548974d8263b3a531a60388411c5e230f97023"
    MYSWAP_ROUTER = "0x010884171baf1914edc28d7afb619b40a4051cfae78a094a55d230f19e944a28"
    TENK_ROUTER = "0x07a6f98c03379b9513ca84cca1373ff452a7462a3b61598f0af5bb27ad7f76d1"
    
    # Lending protocols
    ZKLEND_ROUTER = "0x04c0a5193d58f74fbace4b74dcf65481e734ed1714121bdc571da345540efa05"
    NOSTRA_ROUTER = "0x040e59c2c182a58fb0a74349bef1593ee94a43db3838eec9d5f0f2235dd81121"

    # NFT contracts
    STARKNET_ID = "0x05dbdedc203e92749e2e746e2d40a768d966bd243df04a6b712e222bc040a9af"
    STARKVERSE = "0x060582df2cd4ad2c988b11fdede5c43f56a432e895df255ccd1af129160044b8"
    UNFRAMED = "0x051734077ba7baf5765896c56ce41f3c4f5b4e66cec5852b43867c580ce0d203"
    STARKSTARS = "0x05b5884487045e893fb3f0e98c34de668d4cc60b1d7ca42489684f7c860ab4cf"
    ALMANAC = "0x05c131e45b9a4d1b2671260062c3e441f1d72d5fd8ab7e4c7d03c4edadc6e96d"

    # Contract deployment
    STARKGUARDIANS_DEPLOYER = "0x06e2616a2dceff4355997369246c25a78e95093df7a49e5ca6a06ce1544ffd50"

    # Additional DEXes
    SITHSWAP_ROUTER = "0x028c858a586fa12123a1ccb337a0a3b369281f91ea00544d0c086524b759f627"
    PROTOSS_ROUTER = "0x07a0922657e47de9b25d9e0af32c8cf3e7029f2614f1f23774530c4dc0c465f3"
    AVNU_ROUTER = "0x04270219d365d6b017231b52e92b3fb5d7c8378b05e9abc97724537a80e93b0f"
    OPENOCEAN_ROUTER = "0x042aa74f859c68b5a6c76885a3bba1a1ed7f59c5b5d3c7f2fbb2fd1ccc3fbf7f"

    # NFT Marketplaces
    FLEX_MARKETPLACE = "0x04d0390b777b424e43839cd1e744799f3de6c176c7e32c1812a41dbd9c19db6a"
    UNFRAMED_MARKETPLACE = "0x051734077ba7baf5765896c56ce41f3c4f5b4e66cec5852b43867c580ce0d203"

    # Gas estimation safety margins
    GAS_MARGIN = 1.2  # 20% extra for safety
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

class StarkNetTool(SwarmBaseTool):
    """Tool for interacting with StarkNet."""
    
    name: str = "starknet"
    description: str = "Execute operations on StarkNet blockchain"
    
    def __init__(
        self,
        private_key: str,
        account_address: str,
        rpc_url: str = "https://starknet-mainnet.public.blastapi.io"
    ):
        super().__init__()
        self.client = GatewayClient(rpc_url)
        self.account = Account(
            client=self.client,
            address=account_address,
            key_pair=private_key,
            chain=StarknetChainId.MAINNET
        )
        self._load_abis()
        
    def _load_abis(self):
        """Load contract ABIs."""
        self.abis = {}
        abi_dir = "abi"
        for contract in ["erc20", "jediswap", "myswap", "zklend", "dmail"]:
            with open(f"{abi_dir}/{contract}/abi.json") as f:
                self.abis[contract] = json.load(f)
                
    async def _arun(self, command: str) -> str:
        """Execute StarkNet operations."""
        try:
            cmd_parts = command.split(" ")
            action = cmd_parts[0]
            
            if action == "swap":
                return await self.execute_swap(
                    dex=cmd_parts[1],
                    token_in=cmd_parts[2],
                    token_out=cmd_parts[3],
                    amount=int(cmd_parts[4])
                )
                
            elif action == "lend":
                return await self.execute_lending(
                    protocol=cmd_parts[1],
                    action=cmd_parts[2],
                    token=cmd_parts[3],
                    amount=int(cmd_parts[4])
                )
                
            elif action == "nft":
                return await self.execute_nft_action(
                    protocol=cmd_parts[1],
                    action=cmd_parts[2],
                    token_id=int(cmd_parts[3])
                )
                
            elif action == "dmail":
                return await self.send_dmail(
                    to=cmd_parts[1],
                    subject=cmd_parts[2]
                )
                
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def execute_swap(
        self,
        dex: str,
        token_in: str,
        token_out: str,
        amount: int,
        slippage: float = 0.01  # 1% slippage
    ) -> str:
        """Execute a swap with enhanced features."""
        try:
            # Get router contract
            router_address = getattr(StarkNetConfig, f"{dex.upper()}_ROUTER")
            router = Contract(
                address=router_address,
                abi=self.abis[dex.lower()],
                client=self.client
            )
            
            # Special handling for AVNU aggregator
            if dex == "avnu":
                quote = await router.get_quote(
                    token_in=getattr(StarkNetConfig, f"{token_in}_ADDRESS"),
                    token_out=getattr(StarkNetConfig, f"{token_out}_ADDRESS"),
                    amount=amount
                )
                
                # Simulate transaction
                tx = await router.build_swap_tx(quote.id)
                simulation = await self.simulate_transaction(tx)
                
                if not simulation["success"]:
                    raise Exception("Swap simulation failed")
                    
                # Execute with retry
                tx = await self.execute_with_retry(
                    router.swap,
                    quote.id,
                    max_fee=simulation["fee"]
                )
                
            else:
                # Standard DEX swap flow
                if token_in != "ETH":
                    await self.execute_with_retry(
                        self._approve_token,
                        token_in,
                        router_address,
                        amount
                    )
                
                # Get expected output amount
                amounts = await router.get_amounts_out(
                    amount,
                    [
                        getattr(StarkNetConfig, f"{token_in}_ADDRESS"),
                        getattr(StarkNetConfig, f"{token_out}_ADDRESS")
                    ]
                )
                min_out = int(amounts[1] * (1 - slippage))
                
                # Build and simulate swap
                swap_tx = await router.swap_exact_tokens_for_tokens.prepare(
                    amount_in=amount,
                    amount_out_min=min_out,
                    path=[
                        getattr(StarkNetConfig, f"{token_in}_ADDRESS"),
                        getattr(StarkNetConfig, f"{token_out}_ADDRESS")
                    ],
                    to=self.account.address,
                    deadline=999999999999
                )
                
                simulation = await self.simulate_transaction(swap_tx)
                if not simulation["success"]:
                    raise Exception("Swap simulation failed")
                    
                # Execute swap with retry
                tx = await self.execute_with_retry(
                    self.account.execute,
                    swap_tx,
                    max_fee=simulation["fee"]
                )
                
            return f"Swap executed: {tx.hash}"
            
        except Exception as e:
            return f"Swap failed: {str(e)}"

    async def execute_lending(
        self,
        protocol: str,
        action: str,
        token: str,
        amount: int
    ) -> str:
        """Execute lending protocol actions."""
        try:
            # Get protocol contract
            protocol_address = getattr(StarkNetConfig, f"{protocol.upper()}_ROUTER")
            protocol_contract = Contract(
                address=protocol_address,
                abi=self.abis[protocol.lower()],
                client=self.client
            )
            
            if action == "deposit":
                tx = await protocol_contract.deposit(
                    token=getattr(StarkNetConfig, f"{token}_ADDRESS"),
                    amount=amount
                )
            elif action == "withdraw":
                tx = await protocol_contract.withdraw(
                    token=getattr(StarkNetConfig, f"{token}_ADDRESS"),
                    amount=amount
                )
            elif action == "borrow":
                tx = await protocol_contract.borrow(
                    token=getattr(StarkNetConfig, f"{token}_ADDRESS"),
                    amount=amount
                )
            elif action == "repay":
                tx = await protocol_contract.repay(
                    token=getattr(StarkNetConfig, f"{token}_ADDRESS"),
                    amount=amount
                )
                
            return f"Lending action executed: {tx.hash}"
            
        except Exception as e:
            return f"Lending action failed: {str(e)}"

    async def execute_nft_action(
        self,
        protocol: str,
        action: str,
        token_id: int,
        **kwargs
    ) -> str:
        """Execute NFT-related actions."""
        try:
            # Get NFT contract
            nft_address = getattr(StarkNetConfig, f"{protocol.upper()}")
            nft_contract = Contract(
                address=nft_address,
                abi=self.abis[protocol.lower()],
                client=self.client
            )
            
            if action == "mint":
                if protocol == "starknet_id":
                    tx = await nft_contract.mint(token_id)
                elif protocol == "starkstars":
                    tx = await nft_contract.mint()
                elif protocol == "almanac":
                    tx = await nft_contract.publicMint(
                        almanac=kwargs.get("almanac_data"),
                        recipient=self.account.address
                    )
                    
            elif action == "transfer":
                tx = await nft_contract.transferFrom(
                    self.account.address,
                    kwargs["to_address"],
                    token_id
                )
                
            elif action == "approve":
                tx = await nft_contract.approve(
                    kwargs["operator"],
                    token_id
                )
                
            return f"NFT action executed: {tx.hash}"
            
        except Exception as e:
            return f"NFT action failed: {str(e)}"

    async def deploy_contract(
        self,
        contract_type: str,
        salt: int,
        constructor_args: Dict[str, Any]
    ) -> str:
        """Deploy a new contract."""
        try:
            deployer = Contract(
                address=StarkNetConfig.STARKGUARDIANS_DEPLOYER,
                abi=self.abis["starkguardians"],
                client=self.client
            )
            
            # Get class hash based on contract type
            if contract_type == "token":
                class_hash = "0x..." # Add ERC20 class hash
            elif contract_type == "nft":
                class_hash = "0x..." # Add ERC721 class hash
                
            tx = await deployer.deployContract(
                classHash=class_hash,
                salt=salt,
                unique=1,  # Unique deployment
                constructorCalldata=constructor_args
            )
            
            return f"Contract deployed: {tx.hash}"
            
        except Exception as e:
            return f"Deployment failed: {str(e)}"

    async def build_volume(
        self,
        target_volume: int,
        token: str = "USDC",
        num_swaps: int = 5
    ) -> str:
        """Build trading volume through multiple swaps."""
        try:
            # First deposit ETH to lending protocol
            deposit_amount = target_volume // 2
            await self.execute_lending(
                protocol="zklend",
                action="deposit",
                token="ETH",
                amount=deposit_amount
            )
            
            # Enable collateral
            zklend = Contract(
                address=StarkNetConfig.ZKLEND_ROUTER,
                abi=self.abis["zklend"],
                client=self.client
            )
            await zklend.enable_collateral("ETH")
            
            # Borrow target token
            borrow_amount = target_volume // 3
            await self.execute_lending(
                protocol="zklend",
                action="borrow",
                token=token,
                amount=borrow_amount
            )
            
            # Execute multiple swaps between DEXes
            dexes = ["jediswap", "myswap", "sithswap", "tenk"]
            for _ in range(num_swaps):
                dex = random.choice(dexes)
                await self.execute_swap(
                    dex=dex,
                    token_in=token,
                    token_out="ETH",
                    amount=borrow_amount // num_swaps
                )
                await self.execute_swap(
                    dex=dex,
                    token_in="ETH",
                    token_out=token,
                    amount=borrow_amount // num_swaps
                )
                
            # Repay borrowed amount
            await self.execute_lending(
                protocol="zklend",
                action="repay",
                token=token,
                amount=borrow_amount
            )
            
            # Withdraw ETH
            await self.execute_lending(
                protocol="zklend",
                action="withdraw",
                token="ETH",
                amount=deposit_amount
            )
            
            return "Volume building completed successfully"
            
        except Exception as e:
            return f"Volume building failed: {str(e)}"

    async def estimate_gas(self, tx) -> int:
        """Estimate gas for a transaction with safety margin."""
        try:
            estimated = await self.client.estimate_fee(tx)
            return int(estimated.overall_fee * self.GAS_MARGIN)
        except Exception as e:
            raise Exception(f"Gas estimation failed: {str(e)}")

    async def simulate_transaction(self, tx) -> Dict:
        """Simulate a transaction before sending."""
        try:
            simulation = await self.client.simulate_transaction(tx)
            return {
                "success": simulation.status == "ACCEPTED",
                "gas_used": simulation.gas_used,
                "gas_price": simulation.gas_price,
                "fee": simulation.fee
            }
        except Exception as e:
            raise Exception(f"Simulation failed: {str(e)}")

    async def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute a function with retry mechanism."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                continue
        raise Exception(f"Operation failed after {self.MAX_RETRIES} attempts: {str(last_error)}")

    async def execute_marketplace_action(
        self,
        marketplace: str,
        action: str,
        token_id: int,
        price: Optional[int] = None,
        **kwargs
    ) -> str:
        """Execute NFT marketplace actions."""
        try:
            marketplace_address = getattr(StarkNetConfig, f"{marketplace.upper()}_MARKETPLACE")
            marketplace_contract = Contract(
                address=marketplace_address,
                abi=self.abis[marketplace.lower()],
                client=self.client
            )
            
            if action == "list":
                tx = await self.execute_with_retry(
                    marketplace_contract.list_token,
                    token_id=token_id,
                    price=price
                )
            elif action == "buy":
                tx = await self.execute_with_retry(
                    marketplace_contract.buy,
                    token_id=token_id,
                    price=price
                )
            elif action == "cancel":
                tx = await self.execute_with_retry(
                    marketplace_contract.cancel_listing,
                    token_id=token_id
                )
                
            return f"Marketplace action executed: {tx.hash}"
            
        except Exception as e:
            return f"Marketplace action failed: {str(e)}" 