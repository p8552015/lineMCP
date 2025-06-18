import re
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Command:
    name: str
    args: List[str]


def parse_command(message: str) -> Optional[Command]:
    message = message.strip()
    
    if not message.startswith("/"):
        return None
    
    parts = message.split()
    command_name = parts[0][1:].lower()
    
    supported_commands = [
        "search", "docs", "examples", "api", "best", "help", 
        "sql", "tables", "describe", "sample", "status", "trend", "suggest_fix",
        "tools", "list", "create", "read", "write", "chart", "pivot", "format", "info",
        "task"
    ]
    
    if command_name not in supported_commands:
        return None
    
    args = parts[1:] if len(parts) > 1 else []
    
    return Command(name=command_name, args=args)