from typing import Optional, Dict, Any, List
from starknet_py.contract import Contract
from starknet_py.net.client_models import Call
from .starknet import StarkNetTool
from ..base import SwarmBaseTool

class StarkNetLendingTool(SwarmBaseTool):
    """Tool for StarkNet lending protocols."""
    
    name: str = "starknet_lending"
    description: str = "Interact with lending protocols on StarkNet (zkLend, Nostra)"
    
    LENDING_PROTOCOLS = {
        "zklend": {
            "address": "0x04c0a5193d58f74fbace4b74dcf65481e734ed1714121bdc571da345540efa05",
            "markets": {
                "ETH": "0x01...",
                "USDC": "0x02...",
                "USDT": "0x03..."
            }
        },
        "nostra": {
            "address": "0x04...",
            "markets": {
                "ETH": "0x05...",
                "USDC": "0x06..."
            }
        }
    }
    
    def __init__(self, starknet_tool: StarkNetTool):
        super().__init__()
        self.starknet = starknet_tool
        self.lending_contracts = {}
        self._load_contracts()
        
    def _load_contracts(self):
        """Load lending protocol contracts."""
        for protocol, config in self.LENDING_PROTOCOLS.items():
            self.lending_contracts[protocol] = Contract(
                address=config["address"],
                abi=config["abi"],
                client=self.starknet.client
            )
    
    async def _arun(self, command: str) -> str:
        """Execute lending operations."""
        try:
            cmd_parts = command.split(" ")
            protocol = cmd_parts[0]
            action = cmd_parts[1]
            params = cmd_parts[2:]
            
            if protocol not in self.lending_contracts:
                return f"Unsupported protocol: {protocol}"
                
            if action == "supply":
                return await self._supply(
                    protocol,
                    token=params[0],
                    amount=float(params[1])
                )
            elif action == "borrow":
                return await self._borrow(
                    protocol,
                    token=params[0],
                    amount=float(params[1])
                )
            elif action == "repay":
                return await self._repay(
                    protocol,
                    token=params[0],
                    amount=float(params[1])
                )
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _supply(self, protocol: str, token: str, amount: float) -> str:
        """Supply assets to lending protocol."""
        try:
            contract = self.lending_contracts[protocol]
            market = self.LENDING_PROTOCOLS[protocol]["markets"][token]
            
            # Prepare supply call
            supply_call = contract.functions["supply"].prepare(
                market=market,
                amount=int(amount * (10 ** 18))  # Assuming 18 decimals
            )
            
            # Execute transaction
            tx = await self.starknet.account.execute(supply_call)
            receipt = await tx.wait_for_acceptance()
            
            # Get updated position
            position = await self._get_lending_position(protocol, token)
            
            return (
                f"Supply successful: {receipt.transaction_hash}\n"
                f"Updated position: {position}"
            )
        except Exception as e:
            return f"Supply failed: {str(e)}"

    async def _get_lending_position(self, protocol: str, token: str) -> Dict:
        """Get user's lending position."""
        try:
            contract = self.lending_contracts[protocol]
            market = self.LENDING_PROTOCOLS[protocol]["markets"][token]
            
            position = await contract.functions["get_user_position"].call(
                market=market,
                user=self.starknet.account.address
            )
            
            return {
                "supplied": position.supplied_amount / (10 ** 18),
                "borrowed": position.borrowed_amount / (10 ** 18),
                "health_factor": position.health_factor / (10 ** 18)
            }
        except Exception as e:
            return f"Failed to get position: {str(e)}"

    async def get_market_data(self, protocol: str, token: str) -> str:
        """Get market data for a lending protocol."""
        try:
            contract = self.lending_contracts[protocol]
            market = self.LENDING_PROTOCOLS[protocol]["markets"][token]
            
            data = await contract.functions["get_market_data"].call(market=market)
            
            return {
                "supply_apy": data.supply_apy / (10 ** 18),
                "borrow_apy": data.borrow_apy / (10 ** 18),
                "utilization": data.utilization / (10 ** 18),
                "total_supplied": data.total_supplied / (10 ** 18),
                "total_borrowed": data.total_borrowed / (10 ** 18)
            }
        except Exception as e:
            return f"Failed to get market data: {str(e)}"

