"""
Centralized logging utilities for the synthea chatbot backend.
"""
import os
import logging

# Configure logger
logger = logging.getLogger("synthea_agent")
logger.setLevel(logging.DEBUG)
logger.propagate = False

# Check individual debug logging flags
_agent_debug = os.getenv("AGENT_DEBUG_LOGGING", "false").lower() == "true"
_tool_debug = os.getenv("TOOL_DEBUG_LOGGING", "false").lower() == "true"
_db_debug = os.getenv("DATABASE_DEBUG_LOGGING", "false").lower() == "true"
_app_debug = os.getenv("APP_DEBUG_LOGGING", "false").lower() == "true"

# Enable logging if any debug flag is set
if _agent_debug or _tool_debug or _db_debug or _app_debug:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
    logger.addHandler(handler)
    enabled_flags = []
    if _agent_debug: enabled_flags.append("AGENT")
    if _tool_debug: enabled_flags.append("TOOL")
    if _db_debug: enabled_flags.append("DATABASE")
    if _app_debug: enabled_flags.append("APP")
    print(f"[LOGGING] Debug logging enabled for: {', '.join(enabled_flags)}")
else:
    logger.setLevel(logging.WARNING)
    print(f"[LOGGING] Debug logging disabled")


# Centralized logging function with conditional logging based on source type
def log(source: str, message: str, name: str = None, level: str = "debug"):
    """
    Centralized logging function that checks environment variables before logging.

    Args:
        source: One of "APP", "DATABASE", "TOOL", "AGENT"
        message: The message to log
        name: Optional name to append to source prefix
              - For AGENT: "MAIN" or "CYPHER" (becomes "AGENT MAIN" or "AGENT CYPHER")
              - For TOOL: tool name (e.g., "get_patient_procedures")
        level: Log level - "debug", "info", "warning", "error" (default: "debug")
    """
    # Map source to environment variable check
    source_upper = source.upper()

    if source_upper == "AGENT":
        if not _agent_debug:
            return
        # For AGENT, name should be "MAIN" or "CYPHER"
        prefix = f"AGENT {name}" if name else "AGENT"
    elif source_upper == "TOOL":
        if not _tool_debug:
            return
        prefix = f"TOOL {name}" if name else "TOOL"
    elif source_upper == "DATABASE":
        if not _db_debug:
            return
        prefix = "DATABASE"
    elif source_upper == "APP":
        if not _app_debug:
            return
        prefix = "APP"
    else:
        # Unknown source, skip logging
        return

    # Format the full message with prefix
    full_message = f"{prefix}: {message}"

    # Log at the appropriate level
    if level == "error":
        logger.error(full_message)
    elif level == "warning":
        logger.warning(full_message)
    elif level == "info":
        logger.info(full_message)
    else:
        logger.debug(full_message)
