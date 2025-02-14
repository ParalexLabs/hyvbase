from typing import Optional, Dict, Any
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from spl.token.instructions import get_associated_token_address
from ..base import SwarmBaseTool

class SolanaTool(SwarmBaseTool):
    """Base tool for Solana operations."""
    
    name: str = "solana"
    description: str = "Execute Solana transactions and interact with programs"
    
    def __init__(
        self,
        rpc_url: str,
        payer: Any,  # Keypair
        commitment: str = Confirmed
    ):
        super().__init__()
        self.client = AsyncClient(rpc_url, commitment=commitment)
        self.payer = payer
        
    async def _arun(self, command: str) -> str:
        """Execute Solana operations."""
        try:
            cmd_parts = command.split(" ")
            action = cmd_parts[0]
            params = cmd_parts[1:]
            
            if action == "balance":
                return await self._get_balance(params[0])
            elif action == "transfer":
                return await self._transfer_sol(params[0], float(params[1]))
            elif action == "airdrop":
                return await self._request_airdrop(params[0], float(params[1]))
            else:
                return f"Unknown command: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def _get_balance(self, address: str) -> str:
        """Get SOL balance of an address."""
        balance = await self.client.get_balance(address)
        return f"Balance: {balance.value / 1e9} SOL"

    async def _transfer_sol(self, to_address: str, amount: float) -> str:
        """Transfer SOL to an address."""
        try:
            # Convert amount to lamports
            lamports = int(amount * 1e9)
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.payer.public_key,
                    to_pubkey=to_address,
                    lamports=lamports
                )
            )
            
            # Create and sign transaction
            tx = Transaction().add(transfer_ix)
            tx.recent_blockhash = (
                await self.client.get_latest_blockhash()
            ).value.blockhash
            
            # Sign and send transaction
            signed_tx = self.payer.sign_transaction(tx)
            tx_hash = await self.client.send_transaction(signed_tx)
            
            return f"Transfer successful: {tx_hash.value}"
        except Exception as e:
            return f"Transfer failed: {str(e)}"

    async def _request_airdrop(self, address: str, amount: float) -> str:
        """Request SOL airdrop (devnet/testnet only)."""
        try:
            lamports = int(amount * 1e9)
            result = await self.client.request_airdrop(
                address,
                lamports,
                commitment=self.client.commitment
            )
            return f"Airdrop successful: {result.value}"
        except Exception as e:
            return f"Airdrop failed: {str(e)}"

    async def get_token_accounts(self, owner: str) -> str:
        """Get all token accounts for an owner."""
        try:
            accounts = await self.client.get_token_accounts_by_owner(
                owner,
                commitment=self.client.commitment
            )
            return "\n".join(
                f"Token: {acc.account.data.parsed['info']['mint']}, "
                f"Balance: {acc.account.data.parsed['info']['tokenAmount']['uiAmount']}"
                for acc in accounts.value
            )
        except Exception as e:
            return f"Failed to get token accounts: {str(e)}"

