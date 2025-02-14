from typing import Optional, Dict, Any, List
from discord import Client, Intents, Message, TextChannel, Member
from langchain.tools import BaseTool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.callbacks import AsyncCallbackManager
from ..base import SwarmBaseTool
from .base import BaseSocialTool, SocialAuthConfig
import time
import asyncio

class DiscordAuthConfig(SocialAuthConfig):
    """Discord-specific authentication configuration."""
    bot_token: str
    guild_ids: List[str]
    moderator_roles: List[str] = ["moderator", "admin"]
    auto_moderation: bool = True
    message_cache_size: int = 1000

class DiscordTool(BaseSocialTool):
    """Enhanced Discord tool with real-time analysis and moderation."""
    
    name: str = "discord"
    description: str = "Advanced Discord operations with AI-powered features"
    
    def __init__(
        self,
        auth_config: DiscordAuthConfig,
        llm: Optional[Any] = None,
        callback_manager: Optional[AsyncCallbackManager] = None
    ):
        super().__init__(auth_config, llm, callback_manager)
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        self.client = Client(intents=intents)
        self.auth_config = auth_config
        self.message_cache = {}
        self._setup_discord_chains()
        self._setup_event_handlers()
        
    def _setup_discord_chains(self):
        """Setup Discord-specific LangChain chains."""
        if not self.llm:
            return
            
        # Content moderation chain
        moderation_template = """
        Analyze this Discord message for moderation:
        Channel: {channel}
        Author: {author}
        Message: {content}
        Previous context: {context}
        Server rules: {rules}
        
        Evaluate:
        1. Rule violations
        2. Toxicity level (0-10)
        3. Required actions
        4. Recommended response
        
        Analysis:
        """
        
        self.moderation_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["channel", "author", "content", "context", "rules"],
                template=moderation_template
            ),
            memory=self.memory,
            callback_manager=self.callback_manager
        )
        
        # Conversation analysis chain
        conversation_template = """
        Analyze this Discord conversation:
        Channel: {channel}
        Messages: {messages}
        Participants: {participants}
        
        Provide:
        1. Main topics/themes
        2. Sentiment analysis
        3. User engagement levels
        4. Potential action items
        5. Recommended responses
        
        Analysis:
        """
        
        self.conversation_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["channel", "messages", "participants"],
                template=conversation_template
            ),
            callback_manager=self.callback_manager
        )
        
    def _setup_event_handlers(self):
        @self.client.event
        async def on_ready():
            print(f"Discord bot logged in as {self.client.user}")
            
        @self.client.event
        async def on_message(message: Message):
            if message.author == self.client.user:
                return
                
            # Update message cache
            channel_id = str(message.channel.id)
            if channel_id not in self.message_cache:
                self.message_cache[channel_id] = []
            self.message_cache[channel_id].append(message)
            
            # Trim cache if needed
            if len(self.message_cache[channel_id]) > self.auth_config.message_cache_size:
                self.message_cache[channel_id].pop(0)
                
            # Auto-moderation if enabled
            if self.auth_config.auto_moderation:
                await self._moderate_message(message)
                
            # Process commands and analyze context
            await self._process_message(message)
            
    async def _moderate_message(self, message: Message) -> None:
        """Apply AI-powered moderation to a message."""
        try:
            context = self._get_conversation_context(message.channel.id)
            rules = await self._get_server_rules(message.guild.id)
            
            analysis = await self.moderation_chain.arun({
                "channel": message.channel.name,
                "author": message.author.name,
                "content": message.content,
                "context": context,
                "rules": rules
            })
            
            moderation_result = self._parse_moderation_result(analysis)
            
            if moderation_result["toxicity_level"] > 7:
                await message.delete()
                await message.channel.send(
                    f"Message removed due to content violation. "
                    f"Reason: {moderation_result['violations']}"
                )
            elif moderation_result["toxicity_level"] > 4:
                await message.add_reaction("⚠️")
                await self._notify_moderators(message, moderation_result)
                
        except Exception as e:
            print(f"Moderation error: {str(e)}")
            
    async def _analyze_conversation(
        self,
        channel_id: str,
        duration: int = 3600
    ) -> Dict:
        """Analyze recent conversation in a channel."""
        try:
            messages = self.message_cache.get(channel_id, [])
            if not messages:
                return "No messages to analyze"
                
            participants = set(msg.author.name for msg in messages)
            
            analysis = await self.conversation_chain.arun({
                "channel": messages[0].channel.name,
                "messages": [
                    {
                        "author": msg.author.name,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    }
                    for msg in messages
                ],
                "participants": list(participants)
            })
            
            return self._parse_conversation_analysis(analysis)
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"
            
    async def _get_server_rules(self, guild_id: str) -> List[str]:
        """Fetch server rules."""
        guild = self.client.get_guild(int(guild_id))
        rules_channel = discord.utils.get(guild.channels, name="rules")
        if not rules_channel:
            return ["No explicit rules found"]
            
        rules = []
        async for message in rules_channel.history(limit=100):
            if message.author == guild.owner:
                rules.extend(message.content.split("\n"))
        return rules
        
    def _parse_moderation_result(self, analysis: str) -> Dict:
        """Parse moderation chain output."""
        # Implement parsing logic
        pass
        
    def _parse_conversation_analysis(self, analysis: str) -> Dict:
        """Parse conversation analysis chain output."""
        # Implement parsing logic
        pass
        
    async def _notify_moderators(
        self,
        message: Message,
        moderation_result: Dict
    ) -> None:
        """Notify moderators about potential violations."""
        mod_channel = discord.utils.get(
            message.guild.channels,
            name="mod-logs"
        )
        if mod_channel:
            await mod_channel.send(
                f"⚠️ Potential content violation in {message.channel.mention}\n"
                f"Author: {message.author.mention}\n"
                f"Content: {message.content}\n"
                f"Analysis: {moderation_result['recommended_action']}"
            )

    async def _arun(self, command: str) -> str:
        """Execute Discord operations."""
        try:
            cmd_parts = command.split(" ", 2)
            action = cmd_parts[0]
            
            if action == "send":
                channel_id = int(cmd_parts[1])
                content = cmd_parts[2]
                return await self.send_message(channel_id, content)
                
            elif action == "monitor":
                channel_id = int(cmd_parts[1])
                keywords = cmd_parts[2].split(",")
                return await self.monitor_channel(channel_id, keywords)
                
            elif action == "react":
                message_id = int(cmd_parts[1])
                emoji = cmd_parts[2]
                return await self.add_reaction(message_id, emoji)
                
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def send_message(
        self,
        channel_id: int,
        content: str,
        embed: Optional[Dict] = None
    ) -> str:
        """Send a message to a Discord channel."""
        channel = self.client.get_channel(channel_id)
        if not channel:
            return "Channel not found"
            
        message = await channel.send(content=content, embed=embed)
        return f"Message sent: {message.id}"
        
    async def monitor_channel(
        self,
        channel_id: int,
        keywords: List[str],
        duration: int = 3600
    ) -> str:
        """Monitor a channel for specific keywords."""
        channel = self.client.get_channel(channel_id)
        if not channel:
            return "Channel not found"
            
        async for message in channel.history(limit=100):
            if any(keyword.lower() in message.content.lower() for keyword in keywords):
                await self._handle_keyword_match(message, keywords)
                
        return "Monitoring complete" 