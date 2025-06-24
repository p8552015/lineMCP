from typing import Any


def get_mcp_manifest() -> dict[str, Any]:
    """
    Returns the MCP tools manifest for Context7 documentation queries
    and PostgreSQL database operations.
    This defines the available tools that can be called via OpenAI's function calling.
    """
    return {
        "search_docs": {
            "description": (
                "Search for up-to-date documentation and code examples using Context7"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query for documentation (e.g., 'Next.js app router', "
                            "'React hooks', 'Python FastAPI')"
                        ),
                    },
                    "framework": {
                        "type": "string",
                        "description": (
                            "Optional framework or technology to focus on "
                            "(e.g., 'react', 'nextjs', 'python', 'fastapi')"
                        ),
                        "default": "",
                    },
                    "language": {
                        "type": "string",
                        "description": (
                            "Programming language to focus on "
                            "(e.g., 'javascript', 'python', 'typescript')"
                        ),
                        "default": "",
                    },
                },
                "required": ["query"],
            },
        },
        "get_code_examples": {
            "description": "Get specific code examples for a given technology or concept",
            "parameters": {
                "type": "object",
                "properties": {
                    "technology": {
                        "type": "string",
                        "description": "Technology or framework name (e.g., 'React', 'FastAPI', 'Next.js')",
                    },
                    "concept": {
                        "type": "string",
                        "description": "Specific concept or feature (e.g., 'hooks', 'routing', 'authentication')",
                    },
                    "use_case": {
                        "type": "string",
                        "description": "Specific use case or pattern needed",
                        "default": "",
                    },
                },
                "required": ["technology", "concept"],
            },
        },
        "get_api_reference": {
            "description": "Get API reference documentation for specific functions or methods",
            "parameters": {
                "type": "object",
                "properties": {
                    "library": {
                        "type": "string",
                        "description": "Library or framework name",
                    },
                    "api_name": {
                        "type": "string",
                        "description": "API method or function name",
                    },
                    "version": {
                        "type": "string",
                        "description": "Specific version (optional)",
                        "default": "latest",
                    },
                },
                "required": ["library", "api_name"],
            },
        },
        "get_best_practices": {
            "description": "Get current best practices and patterns for a technology",
            "parameters": {
                "type": "object",
                "properties": {
                    "technology": {
                        "type": "string",
                        "description": "Technology or framework name",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Specific topic (e.g., 'security', 'performance', 'testing')",
                    },
                },
                "required": ["technology", "topic"],
            },
        },
        # PostgreSQL Database Tools
        "execute_query": {
            "description": "Execute a read-only SQL query against the PostgreSQL database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (read-only operations only)",
                    }
                },
                "required": ["query"],
            },
        },
        "describe_table": {
            "description": "Get schema information for a specific table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe",
                    }
                },
                "required": ["table_name"],
            },
        },
        "list_tables": {
            "description": "List all tables in the database",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        "get_table_sample": {
            "description": "Get sample data from a table (first 10 rows)",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to sample",
                    }
                },
                "required": ["table_name"],
            },
        },
    }