class SolanaSPLTool(SwarmBaseTool):
    """Tool for SPL token operations."""
    
    name: str = "solana_spl"
    description: str = "Interact with SPL tokens on Solana"
    
    def __init__(self, solana_tool: SolanaTool):
        super().__init__()
        self.solana = solana_tool
        
    async def _arun(self, command: str) -> str:
        """Execute SPL token operations."""
        try:
            cmd_parts = command.split(" ")
            action = cmd_parts[0]
            params = cmd_parts[1:]
            
            if action == "balance":
                return await self._get_token_balance(params[0], params[1])
            elif action == "transfer":
                return await self._transfer_tokens(
                    token_mint=params[0],
                    to_address=params[1],
                    amount=float(params[2])
                )
            elif action == "create_account":
                return await self._create_token_account(params[0])
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _get_token_balance(self, token_mint: str, owner: str) -> str:
        """Get SPL token balance for an owner."""
        try:
            # Get associated token account
            ata = get_associated_token_address(owner, token_mint)
            
            # Get account info
            account_info = await self.solana.client.get_token_account_balance(ata)
            
            return (
                f"Token balance: "
                f"{account_info.value.ui_amount} "
                f"(decimals: {account_info.value.decimals})"
            )
        except Exception as e:
            return f"Failed to get token balance: {str(e)}"

    async def _transfer_tokens(
        self,
        token_mint: str,
        to_address: str,
        amount: float
    ) -> str:
        """Transfer SPL tokens."""
        try:
            # Get associated token accounts
            from_ata = get_associated_token_address(
                self.solana.payer.public_key,
                token_mint
            )
            to_ata = get_associated_token_address(to_address, token_mint)
            
            # Create transfer instruction
            transfer_ix = spl_token.transfer(
                token_program_id=TOKEN_PROGRAM_ID,
                source=from_ata,
                dest=to_ata,
                owner=self.solana.payer.public_key,
                amount=int(amount * (10 ** token_decimals))
            )
            
            # Create and send transaction
            tx = Transaction().add(transfer_ix)
            tx.recent_blockhash = (
                await self.solana.client.get_latest_blockhash()
            ).value.blockhash
            
            signed_tx = self.solana.payer.sign_transaction(tx)
            tx_hash = await self.solana.client.send_transaction(signed_tx)
            
            return f"Token transfer successful: {tx_hash.value}"
        except Exception as e:
            return f"Token transfer failed: {str(e)}"

class SolanaMarketTool(SwarmBaseTool):
    """Tool for Solana DEX operations."""
    
    name: str = "solana_market"
    description: str = "Execute trades on Solana DEXes (Raydium, Orca)"
    
    def __init__(self, solana_tool: SolanaTool):
        super().__init__()
        self.solana = solana_tool
        
    async def _arun(self, command: str) -> str:
        """Execute market operations."""
        try:
            cmd_parts = command.split(" ")
            dex = cmd_parts[0]
            action = cmd_parts[1]
            params = cmd_parts[2:]
            
            if action == "swap":
                return await self._swap(
                    dex=dex,
                    token_in=params[0],
                    token_out=params[1],
                    amount=float(params[2])
                )
            elif action == "pool_info":
                return await self._get_pool_info(dex, params[0])
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _swap(
        self,
        dex: str,
        token_in: str,
        token_out: str,
        amount: float
    ) -> str:
        """Execute swap on Raydium or Orca."""
        try:
            if dex == "raydium":
                return await self._raydium_swap(token_in, token_out, amount)
            elif dex == "orca":
                return await self._orca_swap(token_in, token_out, amount)
            else:
                return f"Unsupported DEX: {dex}"
        except Exception as e:
            return f"Swap failed: {str(e)}"

    async def _get_pool_info(self, dex: str, pool_address: str) -> str:
        """Get pool information."""
        try:
            pool_info = await self.solana.client.get_account_info(pool_address)
            # Parse pool data based on DEX
            if dex == "raydium":
                return self._parse_raydium_pool(pool_info.value.data)
            elif dex == "orca":
                return self._parse_orca_pool(pool_info.value.data)
            else:
                return f"Unsupported DEX: {dex}"
        except Exception as e:
            return f"Failed to get pool info: {str(e)}"

    async def get_best_route(
        self,
        token_in: str,
        token_out: str,
        amount: float
    ) -> str:
        """Find best swap route across all DEXes."""
        try:
            routes = []
            
            # Check Raydium route
            raydium_quote = await self._get_raydium_quote(
                token_in,
                token_out,
                amount
            )
            if raydium_quote:
                routes.append(("raydium", raydium_quote))
            
            # Check Orca route
            orca_quote = await self._get_orca_quote(
                token_in,
                token_out,
                amount
            )
            if orca_quote:
                routes.append(("orca", orca_quote))
            
            if not routes:
                return "No routes found"
            
            # Find best route
            best_route = max(routes, key=lambda x: x[1]["out_amount"])
            
            return (
                f"Best route: {best_route[0]}\n"
                f"Output amount: {best_route[1]['out_amount']}\n"
                f"Price impact: {best_route[1]['price_impact']}%"
            )
        except Exception as e:
            return f"Failed to find route: {str(e)}" 