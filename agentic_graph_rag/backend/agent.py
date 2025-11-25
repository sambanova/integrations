"""
LangGraph agent for querying Synthea Neo4j database with natural language.
"""
import json
import time
from datetime import datetime
from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from llm_factory import create_llm, get_main_agent_model, get_validation_model, get_synthesis_model
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langgraph.types import Command
from neo4j_utils import Neo4jConnection
from cypher_subagent import query_cypher_subgraph
from langsmith.run_helpers import traceable
from logging_utils import log
from pydantic import BaseModel, Field


# Initialize Neo4j connection
neo4j_conn = Neo4jConnection()
neo4j_conn.connect()


# Define tools for the agent
@tool
@traceable(name="get_patient_procedures", run_type="tool", tags=["tool", "patient", "procedures"])
def get_patient_procedures(patient_name: str, limit: int = 30, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Get procedures that have been performed on a patient, sorted by most recent first.

    Note: Returns the actual number of procedures found, up to the limit specified.
    The output will indicate "(showing up to X most recent)" ONLY if the result count equals the limit.
    If fewer results are found, the output will NOT mention the limit.

    Args:
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)
        patient_name: The patient's name (can be first name, last name, or full name like 'John Smith')
        limit: Maximum number of results to return (default: 30). Only increase this if the user explicitly asks for more results.

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    log("TOOL", f"Called with patient_name='{patient_name}', limit={limit}", "get_patient_procedures")

    # Track tool execution latency
    start_time = time.time()

    try:
        results, query, params = neo4j_conn.get_patient_procedures(patient_name, limit=limit)

        if not results:
            log("TOOL", f"No procedures found for '{patient_name}'", "get_patient_procedures")
            output = f"No procedures found for patient '{patient_name}'. The patient may not exist or has no recorded procedures."
        else:
            # Only mention limit if we hit the limit (results count equals limit)
            if len(results) >= limit:
                output = f"Procedures for {results[0]['patient_name']} (showing up to {limit} most recent):\n\n"
            else:
                output = f"Procedures for {results[0]['patient_name']}:\n\n"

            for i, record in enumerate(results, 1):
                output += f"{i}. {record['procedure_description']}\n"
                output += f"   Date: {record['encounter_date']}\n"
                output += f"   Encounter Type: {record['encounter_type']}\n\n"

            log("TOOL", f"Found {len(results)} procedures", "get_patient_procedures")

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "get_patient_procedures",
            "tool_args": {"patient_name": patient_name, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: get_patient_procedures",
            "duration_ms": duration_ms
        }

        # Return Command that updates both messages (for LLM) and executed_queries (for tracking)
        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id)],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )
    except Exception as e:
        log("TOOL", f"Error - {str(e)}", "get_patient_procedures", level="error")
        error_msg = f"Error retrieving procedures: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id)],
                "latency_logs": [{
                    "name": "Tool: get_patient_procedures",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="get_patient_conditions", run_type="tool", tags=["tool", "patient", "conditions"])
def get_patient_conditions(patient_name: str, limit: int = 30, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Get medical conditions/diagnoses for a patient, sorted by most recent first.

    Note: Returns the actual number of conditions found, up to the limit specified.
    The output will indicate "(showing up to X most recent)" ONLY if the result count equals the limit.
    If fewer results are found, the output will NOT mention the limit.

    Args:
        patient_name: The patient's name (can be first name, last name, or full name like 'John Smith')
        limit: Maximum number of results to return (default: 30). Only increase this if the user explicitly asks for more results.
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    # Track tool execution latency
    start_time = time.time()

    try:
        results, query, params = neo4j_conn.get_patient_conditions(patient_name, limit=limit)

        if not results:
            output = f"No conditions found for patient '{patient_name}'. The patient may not exist or has no recorded conditions."
        else:
            # Only mention limit if we hit the limit (results count equals limit)
            if len(results) >= limit:
                output = f"Conditions for {results[0]['patient_name']} (showing up to {limit} most recent):\n\n"
            else:
                output = f"Conditions for {results[0]['patient_name']}:\n\n"

            for i, record in enumerate(results, 1):
                output += f"{i}. {record['condition_description']}\n"
                output += f"   Diagnosed: {record['encounter_date']}\n\n"

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "get_patient_conditions",
            "tool_args": {"patient_name": patient_name, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: get_patient_conditions",
            "duration_ms": duration_ms
        }

        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )
    except Exception as e:
        error_msg = f"Error retrieving conditions: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")],
                "latency_logs": [{
                    "name": "Tool: get_patient_conditions",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="get_patient_medications", run_type="tool", tags=["tool", "patient", "medications"])
def get_patient_medications(patient_name: str, limit: int = 30, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Get medications prescribed to a patient, sorted by most recent first.

    Note: Returns the actual number of medications found, up to the limit specified.
    The output will indicate "(showing up to X most recent)" ONLY if the result count equals the limit.
    If fewer results are found, the output will NOT mention the limit.

    Args:
        patient_name: The patient's name (can be first name, last name, or full name like 'John Smith')
        limit: Maximum number of results to return (default: 30). Only increase this if the user explicitly asks for more results.
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    # Track tool execution latency
    start_time = time.time()

    try:
        results, query, params = neo4j_conn.get_patient_medications(patient_name, limit=limit)

        if not results:
            output = f"No medications found for patient '{patient_name}'. The patient may not exist or has no prescribed medications."
        else:
            # Only mention limit if we hit the limit (results count equals limit)
            if len(results) >= limit:
                output = f"Medications for {results[0]['patient_name']} (showing up to {limit} most recent):\n\n"
                log("TOOL", f"Hit limit: {len(results)} >= {limit}, including limit language", "get_patient_medications")
            else:
                output = f"Medications for {results[0]['patient_name']}:\n\n"
                log("TOOL", f"Under limit: {len(results)} < {limit}, NOT including limit language", "get_patient_medications")

            for i, record in enumerate(results, 1):
                output += f"{i}. {record['medication']}\n"
                output += f"   Prescribed: {record['prescribed_date']}\n\n"

            log("TOOL", f"Tool output starts with: {output[:100]}", "get_patient_medications")

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "get_patient_medications",
            "tool_args": {"patient_name": patient_name, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: get_patient_medications",
            "duration_ms": duration_ms
        }

        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )
    except Exception as e:
        error_msg = f"Error retrieving medications: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")],
                "latency_logs": [{
                    "name": "Tool: get_patient_medications",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="get_patient_encounters", run_type="tool", tags=["tool", "patient", "encounters"])
def get_patient_encounters(patient_name: str, limit: int = 30, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Get healthcare encounters for a patient, sorted by most recent first.

    Note: Returns the actual number of encounters found, up to the limit specified.
    The output will indicate "(showing up to X most recent)" ONLY if the result count equals the limit.
    If fewer results are found, the output will NOT mention the limit.

    Args:
        patient_name: The patient's name (can be first name, last name, or full name like 'John Smith')
        limit: Maximum number of results to return (default: 30). Only increase this if the user explicitly asks for more results.
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    # Track tool execution latency
    start_time = time.time()

    try:
        results, query, params = neo4j_conn.get_patient_encounters(patient_name, limit=limit)

        if not results:
            output = f"No encounters found for patient '{patient_name}'. The patient may not exist."
        else:
            # Only mention limit if we hit the limit (results count equals limit)
            if len(results) >= limit:
                output = f"Encounters for {results[0]['patient_name']} (showing up to {limit} most recent):\n\n"
            else:
                output = f"Encounters for {results[0]['patient_name']}:\n\n"

            for i, record in enumerate(results, 1):
                output += f"{i}. {record['encounter_type']}\n"
                output += f"   Date: {record['encounter_date']}\n"
                output += f"   Type: {', '.join(record['encounter_labels'])}\n\n"

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "get_patient_encounters",
            "tool_args": {"patient_name": patient_name, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: get_patient_encounters",
            "duration_ms": duration_ms
        }

        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )
    except Exception as e:
        error_msg = f"Error retrieving encounters: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")],
                "latency_logs": [{
                    "name": "Tool: get_patient_encounters",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="search_patients", run_type="tool", tags=["tool", "patient", "search"])
def search_patients(search_term: str = None, limit: int = 30, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Search for patients by name, sorted by relevance. Use this when you need to find a patient or list patients.

    Note: Returns the actual number of patients found, up to the limit specified.
    The output will indicate "showing up to X results" accordingly.

    Args:
        search_term: Optional. Part of the patient's first or last name to search for. If not provided, returns recent patients.
        limit: Maximum number of results to return (default: 30). Only increase this if the user explicitly asks for more results.
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    # Track tool execution latency
    start_time = time.time()

    try:
        results, query, params = neo4j_conn.search_patients(search_term, limit=limit)

        if not results:
            output = f"No patients found matching '{search_term}'."
        else:
            if search_term:
                output = f"Found patients matching '{search_term}' (showing up to {limit} results, sorted by relevance):\n\n"
            else:
                output = f"Found patients (showing up to {limit} most recent):\n\n"

            for i, record in enumerate(results, 1):
                output += f"{i}. {record['patient_name']} (ID: {record['patient_id']})\n"
                output += f"   Birth Date: {record['birth_date']}\n\n"

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "search_patients",
            "tool_args": {"search_term": search_term, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: search_patients",
            "duration_ms": duration_ms
        }

        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )
    except Exception as e:
        error_msg = f"Error searching patients: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")],
                "latency_logs": [{
                    "name": "Tool: search_patients",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="get_database_schema", run_type="tool", tags=["tool", "schema", "database"])
def get_database_schema(tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Get information about the database schema and structure.
    Use this to understand how data is organized and what relationships exist.

    Args:
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and latency tracking state.
    """
    # Track tool execution latency
    start_time = time.time()

    schema_description = neo4j_conn.get_database_schema()

    # Calculate latency
    duration_ms = round((time.time() - start_time) * 1000)

    # Create latency log entry
    latency_entry = {
        "name": "Tool: get_database_schema",
        "duration_ms": duration_ms
    }

    return Command(
        update={
            "messages": [ToolMessage(content=schema_description, tool_call_id=tool_call_id or "")],
            "latency_logs": [latency_entry]
        }
    )


@tool
@traceable(name="find_similar_patients", run_type="tool", tags=["tool", "patient", "similarity"])
def find_similar_patients(patient_name: str, limit: int = 5, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Find patients who are most similar to a given patient based on their medical history,
    encounters, procedures, medications, demographics, and expenses.

    This tool uses KNN (K-Nearest Neighbors) similarity based on embeddings that combine:
    - Encounter patterns (types and frequency of medical visits)
    - Procedure history (types and frequency of procedures)
    - Medication history (types and frequency of drugs prescribed)
    - Demographics (age)
    - Healthcare utilization (total encounters, expenses)

    Use this when users ask to:
    - Find similar patients
    - Compare a patient to others
    - Identify patients with similar medical profiles or journeys

    Args:
        patient_name: The patient's name (can be first name, last name, or full name like 'John Smith')
        limit: Maximum number of similar patients to return (default: 5)
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    log("TOOL", f"Called with patient_name='{patient_name}', limit={limit}", "find_similar_patients")

    # Track tool execution latency
    start_time = time.time()

    try:
        # Import here to avoid circular dependencies and only load when needed
        from patient_similarity_embeddings import PatientSimilarityEmbeddings

        # Initialize the embeddings generator
        embeddings_gen = PatientSimilarityEmbeddings()

        try:
            # Find similar patients using KNN_SIMILARITY (as per test 1)
            similar_patients = embeddings_gen.find_similar_patients(
                patient_name=patient_name,
                k=limit,
                similarity_type='KNN_SIMILARITY'
            )

            if not similar_patients:
                log("TOOL", f"No similar patients found for '{patient_name}'", "find_similar_patients")
                output = f"No similar patients found for '{patient_name}'. The patient may not exist or has no similarity relationships."
            else:
                source_patient = similar_patients[0]['source_patient']
                output = f"Top {len(similar_patients)} patients most similar to {source_patient}:\n\n"

                for i, patient in enumerate(similar_patients, 1):
                    output += f"{i}. {patient['similar_patient']}\n"
                    output += f"   Similarity Score: {patient['similarity_score']:.4f}\n"
                    output += f"   Age: {patient.get('age', 'N/A')}\n"
                    output += f"   Total Encounters: {patient.get('total_encounters', 0)}\n"
                    output += f"   Procedures: {patient.get('procedure_count', 0)}\n"
                    output += f"   Medications: {patient.get('drug_count', 0)}\n"
                    output += f"   Total Expenses: ${patient.get('expenses', 0):,.2f}\n\n"

                log("TOOL", f"Found {len(similar_patients)} similar patients", "find_similar_patients")

            # Build a pseudo-query for tracking purposes
            # (The actual implementation uses the GDS library, not a direct Cypher query)
            query = f"""
            MATCH (p:Patient)-[sim:KNN_SIMILARITY]-(similar:Patient)
            WHERE p.firstName + ' ' + p.lastName CONTAINS $patient_name
            RETURN similar
            ORDER BY sim.similarityScore DESC
            LIMIT $limit
            """

            params = {"patient_name": patient_name, "limit": limit}

        finally:
            # Always close the connection
            embeddings_gen.close()

        # Calculate latency
        duration_ms = round((time.time() - start_time) * 1000)

        # Create query tracking entry
        query_entry = {
            "query": query,
            "params": params,
            "source": "find_similar_patients",
            "tool_args": {"patient_name": patient_name, "limit": limit},
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entry
        latency_entry = {
            "name": "Tool: find_similar_patients",
            "duration_ms": duration_ms
        }

        return Command(
            update={
                "messages": [ToolMessage(content=output, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry],
                "latency_logs": [latency_entry]
            }
        )

    except Exception as e:
        log("TOOL", f"Error - {str(e)}", "find_similar_patients", level="error")
        error_msg = f"Error finding similar patients: {str(e)}"
        duration_ms = round((time.time() - start_time) * 1000)

        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")],
                "latency_logs": [{
                    "name": "Tool: find_similar_patients",
                    "duration_ms": duration_ms
                }]
            }
        )


@tool
@traceable(name="execute_custom_query", run_type="tool", tags=["tool", "custom", "cypher"])
def execute_custom_query(user_question: str, tool_call_id: Annotated[str, InjectedToolCallId] = None) -> Command:
    """
    Execute a custom database query for questions that don't fit the standard tools.
    This tool uses a specialized Cypher subgraph (LangGraph) to construct and execute custom queries.

    Use this tool when:
    - The user asks for complex aggregations or analytics
    - The user wants to find relationships between multiple entities
    - The question requires custom filtering or grouping
    - None of the other specialized tools can answer the question
    - The user asks about providers, organizations, or other non-patient entities
    - The user wants time-based analysis or trends

    Examples of when to use this tool:
    - "Which providers treated the most patients?"
    - "How many emergency visits were there in 2023?"
    - "What's the most common procedure performed?"
    - "Show me patients who had both diabetes and hypertension"
    - "Which organizations have the highest patient volume?"

    Args:
        user_question: The exact question the user asked in natural language
        tool_call_id: Internal parameter for tracking (automatically provided by LangGraph)

    Returns:
        Command object that updates both LLM-visible messages and internal query tracking state.
    """
    try:
        # Import here to avoid circular dependency
        from cypher_subagent import get_cypher_subgraph

        # Get the cypher subgraph and invoke it
        cypher_subgraph = get_cypher_subgraph()

        # Invoke subgraph with its own state structure
        subgraph_result = cypher_subgraph.invoke({
            "messages": [],
            "user_question": user_question,
            "generated_cypher": "",
            "cypher_explanation": "",
            "query_results": "",
            "llm_latency_ms": 0,
            "tool_latency_ms": 0,
            "cypher_model": ""
        })

        # Extract the response and generated cypher
        response = subgraph_result["messages"][-1].content if subgraph_result["messages"] else "No response"
        generated_cypher = subgraph_result.get("generated_cypher", "")

        # Extract latency information and model from subgraph
        llm_latency = subgraph_result.get("llm_latency_ms", 0)
        tool_latency = subgraph_result.get("tool_latency_ms", 0)
        cypher_model = subgraph_result.get("cypher_model", "")

        # Create query tracking entry with all details
        query_entry = {
            "query": generated_cypher,
            "params": {},
            "source": "execute_custom_query",
            "tool_args": {"user_question": user_question},
            "question": user_question,  # Include the question for frontend display
            "timestamp": datetime.now().isoformat()
        }

        # Create latency log entries for Cypher subgraph
        latency_logs = []
        if llm_latency > 0:
            latency_logs.append({
                "name": "LLM: Cypher",
                "duration_ms": llm_latency,
                "model": cypher_model
            })
        if tool_latency > 0:
            latency_logs.append({
                "name": "Tool: execute_cypher_query",
                "duration_ms": tool_latency
            })

        return Command(
            update={
                "messages": [ToolMessage(content=response, tool_call_id=tool_call_id or "")],
                "executed_queries": [query_entry] if generated_cypher else [],  # Only track if query was generated
                "latency_logs": latency_logs
            }
        )

    except Exception as e:
        error_msg = f"Error executing custom query: {str(e)}"
        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id or "")]
            }
        )


# Reducer function for executed_queries - concatenates new queries to existing list
def add_queries(existing: list, new: list) -> list:
    """
    Reducer that concatenates new queries to the existing list.
    This is needed for the Command pattern - when tools return {"executed_queries": [...]},
    LangGraph uses this reducer to append (not replace) the queries.
    """
    return existing + new


# Reducer function for latency_logs - concatenates new latency entries to existing list
def add_latency_logs(existing: list, new: list) -> list:
    """
    Reducer that concatenates new latency logs to the existing list.
    This tracks both LLM calls and tool executions with their timing information.
    """
    return existing + new


# Define the agent state
class AgentState(TypedDict):
    """State of the agent conversation."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    executed_queries: Annotated[list, add_queries]  # Track all Cypher queries executed (with reducer)
    latency_logs: Annotated[list, add_latency_logs]  # Track LLM and tool call latencies (with reducer)
    iteration_count: int  # Track number of reflection loop iterations
    route_decision: str  # Router's decision: "cypher" or "agent"

    # Note: executed_queries serves as our "user_info_for_display" channel - it stores
    # structured query data that the caller can access, separate from LLM messages.
    # The reducer ensures that when tools return new queries via Command, they are
    # appended to the list rather than replacing it.
    #
    # Note: latency_logs tracks timing information for LLM calls and tool executions.
    # Format: [{"name": "LLM: Validation", "duration_ms": 123.45}, ...]


# Create the tools list (INCLUDING execute_custom_query for analytics)
tools = [
    get_patient_procedures,
    get_patient_conditions,
    get_patient_medications,
    get_patient_encounters,
    search_patients,
    get_database_schema,
    find_similar_patients,
    execute_custom_query  # Added back for main agent to handle analytics
]


# ============================================================================
# Validation Decision Model (Pydantic model for structured output)
# ============================================================================

class ValidationDecision(BaseModel):
    """Validation of user query relevance to Synthea database schema."""

    is_relevant: bool = Field(
        description=(
            "Whether the user's query is relevant to the Synthea medical database:\n"
            "- True: Query is about patients, medical records, procedures, conditions, "
            "medications, encounters, providers, or organizations in the database\n"
            "- False: Query is unrelated to medical records or asks about topics outside "
            "the database scope (e.g., general knowledge, weather, news, other domains)"
        )
    )
    reasoning: str = Field(
        description="Brief explanation (1-2 sentences) of why the query is or isn't relevant"
    )


# NOTE: Query tracking is now handled via the Command pattern in tools.
# Tools return Command objects that update both messages and executed_queries state.
# The standard ToolNode handles Command returns automatically with the reducer.


# Initialize the LLM with tools
def create_agent(api_key: str = None):
    """
    Create and configure the LangGraph agent.

    Args:
        api_key: SambaNova API key (defaults to SAMBANOVA_API_KEY env var)

    Returns:
        Compiled LangGraph agent
    """
    # Initialize Main Agent LLM (for tool selection and initial responses)
    main_model = get_main_agent_model()
    main_llm = create_llm(
        model=main_model,
        temperature=0,
        api_key=api_key
    )

    # Initialize Synthesis LLM (for synthesizing tool results into final responses)
    synthesis_model = get_synthesis_model()
    synthesis_llm = create_llm(
        model=synthesis_model,
        temperature=0,
        api_key=api_key,
        max_tokens=3000  # Set max tokens for synthesis responses
    )

    # Bind tools to Main LLM
    llm_with_tools = main_llm.bind_tools(tools)

    # ========================================================================
    # Validation Node Function
    # ========================================================================
    def validation_node(state: AgentState) -> dict:
        """
        Entry validation: checks if user query is relevant to Synthea database.
        This runs FIRST for each new user message.
        """
        messages = state["messages"]

        # Find the user's question
        user_query = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break

        if not user_query:
            log("APP", "No user query found in validation")
            return {"messages": messages}

        log("APP", f"Validation processing query: {user_query[:80]}...")

        # Create validation LLM using provider-specific config
        try:
            validation_model = get_validation_model()
            validation_llm = create_llm(
                model=validation_model,
                temperature=0,
            ).with_structured_output(ValidationDecision)
        except Exception as e:
            log("APP", f"Validation LLM creation failed: {e}, proceeding to agent", level="error")
            return {"messages": messages}

        # Get database schema for validation context
        schema_description = neo4j_conn.get_database_schema()

        # Build conversation history context
        conversation_context = ""
        if len(messages) > 1:
            # Get previous messages (excluding the current user query)
            previous_messages = []
            for msg in messages[:-1]:
                if isinstance(msg, HumanMessage):
                    previous_messages.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    previous_messages.append(f"Assistant: {msg.content}")

            if previous_messages:
                conversation_context = "\nCONVERSATION HISTORY:\n" + "\n".join(previous_messages[-6:]) + "\n"

        # Validation prompt with schema and conversation context
        validation_prompt = f"""You are a query validator for the Synthea medical records database.

DATABASE SCHEMA:
{schema_description}
{conversation_context}
CURRENT USER QUERY: {user_query}

Your task: Determine if the user's current query is relevant to this medical database.

IMPORTANT: Consider the conversation history when evaluating the query. Pronouns (he, she, they, him, her, them) or contextual references (that patient, those medications, etc.) should be evaluated based on what they refer to in the conversation history.

RELEVANT queries include:
- Questions about patients, their medical history, procedures, conditions, medications
- Questions about healthcare encounters, providers, organizations
- Statistical queries about medical data (counts, averages, trends)
- Searching for or retrieving medical records
- Questions about the database structure or schema
- Follow-up questions that reference previous medical queries (even if using pronouns)

IRRELEVANT queries include:
- General knowledge questions unrelated to medical records
- Questions about current events, news, weather
- Questions about topics outside healthcare/medical domain
- Requests for information not stored in this database

Classify this query as relevant (True) or irrelevant (False)."""

        try:
            # Track validation LLM latency
            start_time = time.time()
            decision: ValidationDecision = validation_llm.invoke(validation_prompt)
            duration_ms = round((time.time() - start_time) * 1000)

            log("APP", f"Validation decision: {decision.is_relevant} - {decision.reasoning}")

            # Create latency log entry
            latency_entry = {
                "name": "LLM: Validation",
                "duration_ms": duration_ms,
                "model": validation_model
            }

            if not decision.is_relevant:
                # Query is not relevant - return rejection message
                rejection_message = "I am sorry - I can only answer questions that pertain to the Synthea medical records."
                log("APP", f"Query rejected as irrelevant: {user_query[:80]}...")
                return {
                    "messages": messages + [AIMessage(content=rejection_message)],
                    "latency_logs": [latency_entry]
                }

            # Query is relevant - proceed with normal flow
            log("APP", "Query validated as relevant, proceeding to agent")
            return {
                "messages": messages,
                "latency_logs": [latency_entry]
            }

        except Exception as e:
            log("APP", f"Validation error: {e}, proceeding to agent", level="error")
            return {"messages": messages}

    # ========================================================================
    # Simplified Routing Functions
    # ========================================================================
    def route_from_validation(state: AgentState) -> str:
        """Route from validation: if query was rejected, end. Otherwise, go to agent."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check if the last message is a rejection from validation
        if isinstance(last_message, AIMessage) and "I am sorry - I can only answer questions that pertain to the Synthea medical records" in last_message.content:
            log("APP", "Query rejected by validation, ending")
            return "end"

        log("APP", "Query validated, routing to agent")
        return "agent"

    def route_from_agent(state: AgentState) -> str:
        """Route from agent: tools if tool calls, otherwise end."""
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            log("APP", f"Agent called tools: {[tc['name'] for tc in last_message.tool_calls]}")
            return "tools"

        log("APP", "Agent done with final response, ending")
        return "end"


    # Define the function that calls the model
    def call_model(state: AgentState) -> dict:
        """Call the LLM with the current state."""
        messages = state["messages"]

        # Increment iteration count
        current_iteration = state.get("iteration_count", 0)
        new_iteration = current_iteration + 1

        log("APP", f"call_model invoked: incrementing iteration from {current_iteration} to {new_iteration}")

        # Find the index of the most recent HumanMessage to identify the current turn
        last_human_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_idx = i
                break

        # Detect if we have tool results in the CURRENT turn (synthesis mode)
        has_tool_results = False
        if last_human_idx is not None and new_iteration > 1:
            # Check messages after the last HumanMessage for ToolMessages (current turn only)
            current_turn_messages = messages[last_human_idx + 1:]
            has_tool_results = any(isinstance(msg, ToolMessage) for msg in current_turn_messages)

        # Filter messages for LLM: keep only HumanMessage and AIMessage from previous turns
        # Keep ALL message types from the current turn
        filtered_messages = []
        for i, msg in enumerate(messages):
            if i <= (last_human_idx or 0):
                # For previous turns and the current HumanMessage, keep only Human and AI messages
                if isinstance(msg, (HumanMessage, AIMessage)):
                    filtered_messages.append(msg)
            else:
                # For current turn after HumanMessage, keep all messages (including ToolMessage)
                filtered_messages.append(msg)

        # Use filtered messages for the rest of the function
        messages = filtered_messages

        # Add system message if this is the first message
        if len(messages) == 1:
            system_message = """You are a helpful medical database assistant that helps users query patient information from the Synthea database.

The database contains patient healthcare records including:
- Patient demographics
- Healthcare encounters (visits)
- Procedures performed
- Diagnoses
- Medications prescribed

TOOL SELECTION GUIDELINES:

**Use the specialized tools for specific patient queries:**
- get_patient_procedures: When users ask about a specific patient's procedures. Use the patient's name (first, last, or full name).
- get_patient_conditions: When users ask about a specific patient's conditions/diagnoses. Use the patient's name (first, last, or full name).
- get_patient_medications: When users ask about a specific patient's medications. Use the patient's name (first, last, or full name).
- get_patient_encounters: When users ask about a specific patient's encounters/visits. Use the patient's name (first, last, or full name).
- search_patients: When you need to find or search for patients by name. Returns a list of matching patients.
- get_database_schema: When users ask about database structure or schema information.
- find_similar_patients: When users ask to find patients similar to a specific patient based on their medical history, demographics, and healthcare utilization. Returns patients with similar medical profiles/journeys.

**Use execute_custom_query for complex analytics:**
- Aggregations and counts ("How many patients...", "What's the total...", "Average age...")
- Top-N queries ("Which patients spent the most...", "Most common procedures...", "Top 10...")
- Time-based analysis ("Patients admitted in 2023...", "Encounters last month...")
- Multi-entity relationships ("Patients with both diabetes AND hypertension...")
- Provider/organization queries ("Which providers treated...", "Organizations with highest volume...")
- Statistical queries ("Distribution of...", "Trends over time...")

**RESULT LIMITS:**
- All tools return a maximum of 30 results by default, sorted by most recent first
- Only increase the limit parameter if the user explicitly requests more results (e.g., "show me all 100 procedures" or "give me the last 50 medications")
- Tool outputs will indicate if results were limited

**MULTI-STEP QUERIES:**
If a query requires multiple pieces of information, call ALL relevant tools in a single response.

Example: "What procedures and medications did John Smith have?"
→ Call BOTH get_patient_procedures AND get_patient_medications in the same response

**PATIENT NAMES:**
Patient names in this database are synthetic and may include numbers (e.g., "Ethan766 Nolan344" or "John123 Smith456").
- These alphanumeric names are actual patient names, NOT patient IDs
- When a user asks about a patient with an alphanumeric name, use that exact name in your tool calls
- Don't ask for clarification or treat these as IDs - they are the actual names in the database
- Tools can match patients using just the first name, just the last name, or the full name - simply pass whatever name the user provides to the tool and let it handle the matching

**CONVERSATION CONTEXT AND PRONOUNS:**
IMPORTANT: Review the conversation history to resolve pronoun references (he, she, they, him, her, them) and contextual references (that patient, those medications, etc.).
- If the user asks "how old is he?", look at the conversation history to identify which patient was previously discussed
- If the user asks "find patients similar to him", identify the patient from the conversation history
- Use the exact patient name from the conversation history when making tool calls
- Example: If the previous question was about "Dudley365 Spencer878" and the user asks "how old is he?", use execute_custom_query to get Dudley365 Spencer878's age

Always be clear and helpful in your responses. If a patient is not found, suggest searching by name."""

            messages = [HumanMessage(content=system_message)] + messages

        # If we have tool results, inject synthesis guidance
        elif has_tool_results and current_iteration > 0:
            # Count how many tool results we have
            tool_count = sum(1 for msg in messages[-10:] if isinstance(msg, ToolMessage))

            log("APP", f"Synthesis mode: {tool_count} tool result(s) detected")

            synthesis_instruction = """You have received results from your tool calls.

*** IMPORTANT: RESPECTFUL COMMUNICATION ***
Your response must be respectful, professional, and helpful at all times:
- Use a polite, supportive, and empathetic tone
- Never include harsh, rude, or confrontational language
- Avoid any content that could be considered hate speech, discriminatory, or offensive
- Be patient and understanding, even if the user's question cannot be fully answered
- Frame limitations or missing information in a helpful, constructive way
- Treat all patients, demographics, and medical conditions with dignity and respect

*** CRITICAL RULE #1 - NO HALLUCINATION ***
DO NOT HALLUCINATE OR MAKE UP INFORMATION!
- ONLY use information that is explicitly present in the tool results
- If the tool results do not contain information that answers the user's question, respond EXACTLY with: "I am sorry, I do not have the answer to your question"
- DO NOT infer, guess, or extrapolate beyond what the tool results explicitly state
- If you cannot answer the user's question based on the tool results, acknowledge this truthfully with the exact apology message above

*** CRITICAL RULE #2 - LIMIT LANGUAGE ***
DO NOT ADD PHRASES LIKE "showing up to 30" OR "top 30" UNLESS THE TOOL OUTPUT CONTAINS THEM!
- Check the FIRST LINE of the tool result message
- If it says "(showing up to X most recent)" → copy that exact phrase
- If it does NOT have that phrase → do NOT add any "showing up to" or "top X" language
- Instead, just state the actual count (e.g., "has 21 medications")

*** CRITICAL RULE #3 - PATIENT IDs ***
DO NOT include patient IDs (UUIDs like "34363d95-4e03-4910-5018-3cabddcc50a3") in your response UNLESS the user specifically asked for IDs.
- Only show patient names and other relevant clinical information
- IDs are internal database identifiers that are not useful to users in most cases
- Exception: If the user explicitly asks "show me the patient ID" or similar, then include it

*** CRITICAL RULE #4 - MARKDOWN FORMATTING ***
Your response will be rendered as Markdown in the UI.

IMPORTANT LIST FORMATTING - Use this EXACT format (no trailing spaces, no blank lines):
```
Here are the results:

1. Item one text here
2. Item two text here
3. Item three text here
```

DO NOT use trailing spaces (two spaces at line end) for line breaks - they cause excessive spacing in lists.
If you need an explicit line break within text, use a blank line to start a new paragraph instead.

Rules:
- NEVER add trailing spaces after list items
- No blank lines between list items
- Lists should be compact and readable

IMPORTANT - SYNTHESIZE YOUR FINAL ANSWER NOW:

1. Review all tool results and extract specific data (names, dates, numbers, amounts)
2. Synthesize the information into a clear, natural answer to the user's question
3. DO NOT make additional tool calls - just provide the final response
4. Present information in a conversational, user-friendly way

FORMATTING GUIDELINES:

**For Single-Result Queries (only ONE item to report):**
- DO NOT use numbered lists or bullet points for single results
- Present the answer as a natural, conversational sentence
- Examples:
  * "Sarah Williams has spent the most on healthcare, with total expenses of $3,245,123.50."
  * "Robert Johnson's most recent procedure was a Blood Pressure Screening on 2024-02-20."
  * "The database contains 6,421 total patient records."

**For Multiple Records (2+ items - procedures, medications, conditions, encounters, etc.):**
- Present the results as a numbered list
- Include a brief introductory sentence with the patient name and count
- Check the tool output's first line for limit language:
  * Contains "(showing up to X most recent)" → Say "has had at least X [items]. Here are X of the most recent [items]:"
  * Does NOT contain limit language → Say "has X [items]:" where X is the actual count
- Then list ALL items from the tool results
- Examples:
  * Tool says "(showing up to 30 most recent)" → "Michael Brown has had at least 30 procedures. Here are 30 of the most recent procedures:"
  * Tool has no limit phrase → "Jennifer Davis has 18 medications:"

**For Multiple Tool Results (combining different types of data):**
- Organize information logically (chronologically, by category, or by relationship)
- Use connecting phrases to create natural flow
- Use lists for each data type if appropriate
- Example: "John Smith has had several procedures including an Electrocardiogram on 2023-06-15 and a Chest X-ray on 2023-03-22. He is currently taking Metformin for Type 2 Diabetes and Lisinopril for Hypertension."

**For Similar Patient Results (from find_similar_patients tool):**
- ALWAYS use Markdown table format for better readability
- Include ALL available columns: Patient Name, Similarity Score, Age, Encounters, Procedures, Medications, and Total Expenses
- Format similarity scores to 4 decimal places (e.g., 0.8557)
- Format expenses with dollar sign and commas (e.g., $232,720.06)
- Example table format:
```
Here are the top 5 patients most similar to [Patient Name]:

| Patient Name | Similarity | Age | Encounters | Procedures | Medications | Total Expenses |
|--------------|------------|-----|------------|------------|-------------|----------------|
| John Smith | 0.8557 | 43 | 44 | 43 | 3 | $232,720.06 |
| Jane Doe | 0.8543 | 43 | 51 | 39 | 6 | $211,810.82 |
```

CRITICAL RULES:
- Use EXACT numbers, dates, and amounts from tool results - don't approximate
- Don't add uncertainty phrases like "approximately" or "based on available information" when complete data is provided
- Plain natural language ONLY - NO Cypher queries, SQL, or code in your response
- NO table formatting with pipes (|) or dashes (-) EXCEPT for similar patient results from find_similar_patients tool
- PRESERVE RESULT COUNT LANGUAGE: If the tool output mentions a specific count (e.g., "showing up to 30") or doesn't mention a limit at all, use that exact language. DO NOT add phrases like "top 30" or "most recent 30" if the tool output doesn't include them.
- When the tool output contains a numbered or bulleted list, preserve that list format in your response
- FORMAT TIMESTAMPS: Convert ISO 8601 timestamps (e.g., "2023-01-01T12:48:47.000000000+00:00") to natural date format (e.g., "January 1, 2023" or "2023-01-01"). Strip time and timezone unless specifically relevant.

Provide your synthesized answer now:"""

            messages = messages + [HumanMessage(content=synthesis_instruction)]

        # Track LLM latency and invoke appropriate LLM
        start_time = time.time()

        # Use synthesis LLM if we have tool results, otherwise use main LLM with tools
        if has_tool_results:
            # Synthesis mode: use synthesis LLM (no tool binding needed)
            response = synthesis_llm.invoke(messages)
            llm_name = "LLM: Synthesis"
            log("AGENT", "Using SYNTHESIS_LLM for response synthesis", "MAIN")
        else:
            # Initial call: use main agent LLM with tools
            response = llm_with_tools.invoke(messages)
            llm_name = "LLM: Main"
            log("AGENT", "Using MAIN_AGENT_LLM for tool selection", "MAIN")

        duration_ms = round((time.time() - start_time) * 1000)

        if hasattr(response, 'content') and response.content:
            log("AGENT", f"Response content: {response.content[:200]}...", "MAIN")
        if hasattr(response, 'tool_calls') and response.tool_calls:
            log("AGENT", f"Made tool calls: {[tc['name'] for tc in response.tool_calls]}", "MAIN")

        # Determine which model was used based on llm_name
        model_used = synthesis_model if llm_name == "LLM: Synthesis" else main_model

        latency_entry = {
            "name": llm_name,
            "duration_ms": duration_ms,
            "model": model_used
        }

        return {
            "messages": [response],
            "iteration_count": new_iteration,
            "latency_logs": [latency_entry]
        }

    # NOTE: call_model_summary() removed - agent now synthesizes its own responses
    # after receiving tool results using conditional synthesis instruction injection

    # Create standard tool node - tools return Command objects that handle query tracking
    tool_node = ToolNode(tools)

    # Build the graph with validation and simplified routing
    workflow = StateGraph(AgentState)

    # ========================================================================
    # OPTIMIZED GRAPH STRUCTURE WITH VALIDATION:
    # START → validation → [agent → tools → agent (synthesis)] OR [end] → END
    #
    # Key features:
    # - Validation node checks query relevance before processing
    # - No router node (agent handles tool selection including execute_custom_query)
    # - No cypher node (now a tool that agent can call)
    # - No summary node (agent synthesizes its own tool results)
    # - LLM calls: validation (1) + agent (1-2) = 2-3 total (vs 3-4 before)
    # ========================================================================
    log("APP", "Building optimized graph with validation and agent self-synthesis")

    # Add nodes
    workflow.add_node("validation", validation_node)  # Entry validation - checks relevance
    workflow.add_node("agent", call_model)            # Main agent - tool selection and synthesis
    workflow.add_node("tools", tool_node)             # Tool execution

    # Set validation as entry point
    workflow.set_entry_point("validation")

    # Validation routes to agent or end
    workflow.add_conditional_edges(
        "validation",
        route_from_validation,
        {
            "agent": "agent",
            "end": END
        }
    )

    # Agent routes to tools or end
    workflow.add_conditional_edges(
        "agent",
        route_from_agent,
        {
            "tools": "tools",
            "end": END
        }
    )

    # Tools always route back to agent for synthesis (deterministic)
    workflow.add_edge("tools", "agent")

    # Compile and return
    return workflow.compile()


@traceable(name="query_agent", tags=["agent", "main"])
def query_agent(agent, user_message: str, conversation_history: list = None, executed_queries: list = None) -> tuple[str, list, list, list]:
    """
    Query the agent with a user message.

    Args:
        agent: Compiled LangGraph agent
        user_message: User's question
        conversation_history: Previous conversation messages
        executed_queries: Previous executed queries (not used, reset each turn)

    Returns:
        Tuple of (response_text, updated_conversation_history, executed_queries, latency_logs)
    """
    if conversation_history is None:
        conversation_history = []

    # Add user message to history
    conversation_history.append(HumanMessage(content=user_message))

    # Run the agent with state - reset executed_queries and latency_logs to empty list for each new turn
    # This ensures only queries and latency logs from the current turn are returned
    result = agent.invoke({
        "messages": conversation_history,
        "executed_queries": [],  # Reset to empty list for each new query
        "latency_logs": [],  # Reset to empty list for each new query
        "iteration_count": 0  # Initialize iteration count for each new query
    })

    # Get the final response
    final_message = result["messages"][-1]
    response_text = final_message.content

    # Update conversation history and get only the queries and latency logs from this turn
    conversation_history = result["messages"]
    executed_queries = result.get("executed_queries", [])
    latency_logs = result.get("latency_logs", [])

    return response_text, conversation_history, executed_queries, latency_logs
