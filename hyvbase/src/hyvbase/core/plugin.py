"""Plugin Architecture for HyvBase

Dynamic plugin loading and management system that allows for extensible
tool integration and third-party plugin support.
"""

import asyncio
import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from pathlib import Path
import uuid

from .types import AgentResponse, ToolCapability, ToolProtocol
from .config import HyvBaseConfig

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: str
    capabilities: List[ToolCapability]
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)


class BaseTool(ABC):
    """Base class for all HyvBase tools"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.id = str(uuid.uuid4())
        self.name = self.__class__.__name__
        self.initialized = False
        
    @abstractmethod
    async def execute(self, command: str, **kwargs) -> AgentResponse:
        """Execute a command with this tool"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ToolCapability]:
        """Get tool capabilities"""
        pass
    
    @abstractmethod
    def validate_command(self, command: str) -> bool:
        """Validate if command is supported by this tool"""
        pass
    
    async def initialize(self) -> None:
        """Initialize the tool"""
        self.initialized = True
        logger.info(f"Tool {self.name} initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the tool"""
        self.initialized = False
        logger.info(f"Tool {self.name} shutdown")
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description=self.__doc__ or "No description provided",
            author="HyvBase",
            capabilities=self.get_capabilities()
        )


class PluginRegistry:
    """Registry for managing plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Type[BaseTool]] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        
    def register(self, plugin_class: Type[BaseTool]) -> None:
        """Register a plugin class"""
        # Create temporary instance to get metadata
        temp_instance = plugin_class({})
        metadata = temp_instance.get_metadata()
        
        self.plugins[metadata.name] = plugin_class
        self.metadata[metadata.name] = metadata
        
        logger.info(f"Registered plugin: {metadata.name}")
    
    def get_plugin(self, name: str) -> Optional[Type[BaseTool]]:
        """Get plugin class by name"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, Type[BaseTool]]:
        """Get all registered plugins"""
        return self.plugins.copy()
    
    def get_plugins_by_capability(self, capability: ToolCapability) -> List[Type[BaseTool]]:
        """Get plugins by capability"""
        result = []
        for name, metadata in self.metadata.items():
            if capability in metadata.capabilities:
                plugin_class = self.plugins.get(name)
                if plugin_class:
                    result.append(plugin_class)
        return result
    
    def search_plugins(self, query: str) -> List[Type[BaseTool]]:
        """Search plugins by name, description, or tags"""
        query = query.lower()
        result = []
        
        for name, metadata in self.metadata.items():
            if (query in name.lower() or 
                query in metadata.description.lower() or 
                any(query in tag.lower() for tag in metadata.tags)):
                plugin_class = self.plugins.get(name)
                if plugin_class:
                    result.append(plugin_class)
        
        return result


class PluginManager:
    """Plugin manager for dynamic loading and management"""
    
    def __init__(self, config: HyvBaseConfig):
        self.config = config
        self.registry = PluginRegistry()
        self.loaded_tools: Dict[str, BaseTool] = {}
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize plugin manager"""
        if self.initialized:
            return
        
        try:
            # Load built-in plugins
            await self._load_builtin_plugins()
            
            # Load external plugins
            await self._load_external_plugins()
            
            self.initialized = True
            logger.info("Plugin manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize plugin manager: {e}")
            raise
    
    async def _load_builtin_plugins(self) -> None:
        """Load built-in plugins"""
        # Import and register built-in tools
        builtin_modules = [
            "hyvbase.tools.crypto.starknet",
            "hyvbase.tools.crypto.avnu_dex",
            "hyvbase.tools.social.twitter",
            "hyvbase.tools.social.telegram",
            "hyvbase.tools.social.discord",
            "hyvbase.tools.analytics.market_data",
            "hyvbase.tools.web.scraper",
        ]
        
        for module_name in builtin_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Look for tool classes in module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseTool) and 
                        obj != BaseTool):
                        self.registry.register(obj)
                        
            except ImportError as e:
                logger.warning(f"Could not load built-in plugin {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error loading built-in plugin {module_name}: {e}")
    
    async def _load_external_plugins(self) -> None:
        """Load external plugins from plugin directory"""
        plugin_dir = Path.home() / ".hyvbase" / "plugins"
        
        if not plugin_dir.exists():
            plugin_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Load Python files as plugins
        for plugin_file in plugin_dir.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for tool classes in module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseTool) and 
                        obj != BaseTool):
                        self.registry.register(obj)
                        
            except Exception as e:
                logger.error(f"Error loading external plugin {plugin_file}: {e}")
    
    async def load_tool(self, tool_name: str, tool_config: Optional[Dict[str, Any]] = None) -> BaseTool:
        """Load and initialize a tool"""
        if tool_name in self.loaded_tools:
            return self.loaded_tools[tool_name]
        
        # Get plugin class
        plugin_class = self.registry.get_plugin(tool_name)
        if not plugin_class:
            raise ValueError(f"Plugin {tool_name} not found")
        
        # Create and initialize tool instance
        tool_instance = plugin_class(tool_config)
        await tool_instance.initialize()
        
        # Store loaded tool
        self.loaded_tools[tool_name] = tool_instance
        
        logger.info(f"Loaded tool: {tool_name}")
        return tool_instance
    
    async def unload_tool(self, tool_name: str) -> None:
        """Unload a tool"""
        if tool_name in self.loaded_tools:
            tool = self.loaded_tools[tool_name]
            await tool.shutdown()
            del self.loaded_tools[tool_name]
            logger.info(f"Unloaded tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get loaded tool by name"""
        return self.loaded_tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all loaded tools"""
        return list(self.loaded_tools.values())
    
    def get_tools_by_capability(self, capability: ToolCapability) -> List[BaseTool]:
        """Get tools by capability"""
        result = []
        for tool in self.loaded_tools.values():
            if capability in tool.get_capabilities():
                result.append(tool)
        return result
    
    def get_available_plugins(self) -> Dict[str, PluginMetadata]:
        """Get all available plugins"""
        return self.registry.metadata.copy()
    
    async def install_plugin(self, plugin_source: str) -> None:
        """Install a plugin from source (URL, file, etc.)"""
        # TODO: Implement plugin installation
        raise NotImplementedError("Plugin installation not yet implemented")
    
    async def update_plugin(self, plugin_name: str) -> None:
        """Update a plugin"""
        # TODO: Implement plugin updates
        raise NotImplementedError("Plugin updates not yet implemented")
    
    async def remove_plugin(self, plugin_name: str) -> None:
        """Remove a plugin"""
        # TODO: Implement plugin removal
        raise NotImplementedError("Plugin removal not yet implemented")
    
    async def reload_plugin(self, plugin_name: str) -> None:
        """Reload a plugin"""
        # Unload if loaded
        if plugin_name in self.loaded_tools:
            await self.unload_tool(plugin_name)
        
        # Remove from registry
        if plugin_name in self.registry.plugins:
            del self.registry.plugins[plugin_name]
            del self.registry.metadata[plugin_name]
        
        # Reload
        await self._load_builtin_plugins()
        await self._load_external_plugins()
        
        logger.info(f"Reloaded plugin: {plugin_name}")
    
    def validate_plugin(self, plugin_class: Type[BaseTool]) -> bool:
        """Validate a plugin class"""
        try:
            # Check if it's a subclass of BaseTool
            if not issubclass(plugin_class, BaseTool):
                return False
            
            # Check if required methods are implemented
            required_methods = ['execute', 'get_capabilities', 'validate_command']
            for method_name in required_methods:
                if not hasattr(plugin_class, method_name):
                    return False
                method = getattr(plugin_class, method_name)
                if not callable(method):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating plugin: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown plugin manager"""
        # Shutdown all loaded tools
        for tool_name in list(self.loaded_tools.keys()):
            await self.unload_tool(tool_name)
        
        self.initialized = False
        logger.info("Plugin manager shut down")


