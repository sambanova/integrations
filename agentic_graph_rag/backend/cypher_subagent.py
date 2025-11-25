"""
Cypher Subagent - LangGraph subgraph for constructing custom Cypher queries.
This subagent has deep knowledge of the Synthea database schema.
"""
import os
import time
import logging
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from neo4j_utils import Neo4jConnection
from llm_factory import create_llm, get_cypher_agent_model
from langsmith.run_helpers import traceable

# Configure logger for cypher subagent
cypher_logger = logging.getLogger("synthea_cypher_agent")
if os.getenv("AGENT_DEBUG_LOGGING", "false").lower() == "true":
    cypher_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
    cypher_logger.addHandler(handler)
    cypher_logger.propagate = False
else:
    cypher_logger.setLevel(logging.WARNING)


# Initialize Neo4j connection for the subagent
_neo4j_conn = None

def get_neo4j_connection():
    """Get or create Neo4j connection."""
    global _neo4j_conn
    if _neo4j_conn is None:
        _neo4j_conn = Neo4jConnection()
        _neo4j_conn.connect()
    return _neo4j_conn


# Detailed Synthea database schema for the subagent
SYNTHEA_SCHEMA_DETAILED = """
# SYNTHEA DATABASE SCHEMA - COMPLETE REFERENCE

## NODE TYPES AND PROPERTIES

### Patient Node
Label: Patient
Properties:
  - id (String): Unique patient identifier
  - firstName (String): Patient's first name
  - lastName (String): Patient's last name
  - birthDate (Date): Date of birth
  - ssn (String): Social Security Number
  - gender (String): Patient gender
  - marital (String): Marital status
  - suffix (Float): Name suffix
  - age (Float): Patient age
  - expenses (Float): Total healthcare expenses
  - income (Integer): Annual income

Relationships FROM Patient:
  - [:HAS_ENCOUNTER] -> (Encounter): Patient's healthcare visits
  - [:HAS_RACE] -> (Race): Patient's race

### Encounter Node
Labels: Encounter with additional type labels
  - Base label: Encounter (all encounters)
  - Type labels (multi-label): Ambulatory, Wellness, Outpatient, Urgentcare, Emergency, Inpatient, Home, Hospice, Snf, Virtual

Properties:
  - id (String): Unique encounter identifier
  - date (DateTime): Encounter start date/time
  - description (String): Encounter description
  - end (DateTime): Encounter end date/time
  - isEnd (Boolean): Whether encounter has ended
  - totalCost (Float): Total cost of encounter

Relationships FROM Encounter:
  - [:HAS_PROCEDURE] -> (Procedure): Procedures performed during encounter
  - [:HAS_DRUG] -> (Drug): Medications prescribed
  - [:HAS_DIAGNOSIS] -> (Diagnosis): Diagnoses made
  - [:OF_TYPE] -> (SNOMED_CT): Encounter type classification
  - [:HAS_END] -> (Encounter): Link to another encounter (end relationship)

Relationships TO Encounter:
  - (Patient)-[:HAS_ENCOUNTER] -> (Encounter)

### Procedure Node
Labels: SNOMED_CT, Procedure (multi-label)
Properties:
  - description (String): Procedure description
  - code (String): SNOMED CT code

Relationships TO Procedure:
  - (Encounter)-[:HAS_PROCEDURE] -> (Procedure)
  - (Encounter)-[:OF_TYPE] -> (Procedure): Some encounters link to procedures via OF_TYPE

### Drug Node
Label: Drug
Properties:
  - code (Long): Drug code
  - description (String): Drug/medication name

Relationships TO Drug:
  - (Encounter)-[:HAS_DRUG] -> (Drug)

### Diagnosis Node
Labels: SNOMED_CT, Diagnosis (multi-label)
Properties:
  - code (String): SNOMED CT code
  - description (String): Diagnosis description

Relationships TO Diagnosis:
  - (Encounter)-[:HAS_DIAGNOSIS] -> (Diagnosis)

### Race Node
Label: Race
Properties:
  - race (String): Race description

Relationships TO Race:
  - (Patient)-[:HAS_RACE] -> (Race)

### Other Supporting Nodes
- SNOMED_CT: Medical terminology codes (can have sub-labels: Procedure, Diagnosis)

## COMMON QUERY PATTERNS

### Patient Journey Queries
1. Get all encounters for a patient:
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
   WHERE p.firstName = 'Name' OR p.id = 'patient-id'
   RETURN e ORDER BY e.date

2. Get procedures through encounters:
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc:Procedure)
   WHERE p.firstName = 'Name'
   RETURN proc.description, e.date

3. Get diagnoses through encounters:
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DIAGNOSIS]->(diag:Diagnosis)
   WHERE p.firstName = 'Name'
   RETURN diag.description, e.date

4. Get medications through encounters:
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DRUG]->(drug:Drug)
   WHERE p.firstName = 'Name'
   RETURN drug.description, e.date

### Encounter Type Queries
5. Filter by encounter type (using multi-labels):
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Emergency)  # Emergency visits only
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Inpatient)  # Hospital stays only
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Wellness)   # Wellness visits only

### Aggregate Queries
6. Count procedures per patient:
   MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc:Procedure)
   RETURN p.firstName + ' ' + p.lastName AS patient, count(proc) AS procedure_count
   ORDER BY procedure_count DESC

7. Count encounters by type:
   MATCH (e:Encounter)
   RETURN labels(e) AS encounter_types, count(e) AS count
   ORDER BY count DESC

8. Find patients with most healthcare expenses:
   MATCH (p:Patient)
   WHERE p.expenses IS NOT NULL
   RETURN p.firstName, p.lastName, p.expenses
   ORDER BY p.expenses DESC
   LIMIT 10

### Time-based Queries
9. Get recent encounters:
    MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
    WHERE e.date >= datetime('2020-01-01')
    RETURN e ORDER BY e.date DESC

10. Get encounters in a date range:
    MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
    WHERE e.date >= datetime('2020-01-01') AND e.date <= datetime('2020-12-31')
    RETURN e ORDER BY e.date

## IMPORTANT CYPHER SYNTAX NOTES

1. Patient identification:
   - Use: WHERE p.firstName = 'FirstName' OR p.id = 'patient-id'
   - Names are case-sensitive

2. Multi-label nodes:
   - Encounters have type labels: (e:Encounter:Emergency)
   - Can filter by: MATCH (e:Emergency) or check with: labels(e)

3. Date handling:
   - Properties: e.date, e.end (DateTime type)
   - Compare: WHERE e.date >= datetime('2020-01-01')
   - Sort: ORDER BY e.date DESC

4. String matching:
   - Case-insensitive: WHERE toLower(p.firstName) CONTAINS toLower('search')
   - Exact match: WHERE p.firstName = 'Name'

5. Aggregations:
   - count(), sum(), avg(), min(), max()
   - GROUP BY is implicit in RETURN with aggregations

6. Limiting results:
   - Use: LIMIT 10
   - For pagination: SKIP 10 LIMIT 10

7. Distinct results:
   - Use: RETURN DISTINCT
   - Or: WITH DISTINCT before RETURN

## STATISTICS (for reference)
- Total Patients: ~5,885
- Total Encounters: ~1,274,720
- Total Procedures: 271
- Total Conditions: 271
- Total Drugs: 326
- Total Providers: 1,088
- Total Organizations: 1,088
"""


