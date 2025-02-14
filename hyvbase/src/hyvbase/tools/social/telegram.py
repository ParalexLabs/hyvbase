from typing import Optional, Dict, Any, List, Set
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ..base import SwarmBaseTool
from .base import BaseSocialTool, SocialAuthConfig
from langchain_core.callbacks import AsyncCallbackManager
import json
import os

class TelegramAuthConfig(SocialAuthConfig):
    """Telegram-specific authentication configuration."""
    bot_token: str
    allowed_chats: Set[str] = set()  # Changed to Set for unique chat IDs
    chat_store_path: str = "telegram_chats.json"

class TelegramTool(BaseSocialTool):
    """Tool for Telegram interactions."""
    
    name: str = "telegram"
    description: str = "Interact with Telegram chats, send messages, and handle commands"
    auth_config: TelegramAuthConfig
    
    # Declare bot and app as fields
    bot: Optional[Bot] = None
    app: Any = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        token: str,
        app: Optional[Any] = None,
        llm: Optional[Any] = None,
        callback_manager: Optional[AsyncCallbackManager] = None
    ):
        # Initialize auth config first
        auth_config = TelegramAuthConfig(bot_token=token)
        callback_manager = callback_manager or AsyncCallbackManager([])
        
        # Call parent's init
        super().__init__(auth_config=auth_config, llm=llm, callback_manager=callback_manager)
        
        # Use existing application or create new one
        self.app = app or Application.builder().token(token).build()
        self.bot = self.app.bot
        
        # Load existing chats
        self._load_chats()
        
        # Setup handlers
        self._setup_handlers()
    
    def _load_chats(self):
        """Load saved chat IDs from file."""
        try:
            if os.path.exists(self.auth_config.chat_store_path):
                with open(self.auth_config.chat_store_path, 'r') as f:
                    chats = json.load(f)
                    self.auth_config.allowed_chats = set(chats)
        except Exception as e:
            print(f"Error loading chats: {e}")
            self.auth_config.allowed_chats = set()
    
    def _save_chats(self):
        """Save chat IDs to file."""
        try:
            with open(self.auth_config.chat_store_path, 'w') as f:
                json.dump(list(self.auth_config.allowed_chats), f)
        except Exception as e:
            print(f"Error saving chats: {e}")
    
    def _add_chat(self, chat_id: str):
        """Add a chat ID to allowed chats."""
        self.auth_config.allowed_chats.add(str(chat_id))
        self._save_chats()
        
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = str(update.effective_chat.id)
        self._add_chat(chat_id)
        await update.message.reply_text(
            "Hello! I'm your SwarmBase bot. You've been registered for notifications!"
        )
        
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "Available commands:\n"
            "/start - Start receiving notifications\n"
            "/help - Show this help message\n"
            "/status - Show your chat ID and registration status"
        )
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        chat_id = str(update.effective_chat.id)
        status = "registered" if chat_id in self.auth_config.allowed_chats else "not registered"
        await update.message.reply_text(
            f"Your chat ID: {chat_id}\n"
            f"Status: {status}\n"
            f"Total registered chats: {len(self.auth_config.allowed_chats)}"
        )
        
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages."""
        chat_id = str(update.effective_chat.id)
        if chat_id not in self.auth_config.allowed_chats:
            self._add_chat(chat_id)
        await update.message.reply_text("Message received! You're registered for notifications.")
        
    def _setup_handlers(self):
        """Set up message and command handlers."""
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("help", self._help_command))
        self.app.add_handler(CommandHandler("status", self._status_command))
        self.app.add_handler(MessageHandler(filters.TEXT, self._handle_message))
        
    async def broadcast_message(self, text: str) -> str:
        """Send a message to all registered chats."""
        results = []
        for chat_id in self.auth_config.allowed_chats:
            try:
                result = await self.send_message(chat_id, text)
                results.append(result)
            except Exception as e:
                results.append(f"Failed for {chat_id}: {str(e)}")
        return "\n".join(results)

    async def _arun(self, command: str) -> str:
        """Execute Telegram operations."""
        try:
            cmd_parts = command.split(" ", 1)
            action = cmd_parts[0]
            
            if action == "broadcast":
                message = cmd_parts[1]
                return await self.broadcast_message(message)
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = None
    ) -> str:
        """Send a message to a specific chat."""
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return f"Message sent: {message.message_id}"
        except Exception as e:
            return f"Failed to send message: {str(e)}"

    async def run(self):
        """Run the bot to handle incoming messages."""
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.run_polling()
        finally:
            await self.app.stop()
            await self.app.shutdown() 