# Decorator for registering plugins
def register_plugin(plugin_class: Type[BaseTool]) -> Type[BaseTool]:
    """Decorator to register a plugin"""
    # This would be used with a global registry
    # For now, it's a placeholder
    return plugin_class


# Plugin discovery utilities
def discover_plugins(directory: Path) -> List[Type[BaseTool]]:
    """Discover plugins in a directory"""
    plugins = []
    
    for python_file in directory.glob("**/*.py"):
        try:
            spec = importlib.util.spec_from_file_location(
                python_file.stem, python_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for tool classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseTool) and 
                    obj != BaseTool):
                    plugins.append(obj)
                    
        except Exception as e:
            logger.warning(f"Could not load plugin from {python_file}: {e}")
    
    return plugins


# Built-in tool adapters for existing tools
class LegacyToolAdapter(BaseTool):
    """Adapter for legacy tools to work with new plugin system"""
    
    def __init__(self, legacy_tool: Any, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.legacy_tool = legacy_tool
        self.name = getattr(legacy_tool, 'name', legacy_tool.__class__.__name__)
    
    async def execute(self, command: str, **kwargs) -> AgentResponse:
        """Execute command using legacy tool"""
        try:
            # Try async execution first
            if hasattr(self.legacy_tool, '_arun'):
                result = await self.legacy_tool._arun(command, **kwargs)
            elif hasattr(self.legacy_tool, 'arun'):
                result = await self.legacy_tool.arun(command, **kwargs)
            # Fall back to sync execution
            elif hasattr(self.legacy_tool, '_run'):
                result = self.legacy_tool._run(command, **kwargs)
            elif hasattr(self.legacy_tool, 'run'):
                result = self.legacy_tool.run(command, **kwargs)
            else:
                raise AttributeError("Legacy tool has no run method")
            
            return AgentResponse(
                success=True,
                data=result,
                message=str(result)
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                error=str(e)
            )
    
    def get_capabilities(self) -> List[ToolCapability]:
        """Get capabilities from legacy tool"""
        # Try to infer capabilities from tool name/type
        name_lower = self.name.lower()
        
        capabilities = []
        
        if any(word in name_lower for word in ['starknet', 'ethereum', 'crypto', 'dex', 'swap']):
            capabilities.extend([
                ToolCapability.BLOCKCHAIN_READ,
                ToolCapability.BLOCKCHAIN_WRITE
            ])
        
        if any(word in name_lower for word in ['twitter', 'telegram', 'discord', 'social']):
            capabilities.extend([
                ToolCapability.SOCIAL_READ,
                ToolCapability.SOCIAL_WRITE
            ])
        
        if any(word in name_lower for word in ['market', 'price', 'data']):
            capabilities.append(ToolCapability.MARKET_DATA)
        
        return capabilities or [ToolCapability.AUTOMATION]
    
    def validate_command(self, command: str) -> bool:
        """Basic validation for legacy tools"""
        return bool(command and command.strip())