# Define the state for the Cypher subgraph
class CypherSubgraphState(TypedDict):
    """State for the Cypher generation subgraph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_question: str
    generated_cypher: str
    cypher_explanation: str
    query_results: str
    llm_latency_ms: int  # Track Cypher LLM latency
    tool_latency_ms: int  # Track execute_cypher_query tool latency
    cypher_model: str  # Model name used for Cypher generation


# Tool for executing Cypher queries (used by subgraph)
@tool
def execute_cypher_query(cypher_query: str) -> str:
    """
    Execute a Cypher query against the Neo4j database.

    Args:
        cypher_query: A valid Cypher query string

    Returns:
        Formatted query results or error message
    """
    cypher_logger.debug(f"TOOL execute_cypher_query: Executing query: {cypher_query[:200]}...")

    try:
        conn = get_neo4j_connection()
        result = conn.execute_custom_cypher(cypher_query)

        if not result["success"]:
            cypher_logger.error(f"TOOL execute_cypher_query: Query failed: {result['message']}")
            return f"Query execution failed: {result['message']}"

        results = result["results"]
        result_count = result["result_count"]

        if result_count == 0:
            cypher_logger.debug(f"TOOL execute_cypher_query: Query returned no results")
            return "Query executed successfully but returned no results."

        cypher_logger.debug(f"TOOL execute_cypher_query: Query succeeded with {result_count} results")

        # Format results as a simple table
        output = f"Query Results ({result_count} records):\n\n"

        if results:
            # Get column headers from first result
            headers = list(results[0].keys())

            # Add headers
            output += " | ".join(headers) + "\n"
            output += "-" * (len(" | ".join(headers))) + "\n"

            # Add rows (limit to 50 for readability)
            for row in results[:50]:
                values = [str(row.get(h, "")) for h in headers]
                output += " | ".join(values) + "\n"

            if result_count > 50:
                output += f"\n... and {result_count - 50} more results\n"

        cypher_logger.debug(f"TOOL execute_cypher_query: Returning formatted result (first 200 chars): {output[:200]}...")
        return output

    except Exception as e:
        cypher_logger.error(f"TOOL execute_cypher_query: Exception: {str(e)}")
        return f"Error executing query: {str(e)}"


# Create the Cypher subgraph
def create_cypher_subgraph(api_key: str = None):
    """
    Create the Cypher generation subgraph.

    This subgraph:
    1. Receives a user question
    2. Generates appropriate Cypher query
    3. Executes the query
    4. Returns formatted results

    Args:
        api_key: OpenAI API key

    Returns:
        Compiled LangGraph subgraph
    """

    # Initialize LLM for Cypher generation (using configured provider and model)
    model = get_cypher_agent_model()
    llm = create_llm(
        model=model,
        temperature=0,
        api_key=api_key
    )

    # Bind tools to LLM
    tools = [execute_cypher_query]
    llm_with_tools = llm.bind_tools(tools)

    # System message for Cypher generation
    cypher_system_prompt = f"""You are a Cypher query expert specializing in the Synthea healthcare database.

