from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class AgentPersonality(BaseModel):
    """
    A flexible class for creating custom agent personalities.
    Users can define their own agent's characteristics and behavior.
    """
    
    name: str = Field(..., description="The name of the agent")
    role: str = Field(..., description="The agent's role or profession")
    traits: List[str] = Field(default_factory=list, description="Personality traits of the agent")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")
    background: str = Field("", description="Background story or experience")
    speaking_style: str = Field("", description="How the agent communicates")
    language_tone: str = Field("professional", description="Tone of communication")
    custom_attributes: Dict = Field(default_factory=dict, description="Additional custom attributes")
    
    def get_system_prompt(self) -> str:
        """Generate a system prompt based on the personality attributes"""
        prompt = f"""You are {self.name}, {self.role}.

{f'Background: {self.background}' if self.background else ''}

Your expertise includes: {', '.join(self.expertise)}
Your personality traits are: {', '.join(self.traits)}
Communication style: {self.speaking_style}
Tone: {self.language_tone}

Additional characteristics:
{self._format_custom_attributes()}

Maintain this personality while assisting users."""

        return prompt.strip()
    
    def _format_custom_attributes(self) -> str:
        """Format custom attributes for the prompt"""
        if not self.custom_attributes:
            return ""
        
        return "\n".join(f"- {k}: {v}" for k, v in self.custom_attributes.items())
    
    def add_trait(self, trait: str):
        """Add a new personality trait"""
        if trait not in self.traits:
            self.traits.append(trait)
    
    def add_expertise(self, expertise: str):
        """Add a new area of expertise"""
        if expertise not in self.expertise:
            self.expertise.append(expertise)
    
    def update_custom_attributes(self, attributes: Dict):
        """Update or add custom attributes"""
        self.custom_attributes.update(attributes) 