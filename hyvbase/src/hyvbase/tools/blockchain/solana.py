from typing import Optional, Dict, Any, List, Callable, TypeVar, Union
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction, TransactionInstruction
from solana.system_program import TransferParams, transfer
from solana.keypair import Keypair
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from spl.token.instructions import get_associated_token_address, create_associated_token_account
from spl.token.client import Token
from ..base import SwarmBaseTool
import asyncio
import base58
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
import random

class SolanaConfig:
    """Solana configuration and constants."""
    
    # Common program IDs
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    
    # Popular token addresses
    USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    RAY = "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R"
    
    # DEX program IDs
    RAYDIUM_SWAP = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    ORCA_SWAP = "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1"
    
    # NFT program IDs
    METAPLEX = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
    CANDY_MACHINE = "cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ"

@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 10.0  # seconds
    exponential_base: float = 2
    jitter: float = 0.1
    timeout: float = 30.0  # seconds

class SolanaError(Exception):
    """Base exception class for Solana operations."""
    pass

class TransactionError(SolanaError):
    """Exception for transaction-related errors."""
    def __init__(self, message: str, tx_hash: Optional[str] = None):
        super().__init__(message)
        self.tx_hash = tx_hash

class ConnectionError(SolanaError):
    """Exception for RPC connection errors."""
    pass

