from typing import Optional, Dict, Any, List
from linkedin_api import Linkedin
from ..base import SwarmBaseTool

class LinkedInTool(SwarmBaseTool):
    """Tool for LinkedIn interactions based on LangChain patterns."""
    
    name: str = "linkedin"
    description: str = "Search profiles, post updates, and interact with LinkedIn"
    
    def __init__(self, username: str, password: str):
        super().__init__()
        self.api = Linkedin(username, password)
        
    async def _arun(self, command: str) -> str:
        """Execute LinkedIn operations."""
        try:
            cmd_parts = command.split(" ", 2)
            action = cmd_parts[0]
            
            if action == "search_people":
                query = cmd_parts[1]
                return await self.search_people(query)
                
            elif action == "post_update":
                content = cmd_parts[1]
                return await self.post_update(content)
                
            elif action == "get_profile":
                profile_id = cmd_parts[1]
                return await self.get_profile(profile_id)
                
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    async def search_people(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search for people on LinkedIn."""
        try:
            results = self.api.search_people(
                keywords=query,
                limit=limit
            )
            return [
                {
                    'name': person.get('name'),
                    'headline': person.get('headline'),
                    'location': person.get('location'),
                    'profile_id': person.get('public_id')
                }
                for person in results
            ]
        except Exception as e:
            return f"Search failed: {str(e)}"

    async def post_update(
        self,
        text: str,
        visibility: str = "public"
    ) -> str:
        """Post an update on LinkedIn."""
        try:
            response = self.api.post(
                text=text,
                visibility=visibility
            )
            return f"Update posted: {response['id']}"
        except Exception as e:
            return f"Failed to post update: {str(e)}"

    async def get_profile(self, profile_id: str) -> Dict:
        """Get detailed profile information."""
        try:
            profile = self.api.get_profile(profile_id)
            return {
                'name': profile.get('name'),
                'headline': profile.get('headline'),
                'summary': profile.get('summary'),
                'experience': profile.get('experience'),
                'education': profile.get('education')
            }
        except Exception as e:
            return f"Failed to get profile: {str(e)}" 