Your task is to generate valid, efficient Cypher queries based on user questions, then execute them using the execute_cypher_query tool.

{SYNTHEA_SCHEMA_DETAILED}

## YOUR RESPONSIBILITIES

1. **Analyze the Question**: Understand what data the user is asking for
2. **Generate Cypher**: Create a valid, efficient Cypher query
3. **Execute Query**: Call execute_cypher_query tool with your generated query
4. **Present Results**: Explain the results in a clear, user-friendly way

## QUERY GUIDELINES

1. **RESULT LIMITS - PAY ATTENTION TO SINGULAR vs PLURAL**:
   - **SINGULAR questions** (Which patient, What is the most, Who has the highest):
     - Use LIMIT 1 to return ONLY ONE result
     - Examples: "Which patient has the highest expenses?" → LIMIT 1
                 "What is the most common procedure?" → LIMIT 1
                 "Who has undergone the most expensive treatment?" → LIMIT 1
   - **PLURAL questions** (Which patients, What are the top, Show me the most):
     - Use LIMIT 10-30 to return multiple results
     - Examples: "Which patients have high expenses?" → LIMIT 20
                 "What are the top 10 procedures?" → LIMIT 10
   - Only increase the limit if the user explicitly requests more (e.g., "show me 100 results")

2. **SORTING**: Always sort results appropriately
   - For time-based data: ORDER BY e.date DESC (most recent first)
   - For aggregations: ORDER BY count/sum DESC (highest first)
   - For patient names: ORDER BY p.firstName, p.lastName

3. **Patient matching**: Always handle patient name variations (firstName OR lastName matching)

4. **Return meaningful field names** in RETURN clause (use AS to rename)

5. **Add DISTINCT** when appropriate to avoid duplicates

6. **Keep queries efficient** - don't over-complicate

7. **Test logic** - make sure the path makes sense in the schema

## IMPORTANT
After generating a query, you MUST call the execute_cypher_query tool to run it. Do not just return the query - execute it!

## EXAMPLES

User: "Which patient has the highest healthcare expenses?"  [SINGULAR - wants ONE result]

Your response should:
1. Generate the query
2. Call execute_cypher_query with:
   MATCH (p:Patient)
   WHERE p.expenses IS NOT NULL
   RETURN p.firstName + ' ' + p.lastName AS patient_name, p.expenses
   ORDER BY p.expenses DESC
   LIMIT 1
3. Present the results in a friendly way

User: "Which procedures were performed most frequently?"  [PLURAL - wants multiple results]

Your response should:
1. Generate the query
2. Call execute_cypher_query with:
   MATCH (e:Encounter)-[:HAS_PROCEDURE]->(proc:Procedure)
   RETURN proc.description AS procedure_name, count(e) AS procedure_count
   ORDER BY procedure_count DESC
   LIMIT 30
3. Present the results in a friendly way

User: "Show me patients with the highest healthcare expenses"  [PLURAL - wants multiple results]

