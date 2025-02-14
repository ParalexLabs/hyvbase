from typing import Optional, Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langchain.tools import BaseTool
from .base import BaseSocialTool, SocialAuthConfig

class SlackAuthConfig(SocialAuthConfig):
    """Slack-specific authentication configuration."""
    workspace_id: str
    bot_token: str
    user_token: Optional[str] = None
    signing_secret: Optional[str] = None

class SlackTool(BaseSocialTool):
    """Enhanced Slack tool with LangChain integration."""
    
    name: str = "slack"
    description: str = "Interact with Slack workspace using advanced features"
    
    def __init__(self, auth_config: SlackAuthConfig):
        super().__init__(auth_config)
        self.client = WebClient(token=auth_config.bot_token)
        self.user_client = WebClient(token=auth_config.user_token) if auth_config.user_token else None
        self._setup_event_handlers()
        
    async def _arun(self, command: str) -> str:
        """Execute Slack operations with rate limiting."""
        try:
            self._rate_limit()
            return await self._execute_command(command)
        except Exception as e:
            return await self._handle_error(e)
            
    async def _execute_command(self, command: str) -> str:
        """Execute Slack command with enhanced functionality."""
        cmd_parts = command.split(" ", 2)
        action = cmd_parts[0]
        
        actions = {
            "send": self.send_message,
            "search": self.search_messages,
            "react": self.add_reaction,
            "thread": self.create_thread,
            "schedule": self.schedule_message,
            "poll": self.create_poll,
            "remind": self.set_reminder,
            "status": self.update_status,
            "files": self.list_files,
            "upload": self.upload_file
        }
        
        if action not in actions:
            return f"Unknown action: {action}"
            
        return await actions[action](*cmd_parts[1:])
        
    async def create_thread(
        self,
        channel: str,
        parent_ts: str,
        text: str
    ) -> str:
        """Create a thread reply."""
        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                thread_ts=parent_ts,
                text=text
            )
            return f"Thread reply sent: {response['ts']}"
        except SlackApiError as e:
            return f"Failed to create thread: {str(e)}"
            
    async def schedule_message(
        self,
        channel: str,
        text: str,
        post_at: int
    ) -> str:
        """Schedule a message for later."""
        try:
            response = await self.client.chat_scheduleMessage(
                channel=channel,
                text=text,
                post_at=post_at
            )
            return f"Message scheduled: {response['scheduled_message_id']}"
        except SlackApiError as e:
            return f"Failed to schedule message: {str(e)}"
            
    async def create_poll(
        self,
        channel: str,
        question: str,
        options: List[str]
    ) -> str:
        """Create a poll in a channel."""
        try:
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{question}*"}
                }
            ]
            
            for i, option in enumerate(options):
                blocks.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": option},
                    "value": f"option_{i}"
                })
                
            response = await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
            return f"Poll created: {response['ts']}"
        except SlackApiError as e:
            return f"Failed to create poll: {str(e)}"

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None
    ) -> str:
        """Send a message to a Slack channel."""
        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                blocks=blocks
            )
            return f"Message sent: {response['ts']}"
        except SlackApiError as e:
            return f"Failed to send message: {str(e)}"

    async def search_messages(
        self,
        query: str,
        sort: str = "relevant",
        count: int = 20
    ) -> List[Dict]:
        """Search for messages in Slack."""
        try:
            response = await self.client.search_messages(
                query=query,
                sort=sort,
                count=count
            )
            return response['messages']['matches']
        except SlackApiError as e:
            return f"Search failed: {str(e)}"

    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        emoji: str
    ) -> str:
        """Add a reaction to a message."""
        try:
            response = await self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=emoji
            )
            return f"Reaction added: {response['ok']}"
        except SlackApiError as e:
            return f"Failed to add reaction: {str(e)}"

    async def set_reminder(
        self,
        channel: str,
        text: str,
        post_at: int
    ) -> str:
        """Set a reminder for a message."""
        try:
            response = await self.client.reminders_add(
                channel=channel,
                text=text,
                post_at=post_at
            )
            return f"Reminder set: {response['ok']}"
        except SlackApiError as e:
            return f"Failed to set reminder: {str(e)}"

    async def update_status(
        self,
        status: str
    ) -> str:
        """Update the user's Slack status."""
        try:
            response = await self.client.users_profile_set(
                profile=f"status_text={status}"
            )
            return f"Status updated: {response['ok']}"
        except SlackApiError as e:
            return f"Failed to update status: {str(e)}"

    async def list_files(
        self,
        channel: str
    ) -> str:
        """List files in a Slack channel."""
        try:
            response = await self.client.files_list(
                channel=channel
            )
            return f"Files in channel: {response['files']}"
        except SlackApiError as e:
            return f"Failed to list files: {str(e)}"

    async def upload_file(
        self,
        channel: str,
        file_path: str
    ) -> str:
        """Upload a file to a Slack channel."""
        try:
            with open(file_path, 'rb') as f:
                response = await self.client.files_upload(
                    channels=channel,
                    file=f
                )
            return f"File uploaded: {response['file']['name']}"
        except SlackApiError as e:
            return f"Failed to upload file: {str(e)}" 