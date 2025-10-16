"""
Tool Synchronizer for The Librarian

Handles dynamic synchronization of OpenAI tools with Letta tools API.
"""

import logging
from typing import List, Dict, Any, Optional
from letta_client import Letta

logger = logging.getLogger(__name__)


class ToolSynchronizer:
    """Synchronizes OpenAI tool definitions with Letta tools"""
    
    def __init__(self, letta_client: Letta):
        self.letta_client = letta_client
        self.synced_tools = {}  # Cache of synced tools
    
    async def sync_tools(self, agent_id: str, openai_tools: List[Dict[str, Any]]) -> bool:
        """
        Synchronize OpenAI tool definitions with Letta agent
        
        Args:
            agent_id: Letta agent ID
            openai_tools: List of OpenAI tool definitions
            
        Returns:
            True if synchronization successful
        """
        try:
            for tool in openai_tools:
                if tool.get("type") == "function":
                    await self._sync_function_tool(agent_id, tool["function"])
            
            logger.info(f"Successfully synchronized {len(openai_tools)} tools for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error synchronizing tools: {str(e)}")
            return False
    
    async def _sync_function_tool(self, agent_id: str, function_def: Dict[str, Any]) -> None:
        """Sync a single function tool"""
        tool_name = function_def["name"]
        
        try:
            # Check if tool already exists
            existing_tools = self.letta_client.tools.list()
            tool_exists = any(tool.name == tool_name for tool in existing_tools)
            
            if not tool_exists:
                # Create new tool
                await self.letta_client.tools.create(
                    name=tool_name,
                    description=function_def.get("description", ""),
                    parameters=function_def.get("parameters", {})
                )
                logger.info(f"Created new tool: {tool_name}")
            
            # Attach tool to agent
            await self.letta_client.agents.tools.attach(agent_id, tool_name)
            logger.info(f"Attached tool {tool_name} to agent {agent_id}")
            
            # Cache the synced tool
            self.synced_tools[tool_name] = {
                "name": tool_name,
                "description": function_def.get("description", ""),
                "parameters": function_def.get("parameters", {}),
                "agent_id": agent_id
            }
            
        except Exception as e:
            logger.error(f"Error syncing function tool {tool_name}: {str(e)}")
            raise
    
    async def detach_tools(self, agent_id: str, tool_names: List[str]) -> None:
        """Detach tools from agent"""
        for tool_name in tool_names:
            try:
                await self.letta_client.agents.tools.detach(agent_id, tool_name)
                logger.info(f"Detached tool {tool_name} from agent {agent_id}")
            except Exception as e:
                logger.error(f"Error detaching tool {tool_name}: {str(e)}")
    
    def get_synced_tools(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get list of synced tools for an agent"""
        return [
            tool for tool in self.synced_tools.values() 
            if tool["agent_id"] == agent_id
        ]
    
    def clear_cache(self) -> None:
        """Clear the tool cache"""
        self.synced_tools.clear()
        logger.info("Tool cache cleared")