Your response should:
1. Generate the query
2. Call execute_cypher_query with:
   MATCH (p:Patient)
   WHERE p.expenses IS NOT NULL
   RETURN p.firstName + ' ' + p.lastName AS patient_name, p.expenses
   ORDER BY p.expenses DESC
   LIMIT 30
3. Present the results in a friendly way

User: "Give me the top 10 most expensive encounters"  [User explicitly requested 10]

Your response should:
1. Generate the query
2. Call execute_cypher_query with:
   MATCH (e:Encounter)
   WHERE e.totalCost IS NOT NULL
   RETURN e.description AS encounter_type, e.date, e.totalCost
   ORDER BY e.totalCost DESC
   LIMIT 10
3. Present the results in a friendly way

Now help the user with their question!"""

    # Define node functions
    def should_continue(state: CypherSubgraphState) -> str:
        """Determine if we should continue to tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If there are tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        else:
            return "end"

    def call_cypher_generator(state: CypherSubgraphState) -> dict:
        """Generate Cypher query using LLM."""
        messages = state["messages"]
        user_question = state.get("user_question", "")

        cypher_logger.debug(f"CYPHER LLM: Generating Cypher for question: {user_question}")

        # Create messages with system prompt
        full_messages = [
            SystemMessage(content=cypher_system_prompt),
            HumanMessage(content=f"User Question: {user_question}")
        ]

        # If there are existing messages (from tool responses), add them
        if len(messages) > 0:
            full_messages.extend(messages)

        # Call LLM and track latency
        start_time = time.time()
        response = llm_with_tools.invoke(full_messages)
        llm_duration_ms = round((time.time() - start_time) * 1000)

        # Extract the Cypher query from tool calls if present
        generated_query = state.get("generated_cypher", "")
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                if tc["name"] == "execute_cypher_query":
                    generated_query = tc["args"].get("cypher_query", "")
                    cypher_logger.debug(f"CYPHER LLM: Generated query: {generated_query[:200]}...")
                    break

        if hasattr(response, 'content') and response.content:
            cypher_logger.debug(f"CYPHER LLM: Response content: {response.content[:200]}...")

        return {
            "messages": [response],
            "generated_cypher": generated_query,
            "llm_latency_ms": llm_duration_ms,
            "cypher_model": model
        }

    # Create ToolNode
    tool_node = ToolNode(tools)

    # Wrap tool_node to track latency
    def tool_node_with_latency(state: CypherSubgraphState) -> dict:
        """Wrapper for tool node that tracks execution latency."""
        start_time = time.time()
        result = tool_node.invoke(state)
        tool_duration_ms = round((time.time() - start_time) * 1000)

        # Add tool latency to result
        result["tool_latency_ms"] = tool_duration_ms
        return result

    # Build the subgraph
    workflow = StateGraph(CypherSubgraphState)

    # Add nodes
    workflow.add_node("cypher_generator", call_cypher_generator)
    workflow.add_node("execute_query", tool_node_with_latency)

    # Set entry point
    workflow.set_entry_point("cypher_generator")

    # Add conditional edges
    workflow.add_conditional_edges(
        "cypher_generator",
        should_continue,
        {
            "continue": "execute_query",
            "end": END
        }
    )

    # Add edge from tools back to generator (for potential follow-up)
    workflow.add_edge("execute_query", "cypher_generator")

    return workflow.compile()


# Singleton instance for the subgraph
_cypher_subgraph = None


def get_cypher_subgraph():
    """Get or create the Cypher subgraph singleton."""
    global _cypher_subgraph
    if _cypher_subgraph is None:
        _cypher_subgraph = create_cypher_subgraph()
    return _cypher_subgraph


@traceable(name="query_cypher_subgraph", tags=["cypher", "subagent"])
def query_cypher_subgraph(user_question: str) -> str:
    """
    Query the Cypher subgraph with a user question.

    Args:
        user_question: The user's natural language question

    Returns:
        Formatted response with query results
    """
    subgraph = get_cypher_subgraph()

    # Initialize state
    initial_state = {
        "messages": [],
        "user_question": user_question,
        "generated_cypher": "",
        "cypher_explanation": "",
        "query_results": ""
    }

    # Run the subgraph
    result = subgraph.invoke(initial_state)

    # Extract the final response
    if result["messages"]:
        final_message = result["messages"][-1]
        return final_message.content
    else:
        return "Error: No response generated from Cypher subgraph"