class StarkNetNFTTool(SwarmBaseTool):
    """Enhanced tool for StarkNet NFTs."""
    
    NFT_CONTRACTS = {
        "starknet_id": "0x05dbdedc203e92749e2e746e2d40a768d966bd243df04a6b712e222bc040a9af",
        "briq": "0x06...",
        "starkverse": "0x07..."
    }
    
    async def _mint_nft(self, collection: str, token_id: int) -> str:
        """Mint an NFT."""
        try:
            if collection not in self.NFT_CONTRACTS:
                return f"Unsupported collection: {collection}"
                
            contract_address = self.NFT_CONTRACTS[collection]
            contract = await Contract.from_address(contract_address, self.starknet.client)
            
            mint_call = contract.functions["mint"].prepare(
                to=self.starknet.account.address,
                token_id=token_id
            )
            
            tx = await self.starknet.account.execute(mint_call)
            receipt = await tx.wait_for_acceptance()
            
            return f"NFT minted: {receipt.transaction_hash}"
        except Exception as e:
            return f"Mint failed: {str(e)}"

    async def get_nft_metadata(self, collection: str, token_id: int) -> str:
        """Get NFT metadata."""
        try:
            contract_address = self.NFT_CONTRACTS[collection]
            contract = await Contract.from_address(contract_address, self.starknet.client)
            
            uri = await contract.functions["token_uri"].call(token_id)
            owner = await contract.functions["owner_of"].call(token_id)
            
            return {
                "token_id": token_id,
                "owner": owner,
                "uri": uri,
                "collection": collection
            }
        except Exception as e:
            return f"Failed to get metadata: {str(e)}"

class StarkNetBridgeTool(SwarmBaseTool):
    """Enhanced tool for cross-chain bridges."""
    
    BRIDGE_CONFIGS = {
        "orbiter": {
            "address": "0x08...",
            "supported_chains": ["ethereum", "arbitrum", "polygon"]
        },
        "layerswap": {
            "address": "0x09...",
            "supported_chains": ["ethereum", "arbitrum"]
        }
    }
    
    def __init__(self, starknet_tool: StarkNetTool):
        super().__init__()
        self.starknet = starknet_tool
        self.bridge_contracts = {}
        self._load_contracts()
        
    async def _arun(self, command: str) -> str:
        """Execute bridge operations."""
        try:
            cmd_parts = command.split(" ")
            bridge = cmd_parts[0]
            action = cmd_parts[1]
            params = cmd_parts[2:]
            
            if bridge not in self.bridge_contracts:
                return f"Unsupported bridge: {bridge}"
                
            if action == "deposit":
                return await self._bridge_deposit(
                    bridge,
                    token=params[0],
                    amount=float(params[1]),
                    destination_chain=params[2]
                )
            elif action == "withdraw":
                return await self._bridge_withdraw(
                    bridge,
                    token=params[0],
                    amount=float(params[1]),
                    source_chain=params[2]
                )
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _bridge_deposit(
        self,
        bridge: str,
        token: str,
        amount: float,
        destination_chain: str
    ) -> str:
        """Bridge assets to another chain."""
        try:
            if bridge not in self.bridge_contracts:
                return f"Unsupported bridge: {bridge}"
                
            if destination_chain not in self.BRIDGE_CONFIGS[bridge]["supported_chains"]:
                return f"Unsupported destination chain: {destination_chain}"
                
            contract = self.bridge_contracts[bridge]
            
            # Prepare bridge call
            bridge_call = contract.functions["bridge_to"].prepare(
                token=token,
                amount=int(amount * (10 ** 18)),
                destination_chain=destination_chain
            )
            
            # Execute transaction
            tx = await self.starknet.account.execute(bridge_call)
            receipt = await tx.wait_for_acceptance()
            
            return f"Bridge deposit initiated: {receipt.transaction_hash}"
        except Exception as e:
            return f"Bridge deposit failed: {str(e)}"

    async def get_bridge_quote(
        self,
        bridge: str,
        token: str,
        amount: float,
        destination_chain: str
    ) -> str:
        """Get bridge fee quote."""
        try:
            contract = self.bridge_contracts[bridge]
            
            quote = await contract.functions["get_bridge_quote"].call(
                token=token,
                amount=int(amount * (10 ** 18)),
                destination_chain=destination_chain
            )
            
            return {
                "bridge_fee": quote.fee / (10 ** 18),
                "estimated_time": quote.estimated_time,
                "min_amount": quote.min_amount / (10 ** 18),
                "max_amount": quote.max_amount / (10 ** 18)
            }
        except Exception as e:
            return f"Failed to get quote: {str(e)}"

    async def get_bridge_status(self, bridge: str, tx_hash: str) -> str:
        """Get status of a bridge transaction."""
        try:
            contract = self.bridge_contracts[bridge]
            
            status = await contract.functions["get_bridge_status"].call(
                transaction_hash=tx_hash
            )
            
            return {
                "status": status.status,
                "confirmations": status.confirmations,
                "required_confirmations": status.required_confirmations,
                "destination_tx": status.destination_transaction_hash
            }
        except Exception as e:
            return f"Failed to get status: {str(e)}" 