class SolanaTool(SwarmBaseTool):
    """Tool for interacting with Solana blockchain."""
    
    name: str = "solana"
    description: str = "Execute operations on Solana blockchain"
    
    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        commitment: str = "confirmed",
        retry_config: Optional[RetryConfig] = None
    ):
        super().__init__()
        self.client = AsyncClient(rpc_url, commitment=Commitment(commitment))
        self.keypair = Keypair.from_secret_key(base58.b58decode(private_key))
        self.retry_config = retry_config or RetryConfig()
        
    async def _arun(self, command: str) -> str:
        """Execute Solana operations."""
        try:
            cmd_parts = command.split(" ")
            action = cmd_parts[0]
            
            if action == "transfer":
                return await self.transfer_sol(
                    to_address=cmd_parts[1],
                    amount=float(cmd_parts[2])
                )
                
            elif action == "token":
                return await self.handle_token_action(
                    action=cmd_parts[1],
                    token=cmd_parts[2],
                    *cmd_parts[3:]
                )
                
            elif action == "swap":
                return await self.execute_swap(
                    dex=cmd_parts[1],
                    token_in=cmd_parts[2],
                    token_out=cmd_parts[3],
                    amount=float(cmd_parts[4])
                )
                
            elif action == "nft":
                return await self.handle_nft_action(
                    action=cmd_parts[1],
                    *cmd_parts[2:]
                )
                
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def transfer_sol(
        self,
        to_address: str,
        amount: float,
        opts: Optional[TxOpts] = None
    ) -> str:
        """Transfer SOL to another address."""
        try:
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.keypair.public_key,
                    to_pubkey=to_address,
                    lamports=int(amount * 1e9)
                )
            )
            
            tx = Transaction().add(transfer_ix)
            
            # Get recent blockhash
            blockhash = await self.client.get_recent_blockhash()
            tx.recent_blockhash = blockhash["result"]["value"]["blockhash"]
            
            # Sign and send transaction
            tx.sign(self.keypair)
            tx_hash = await self.client.send_transaction(
                tx,
                self.keypair,
                opts=opts
            )
            
            return f"Transfer successful: {tx_hash['result']}"
            
        except Exception as e:
            return f"Transfer failed: {str(e)}"
            
    async def handle_token_action(
        self,
        action: str,
        token: str,
        *args
    ) -> str:
        """Enhanced token operations with error handling."""
        try:
            token_address = getattr(SolanaConfig, token.upper(), token)
            
            async def _get_token_client():
                return Token(
                    self.client,
                    token_address,
                    SolanaConfig.TOKEN_PROGRAM_ID,
                    self.keypair
                )
                
            token_client = await self.with_retry(_get_token_client)
            
            if action == "transfer":
                to_address = args[0]
                amount = float(args[1])
                
                # Validate amount
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                    
                # Get or create associated token accounts with retry
                async def _setup_accounts():
                    from_ata = get_associated_token_address(
                        self.keypair.public_key,
                        token_address
                    )
                    
                    # Check balance
                    balance = await token_client.get_balance(from_ata)
                    if balance < amount:
                        raise ValueError(f"Insufficient balance: {balance}")
                        
                    to_ata = get_associated_token_address(
                        to_address,
                        token_address
                    )
                    
                    # Create destination ATA if needed
                    if not await self.client.get_account_info(to_ata):
                        create_ata_ix = create_associated_token_account(
                            payer=self.keypair.public_key,
                            owner=to_address,
                            mint=token_address
                        )
                        await self._send_transaction([create_ata_ix])
                        
                    return from_ata, to_ata
                    
                from_ata, to_ata = await self.with_retry(_setup_accounts)
                
                # Execute transfer with retry
                tx_sig = await self.with_retry(
                    token_client.transfer,
                    source=from_ata,
                    dest=to_ata,
                    owner=self.keypair.public_key,
                    amount=int(amount * 10**token_client.decimals)
                )
                
                return f"Token transfer successful: {tx_sig}"
                
            elif action == "balance":
                ata = get_associated_token_address(
                    self.keypair.public_key,
                    token_address
                )
                balance = await token_client.get_balance(ata)
                return f"Token balance: {balance / 10**token_client.decimals}"
                
        except ValueError as e:
            return f"Invalid input: {str(e)}"
        except TransactionError as e:
            return f"Transaction failed: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
            
    async def execute_swap(
        self,
        dex: str,
        token_in: str,
        token_out: str,
        amount: float,
        slippage: float = 0.01
    ) -> str:
        """Execute a swap on specified DEX."""
        try:
            # Get DEX program ID
            dex_program_id = getattr(SolanaConfig, f"{dex.upper()}_SWAP")
            
            # Get token addresses
            token_in_address = getattr(SolanaConfig, token_in.upper(), token_in)
            token_out_address = getattr(SolanaConfig, token_out.upper(), token_out)
            
            # Build swap instruction based on DEX
            if dex == "raydium":
                swap_ix = await self._build_raydium_swap_ix(
                    token_in_address,
                    token_out_address,
                    amount,
                    slippage
                )
            elif dex == "orca":
                swap_ix = await self._build_orca_swap_ix(
                    token_in_address,
                    token_out_address,
                    amount,
                    slippage
                )
                
            # Send transaction
            tx_sig = await self._send_transaction([swap_ix])
            return f"Swap successful: {tx_sig}"
            
        except Exception as e:
            return f"Swap failed: {str(e)}"
            
    async def handle_nft_action(
        self,
        action: str,
        *args
    ) -> str:
        """Handle NFT operations."""
        try:
            if action == "mint":
                candy_machine_id = args[0]
                
                # Build mint instruction
                mint_ix = await self._build_candy_machine_mint_ix(
                    candy_machine_id
                )
                
                # Send transaction
                tx_sig = await self._send_transaction([mint_ix])
                return f"NFT minted: {tx_sig}"
                
            elif action == "transfer":
                mint_address = args[0]
                to_address = args[1]
                
                # Get token client for NFT
                nft_token = Token(
                    self.client,
                    mint_address,
                    SolanaConfig.TOKEN_PROGRAM_ID,
                    self.keypair
                )
                
                # Transfer NFT
                tx_sig = await nft_token.transfer(
                    source=self.keypair.public_key,
                    dest=to_address,
                    owner=self.keypair.public_key,
                    amount=1
                )
                
                return f"NFT transferred: {tx_sig}"
                
        except Exception as e:
            return f"NFT action failed: {str(e)}"
            
    async def with_retry(
        self,
        operation: Callable[..., T],
        *args,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> T:
        """Execute an operation with retry mechanism."""
        config = retry_config or self.retry_config
        start_time = datetime.now()
        last_error = None
        attempt = 0
        
        while attempt < config.max_attempts:
            try:
                if (datetime.now() - start_time).total_seconds() > config.timeout:
                    raise TimeoutError("Operation timed out")
                    
                return await operation(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                if attempt >= config.max_attempts:
                    break
                    
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                jitter_amount = delay * config.jitter
                actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
                
                await asyncio.sleep(actual_delay)
                
        error_msg = f"Operation failed after {attempt} attempts"
        raise last_error

    async def verify_transaction(
        self,
        signature: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> bool:
        """Verify transaction confirmation."""
        for attempt in range(max_retries):
            try:
                status = await self.client.get_transaction(
                    signature,
                    commitment=Commitment("finalized")
                )
                if status["result"]:
                    if status["result"]["meta"]["err"]:
                        raise TransactionError(
                            f"Transaction failed: {status['result']['meta']['err']}",
                            signature
                        )
                    return True
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise TransactionError(f"Failed to verify transaction: {str(e)}", signature)
                    
            await asyncio.sleep(retry_delay)
            
        return False

    async def _send_transaction(
        self,
        instructions: List[TransactionInstruction],
        signers: Optional[List[Keypair]] = None
    ) -> str:
        """Enhanced helper to send a transaction with retries and verification."""
        async def _execute_tx():
            tx = Transaction()
            
            # Add instructions
            for ix in instructions:
                tx.add(ix)
                
            try:
                # Get recent blockhash with retry
                blockhash_response = await self.with_retry(
                    self.client.get_recent_blockhash
                )
                tx.recent_blockhash = blockhash_response["result"]["value"]["blockhash"]
                
                # Sign transaction
                signers = signers or [self.keypair]
                tx.sign(*signers)
                
                # Send transaction with retry
                tx_response = await self.with_retry(
                    self.client.send_transaction,
                    tx,
                    *signers,
                    opts=TxOpts(
                        skip_preflight=True,
                        preflight_commitment=Commitment("finalized")
                    )
                )
                
                signature = tx_response["result"]
                
                # Verify transaction
                if not await self.verify_transaction(signature):
                    raise TransactionError("Transaction verification failed", signature)
                    
                return signature
                
            except Exception as e:
                if isinstance(e, TransactionError):
                    raise e
                raise TransactionError(f"Transaction failed: {str(e)}")
                
        return await self.with_retry(_execute_tx)

    async def simulate_swap(
        self,
        input_token: str,
        output_token: str,
        amount: float,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """Simulate a token swap before execution."""
        try:
            # Get token accounts
            input_ata = await self._get_or_create_ata(input_token)
            output_ata = await self._get_or_create_ata(output_token)
            
            # Calculate expected output
            quote = await self._get_swap_quote(
                input_token,
                output_token,
                amount
            )
            
            # Simulate transaction
            simulation = await self.client.simulate_transaction(
                self._build_swap_transaction(
                    input_ata,
                    output_ata,
                    amount,
                    quote
                )
            )
            
            return {
                "expected_output": quote,
                "minimum_output": quote * (1 - slippage),
                "estimated_fee": simulation.value.fee,
                "success": simulation.value.err is None
            }
        except Exception as e:
            raise ValueError(f"Swap simulation failed: {str(e)}") 