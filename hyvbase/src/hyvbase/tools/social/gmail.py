from typing import Optional, Dict, Any, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from ..base import SwarmBaseTool

class GmailTool(SwarmBaseTool):
    """Tool for Gmail interactions based on LangChain's GmailAPIWrapper."""
    
    name: str = "gmail"
    description: str = "Send emails, search messages, and manage Gmail inbox"
    
    def __init__(self, credentials: Credentials):
        super().__init__()
        self.service = build('gmail', 'v1', credentials=credentials)
        
    async def _arun(self, command: str) -> str:
        """Execute Gmail operations."""
        try:
            cmd_parts = command.split(" ", 2)
            action = cmd_parts[0]
            
            if action == "send":
                to, subject_and_body = cmd_parts[1], cmd_parts[2].split("|")
                return await self.send_email(to, subject_and_body[0], subject_and_body[1])
                
            elif action == "search":
                query = cmd_parts[1]
                return await self.search_emails(query)
                
            elif action == "read":
                message_id = cmd_parts[1]
                return await self.read_email(message_id)
                
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> str:
        """Send an email using Gmail."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
                
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return f"Email sent: {message['id']}"
        except Exception as e:
            return f"Failed to send email: {str(e)}"

    async def search_emails(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """Search emails in Gmail."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = []
            for msg in results.get('messages', []):
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                messages.append({
                    'id': message['id'],
                    'subject': self._get_header(message, 'Subject'),
                    'from': self._get_header(message, 'From'),
                    'date': self._get_header(message, 'Date')
                })
            
            return messages
        except Exception as e:
            return f"Search failed: {str(e)}" 