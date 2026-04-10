# Agentic Graph RAG for Healthcare Data

An AI-powered agentic system that enables natural language queries over the Synthea healthcare graph database using intelligent routing, pre-built tools, and dynamic Cypher query generation. Built with LangGraph, FastAPI, and a modern web interface.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Agent Tools & Architecture](#agent-tools--architecture)
- [Cypher Subagent Technical Guide](#cypher-subagent-technical-guide)
- [Patient Similarity Embeddings](#patient-similarity-embeddings)
- [Deployment](#deployment)
- [What Was Built](#what-was-built)
- [Testing & Validation](#testing--validation)

## Overview

This project implements an agentic Graph RAG (Retrieval-Augmented Generation) system for healthcare data analysis. It combines:

- **Intelligent Query Routing**: Automatically classifies queries and routes to appropriate handlers
- **Pre-built Tools**: Fast, optimized queries for common patient data operations
- **Dynamic Cypher Generation**: LLM-powered query construction for complex analytics
- **Graph Database**: Neo4j with Synthea synthetic patient data (5,885 patients, 1.2M+ encounters)
- **Configurable LLMs**: Support for Anthropic Claude and SambaNova models

The system intelligently determines whether to use pre-built queries or generate custom Cypher based on query complexity, optimizing for both performance and flexibility.

## Quick Start

Get up and running in 5 minutes!

### Prerequisites Checklist

- [ ] Python 3.11 or higher installed
- [ ] Neo4j running with synthea-sample database
  - Download the synthea sample from [here](https://drive.google.com/file/d/15WQWmEkHTB71H3OZ_3Kbb_OKBvM9tbVz/view?usp=drive_link)
  - Create a database called "synthea-sample" and load the data from the above `.dump` file
  - Install the **Graph Data Science (GDS) plugin** in Neo4j (required for patient similarity search)
    - In Neo4j Desktop: open your project → click the database → go to the **Plugins** tab → install **Graph Data Science Library**
    - For Neo4j AuraDB: enable GDS from the instance settings in the Aura console
- [ ] LLM API key (Anthropic or SambaNova)

### Installation Steps

1. **Navigate to Project Directory**
```bash
cd agentic_graph_rag/backend
```

2. **Create Virtual Environment**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install Dependencies**
```bash
uv pip install -r requirements.txt
```

4. **Configure Environment**
```bash
# Copy the example file
cp .env.example .env

# Edit backend/.env and add your API keys
# nano backend/.env  # or use your favorite editor
```

**Required in .env:**
```env
# API Keys - Add the key for your chosen provider
ANTHROPIC_API_DEV_KEY=sk-ant-your-key-here  # If using Anthropic
SAMBANOVA_API_KEY=your-key-here  # If using SambaNova

# Provider Configuration - Choose one (can be switched at runtime via UI)
PROVIDER=anthropic  # or 'sambanova'

# Provider-Specific Model Configurations
# Anthropic Configuration (Claude models)
ANTHROPIC_MAIN_AGENT_LLM=claude-sonnet-4-5-20250929
ANTHROPIC_ROUTER_LLM=claude-haiku-4-5-20251001
ANTHROPIC_CYPHER_AGENT_LLM=claude-sonnet-4-5-20250929

# SambaNova Configuration (DeepSeek models)
SAMBANOVA_MAIN_AGENT_LLM=DeepSeek-V3.1
SAMBANOVA_ROUTER_LLM=DeepSeek-V3.1
SAMBANOVA_CYPHER_AGENT_LLM=DeepSeek-V3.1

# Neo4j Database Configuration
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123

# Server Configuration (optional)
PORT=8000
MAX_AGENT_ITERATIONS=3

# Debug Logging (optional - set to 'true' to enable)
AGENT_DEBUG_LOGGING=false
TOOL_DEBUG_LOGGING=false
DATABASE_DEBUG_LOGGING=false
APP_DEBUG_LOGGING=false
```

5. **Test Connection**
```bash
python tests/test_connection.py
```

You should see:
```
✓ Successfully connected to Neo4j
✓ Query successful: Found 5885 patients
✓ All tests completed successfully!
```

6. **Start Server**

The following script runs tests for required prerequisites and then starts the server.

```bash
./start_server.sh
```

7. **Access the Application**

Open your browser and go to: **http://localhost:8000/app**

### Try These Sample Queries

1. "What procedures has Ethan had?" (matches by first name)
2. "Show me patients named John" (patient search)
3. "What medications is taking Smith?" (matches by last name)
4. "Find patients similar to John Smith" (patient similarity)
5. "Which providers treated the most patients?" (analytics query)
6. "How many patients are in the database?" (count aggregation)

## Key Features

- **Natural Language Queries**: Ask questions in plain English about patient records
- **LangGraph Agent**: Streamlined workflow with validation, tool selection, and self-synthesis
- **Query Validation**: Automatically validates query relevance to medical database before processing
- **Cypher Subagent**: Specialized AI agent (subgraph) for constructing custom Cypher queries within the execute_custom_query tool
- **Multi-Provider Support**:
  - Switch between Anthropic and SambaNova providers at runtime via UI dropdown
  - Provider-specific model configurations (main agent, validation, cypher agent)
  - Seamless provider switching without server restart
- **Dual-Mode Querying**:
  - Pre-built tools for common queries (patient procedures, conditions, medications, encounters, search, similarity)
  - Custom query generation tool with Cypher subgraph for complex analytics
- **Patient Similarity Matching**: Find patients with similar medical profiles using KNN embeddings based on:
  - Encounter patterns (types and frequency of visits)
  - Procedure history (types and frequency)
  - Medication history (prescriptions)
  - Demographics (age, expenses, healthcare utilization)
- **Flexible Patient Matching**: Query by first name, last name, or full name
- **Neo4j Integration**: Directly queries the Synthea-sample database
- **RESTful API**: FastAPI backend with automatic documentation
- **Modern UI**: Clean, responsive web interface with provider selection and graph visualization
- **Session Management**: Maintains conversation context across multiple queries
- **Query Transparency**: See all executed Cypher queries in collapsible widgets
- **Granular Debug Logging**: Four separate logging controls (Agent, Tool, Database, App)
- **Architecture Visualization**: Interactive LangGraph visualization showing workflow structure

## Architecture

### Backend (Python)
- **LangGraph**: Orchestrates the AI agent workflow with tool calling
- **LangChain**: Provides LLM integration and tool abstractions
- **FastAPI**: High-performance web server
- **Neo4j Driver**: Direct database connectivity
- **Multi-LLM Support**: Configurable LLM providers (Anthropic Claude, SambaNova DeepSeek)

### Frontend
- **Pure HTML/JavaScript**: No framework dependencies
- **Modern CSS**: Gradient design with smooth animations
- **Real-time Communication**: Fetch API for backend integration

### Database
- **Neo4j**: Graph database containing Synthea patient data
- **Database**: synthea-sample

## Project Structure

```
agentic_graph_rag/
├── backend/
│   ├── agent.py                           # Main LangGraph agent with 8 tools
│   ├── cypher_subagent.py                 # Specialized Cypher query generator (subgraph)
│   ├── neo4j_utils.py                     # Neo4j connection utilities
│   ├── server.py                          # FastAPI server
│   ├── patient_similarity_embeddings.py   # Patient similarity embeddings generator
│   ├── README_EMBEDDINGS.md               # Patient embeddings setup guide
│   ├── tests/                             # Test suite
│   │   ├── test_connection.py            # Neo4j connection test
│   │   ├── test_cypher.py                # Cypher generation tests
│   │   ├── test_subgraph.py              # Subgraph integration tests
│   │   └── test_query_tracking.py        # Query tracking system tests
│   ├── .env                               # Environment configuration (not in git)
│   └── .env.example                       # Environment variables template
├── frontend/
│   ├── index.html                         # Web chat interface
│   └── graph.html                         # LangGraph visualization
├── .gitignore                             # Git ignore rules
├── requirements.txt                       # Python dependencies
└── README.md                              # This file
```

## Running the Application

### Start the Server

From the `agentic_graph_rag` directory:

```bash
cd backend
python server.py
```

The server will start on `http://localhost:8000` (or the port specified in .env)

You should see:
```
╔══════════════════════════════════════════════════╗
║     Synthea Chatbot Server Starting...          ║
╚══════════════════════════════════════════════════╝

Server will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs
Health Check: http://localhost:8000/health
Chat Interface: http://localhost:8000/app
```

### Access the Application

- **Web Interface**: http://localhost:8000/app
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Usage

### Query Types

The chatbot supports two types of queries:

#### 1. Standard Queries (Pre-built Tools)
For common patient-specific questions, the agent uses pre-built tools with flexible name matching:

**Patient Procedures**
- "What procedures has Ethan had?" (matches first name)
- "Show me all procedures for John Smith" (matches full name)
- "What procedures did Smith have?" (matches last name)

**Patient Conditions**
- "What conditions does Sarah have?"
- "List all diagnoses for John Smith"
- "What's wrong with Thompson?" (last name match)

**Patient Medications**
- "What medications is David taking?"
- "Show me drugs prescribed to Maria Johnson"
- "What is Brown taking?" (last name match)

**Patient Search**
- "Find patients named John"
- "Search for patients with last name Smith"
- "Show me patients named Maria Garcia"

**Patient Encounters**
- "What encounters has Ethan had?"
- "Show me hospital visits for John Smith"
- "List encounters for Williams" (last name match)

**Patient Similarity**
- "Find patients similar to John Smith"
- "Who are the most similar patients to Sarah?"
- "Show me patients with similar medical profiles to Williams"

**Name Matching Features:**
- **First name only**: "Ethan" → matches any patient with first or last name containing "Ethan"
- **Last name only**: "Smith" → matches any patient with first or last name containing "Smith"
- **Full name**: "John Smith" → matches patients where full name contains "John Smith"

#### 2. Complex Queries (Cypher Subagent)
For analytics, aggregations, and complex questions, the agent uses a specialized Cypher subagent that constructs custom queries:

**Provider Analytics**
- "Which providers treated the most patients?"
- "Show me providers specializing in cardiology"
- "What's the average patient load per provider?"

**Procedure Analytics**
- "What's the most common procedure performed?"
- "How many procedures were done in 2023?"
- "Which procedures cost the most?"

**Organization Queries**
- "Which organizations have the highest patient volume?"
- "Show me all healthcare organizations in Boston"

**Time-Based Analysis**
- "How many emergency visits were there in 2023?"
- "Show me patient visits by month for last year"
- "What's the trend in wellness visits over time?"

**Multi-Entity Queries**
- "Show me patients who had both diabetes and hypertension"
- "Which providers work at multiple organizations?"
- "Find patients with more than 5 emergency visits"

**Aggregations**
- "What's the average age of patients with heart conditions?"
- "Count encounters by type"
- "Show me the distribution of conditions across patients"

### How It Works

#### Query Flow (Optimized Architecture)
1. **User Query**: You type a natural language question
2. **Validation**: Validation node checks if query is relevant to Synthea medical database
   - **Relevant queries** → Proceed to agent
   - **Irrelevant queries** → Return rejection message and end
3. **Agent Analysis**: Main LLM agent analyzes the query and selects appropriate tools
4. **Tool Execution**: Agent calls one or more tools based on the query:
   - **Pre-built tools** for common patient queries (procedures, conditions, medications, encounters, search)
   - **execute_custom_query tool** for complex analytics (triggers Cypher subgraph)
   - **get_database_schema tool** for schema information
5. **Result Synthesis**: Agent receives tool results and synthesizes them into natural language
   - Uses conditional synthesis instruction injection for clarity
   - Agent self-synthesizes without separate summary node
6. **Response**: Final answer returned to user with executed queries shown
7. **Context Maintenance**: Conversation history preserved for follow-ups

#### Cypher Subgraph Flow (within execute_custom_query tool)
When the agent selects the execute_custom_query tool for complex analytics:
1. **Subgraph Entry**: Tool invokes internal Cypher subgraph with user question
2. **Cypher Agent**: Specialized LLM with deep Synthea schema knowledge (400+ lines)
   - Analyzes the question and generates appropriate Cypher query
   - Includes LIMIT clauses, optimizations, and safety checks
3. **Query Execution**: execute_cypher_query tool runs the generated query
4. **Loop/Refinement**: Results return to Cypher Agent for potential refinement (conditional loop)
5. **Subgraph Exit**: Final results return to main agent for synthesis
6. **Query Transparency**: Generated Cypher query tracked and shown to user

**Key Benefits of This Architecture:**
- **Streamlined flow**: Validation → Agent → Tools → Agent (synthesis) → End
- **Fewer LLM calls**: 2-3 total (validation + agent tool selection + agent synthesis)
- **No separate router**: Agent directly selects tools using built-in tool-calling
- **No separate summary node**: Agent synthesizes its own tool results
- **Validation first**: Rejects irrelevant queries before processing
- **Cypher subgraph**: Deep query expertise isolated within execute_custom_query tool
- **Query tracking**: All queries tracked via Command pattern with reducers
- **Maintainability**: Clear separation of concerns with subgraph architecture

## API Endpoints

### POST /chat
Submit a chat message and get a response.

**Request:**
```json
{
  "message": "What procedures has Ethan had?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "Ethan has had the following procedures...",
  "session_id": "session-id",
  "executed_queries": [
    {
      "source": "tool",
      "query": "MATCH (p:Patient)...",
      "timestamp": "2025-01-30T10:30:00Z"
    }
  ]
}
```

### POST /chat/reset
Reset conversation history for a session.

**Query Parameter:**
- `session_id` (optional): Session to reset (default: "default")

### GET /provider
Get the current LLM provider configuration.

**Response:**
```json
{
  "provider": "anthropic",
  "models": {
    "main_agent": "claude-sonnet-4-5-20250929",
    "router": "claude-haiku-4-5-20251001",
    "cypher_agent": "claude-sonnet-4-5-20250929"
  }
}
```

### POST /provider
Switch the LLM provider at runtime.

**Request:**
```json
{
  "provider": "sambanova"
}
```

**Response:**
```json
{
  "provider": "sambanova",
  "message": "Switched to sambanova provider",
  "models": {
    "main_agent": "DeepSeek-V3.1",
    "router": "DeepSeek-V3.1",
    "cypher_agent": "DeepSeek-V3.1"
  }
}
```

### GET /health
Check server health status.

### GET /sessions
List all active sessions.

## Database Schema

The Synthea database follows this structure:

**Entities:**
- Patient: Demographic information
- Encounter: Healthcare visits
- Procedure: Medical procedures
- Condition: Medical conditions/diagnoses
- Drug: Medications
- Provider: Healthcare providers
- Organization: Healthcare organizations

**Key Relationships:**
- (Patient)-[:HAS_ENCOUNTER]->(Encounter)
- (Encounter)-[:HAS_PROCEDURE]->(Procedure)
- (Encounter)-[:HAS_CONDITION]->(Condition)
- (Encounter)-[:HAS_DRUG]->(Drug)

## Agent Tools & Architecture

The main LangGraph agent uses a streamlined architecture with validation, tool selection, and self-synthesis:

### Architecture Overview
```
START → Validation → Agent → Tools → Agent (synthesis) → END
                      ↓ (if not relevant)
                      END
```

### Main Graph Nodes
1. **Validation Node**: Entry point that validates query relevance to Synthea database
   - Uses lightweight validation LLM with structured output
   - Routes relevant queries to agent, rejects irrelevant queries
2. **Agent Node**: Main LLM with tool-calling capabilities
   - First invocation: Analyzes query and selects appropriate tools
   - Second invocation: Synthesizes tool results into natural language
   - No separate router or summary nodes needed

### Available Tools
The agent has access to 8 tools (all shown as individual nodes in the graph visualization):

#### Pre-built Patient Query Tools
1. **get_patient_procedures**: Retrieve patient procedures (limit: 30)
2. **get_patient_conditions**: Retrieve patient conditions (limit: 30)
3. **get_patient_medications**: Retrieve patient medications (limit: 30)
4. **get_patient_encounters**: Retrieve patient encounters (limit: 30)
5. **search_patients**: Search for patients by name (limit: 30)
6. **get_database_schema**: Get database schema information
7. **find_similar_patients**: Find patients with similar medical profiles using KNN embeddings (limit: 5)

#### Custom Analytics Tool (with Cypher Subgraph)
8. **execute_custom_query**: Handles complex analytics using internal Cypher subgraph
   - Contains its own specialized Cypher Agent (LLM with deep schema knowledge)
   - Internal execute_cypher_query tool for query execution
   - Unconditional edge from Cypher Agent → execute_cypher_query
   - Loop-back edge for query refinement
   - Handles: aggregations, analytics, multi-entity queries, time-based analysis

### Conditional Edges
- **From Validation**: Routes to Agent (relevant) or END (not relevant)
- **From Agent to Tools**: Conditional edges to each of the 8 tools based on query analysis
- **From Agent to END**: Direct edge when no tools needed
- **From Tools to Agent**: Return edges (dashed) for result synthesis

### Graph Structure (Current)
```
START
  ↓
Validation
  ├─(relevant)──→ Agent ─┬─→ get_patient_procedures ──┐
  │                      ├─→ get_patient_conditions ───┤
  │                      ├─→ get_patient_medications ──┤
  │                      ├─→ get_patient_encounters ───┤
  └─(not relevant)─→ END ├─→ search_patients ──────────├─→ Agent (synthesis) → END
                         ├─→ get_database_schema ──────┤
                         ├─→ find_similar_patients ────┤
                         ├─→ execute_custom_query ─────┘
                         │    (contains Cypher subgraph)
                         └─(no tools)──→ END

execute_custom_query (expanded):
  ┌─────────────────────────────────────┐
  │ Cypher Agent → execute_cypher_query │
  │       ↑               │              │
  │       └───(loop)──────┘              │
  └─────────────────────────────────────┘
```

### Architecture Visualization
View the interactive graph visualization at: **http://localhost:8000/graph**
- Shows all nodes (validation, agent, 8 tools, Cypher subgraph internals)
- Displays conditional edges (thick orange) vs regular edges (thin gray)
- Return edges (dashed) showing tool → agent flow
- Click nodes for detailed tooltips
- Expanded view of Cypher subgraph within execute_custom_query tool

## Cypher Subagent Technical Guide

### Overview

The Cypher Subagent is a specialized AI agent (implemented as a LangGraph subgraph) that constructs custom Cypher queries for complex analytics questions. It operates **within** the execute_custom_query tool as an internal subgraph.

### Architecture Flow

```
User Question
    ↓
Validation Node (Check Relevance)
    ↓ (if relevant)
Agent Node (Tool Selection)
    ↓ (selects execute_custom_query for analytics)
execute_custom_query Tool
    ↓
Cypher Subgraph Invocation
    ├─→ Cypher Agent (Generate Query)
    └─→ execute_cypher_query Tool
         ├─→ Neo4j Database
         └─→ Loop back to Cypher Agent (if needed)
    ↓
Results Return to Main Agent
    ↓
Agent Synthesizes Response
    ↓
User
```

### Key Features

#### 1. Deep Schema Knowledge
The Cypher subagent has a comprehensive 400+ line system prompt that includes:
- Complete node type definitions with all properties
- All relationship types and directions
- Multi-label node handling
- Common query patterns
- Cypher syntax guidelines
- Database statistics

#### 2. Safe Query Generation
- **Always includes LIMIT** clauses (default 50)
- **Validates** patient identification patterns
- **Optimizes** for performance
- **Explains** what the query does
- **Formats** results as readable tables

#### 3. Intelligent Tool Selection
The main agent knows when to select execute_custom_query (which triggers the Cypher subgraph):
- Analytics and aggregations
- Provider/organization queries
- Time-based analysis
- Multi-entity relationships
- Complex filtering/grouping
- Statistical queries and counts

### When the Subagraph is Used

#### Agent Selects execute_custom_query (triggers Cypher Subgraph)
- "Which providers treated the most patients?"
- "What's the most common procedure?"
- "How many emergency visits in 2023?"
- "Show patients with both diabetes and hypertension"
- "Average age of patients with heart conditions"
- "Count encounters by type"

#### Agent Selects Standard Tools
- "What procedures has Ethan766 had?" → get_patient_procedures
- "List medications for John" → get_patient_medications
- "Find patients named Smith" → search_patients
- "What encounters did Sarah have?" → get_patient_encounters

### Schema Knowledge in Subagent

The subagent knows about:

**Node Types (26 labels)**
- Patient (5,885 records)
- Encounter (1,274,720 records)
- Procedure, Condition, Drug
- Provider, Organization
- And 19 more...

**Relationships (18 types)**
- HAS_ENCOUNTER (1,274,720)
- HAS_DRUG (569,538)
- HAS_DIAGNOSIS (517,612)
- And 15 more...

**Properties for Each Node**
Example - Patient node:
- id, firstName, lastName
- birthDate, age
- expenses, income
- city, county, location
- And more...

**Multi-Label Handling**
Encounters have type labels:
- Base: Encounter
- Types: Ambulatory, Emergency, Inpatient, Wellness, etc.

Query pattern: `MATCH (e:Emergency)` or `WHERE labels(e) CONTAINS 'Emergency'`

### Query Generation Process

#### Step 1: Analyze Question
```
User: "Which providers treated the most patients?"
```

#### Step 2: Generate Cypher
```cypher
MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROVIDER]->(prov:Provider)
RETURN
    prov.name AS provider_name,
    prov.speciality AS specialty,
    count(DISTINCT p) AS patient_count
ORDER BY patient_count DESC
LIMIT 20
```

#### Step 3: Explain Query
```
This query finds all providers, counts distinct patients they've treated,
and orders by patient count to show the busiest providers.
```

#### Step 4: Execute & Format
```
Query Results (20 records):

provider_name | specialty | patient_count
------------------------------------------
Dr. Smith     | Cardiology | 145
Dr. Johnson   | General    | 132
...

Cypher Query Used:
[query shown above]
```

### Implementation Details

#### File Structure
```
backend/
├── agent.py                 # Main agent with validation, tools, and execute_custom_query
├── cypher_subagent.py       # Cypher query generator subgraph (invoked by execute_custom_query)
└── neo4j_utils.py          # Database utilities and execute_custom_cypher method
```

#### Key Components

**1. execute_custom_query Tool** ([agent.py](backend/agent.py))
```python
@tool
def execute_custom_query(user_question: str, tool_call_id: ...) -> Command:
    """
    Execute a custom database query for questions that don't fit standard tools.
    This tool uses a specialized Cypher subgraph to construct and execute queries.

    Invokes the Cypher subgraph, extracts results, and returns as Command.
    """
```

**2. Cypher Subgraph** ([cypher_subagent.py](backend/cypher_subagent.py))
```python
def get_cypher_subgraph():
    """
    Returns the compiled Cypher subgraph (singleton).

    Subgraph structure:
    - cypher_generator node: LLM that generates Cypher queries
    - execute_query node: ToolNode that executes queries
    - Conditional routing based on tool calls
    - Loop back for query refinement
    """
```

**3. Cypher Agent Node** ([cypher_subagent.py](backend/cypher_subagent.py))
```python
def call_cypher_generator(state: CypherSubgraphState) -> dict:
    """
    LLM-based node with 400+ line schema prompt.
    Generates Cypher queries using execute_cypher_query tool.
    Returns messages with generated query for tracking.
    """
```

**4. execute_cypher_query Tool** ([cypher_subagent.py](backend/cypher_subagent.py))
```python
@tool
def execute_cypher_query(cypher_query: str) -> str:
    """
    Executes generated Cypher query against Neo4j.
    Returns formatted table results.
    Called by Cypher Agent within subgraph.
    """
```

### Benefits of This Architecture

#### 1. Separation of Concerns
- **Main Agent**: Selects tools, maintains conversation, synthesizes responses
- **Validation Node**: Filters irrelevant queries before processing
- **Cypher Subagent**: Isolated expert in query construction within execute_custom_query tool
- **Tools**: Each has single responsibility (procedures, conditions, medications, etc.)

#### 2. Cost Optimization
- Validation: Fast relevance check prevents processing irrelevant queries
- Standard queries: Fast, minimal LLM usage (pre-built queries)
- Complex queries: Cypher subagent LLM only used when execute_custom_query tool is selected
- Fewer LLM calls: No separate router or summary nodes (2-3 calls total)

#### 3. Maintainability
- Schema changes: Update Cypher subagent prompt only
- New query types: Add examples to subagent system prompt
- Main agent: Stays focused on tool selection and synthesis
- Tool addition: Just add @tool decorated function to tools list

#### 4. Safety
- Validation prevents irrelevant query processing
- Queries validated before execution in subgraph
- LIMIT clauses enforced in Cypher generation
- Error handling at multiple levels
- Command pattern with reducers for state management

#### 5. Transparency
- All queries tracked via executed_queries state
- Generated Cypher queries shown to user
- Query source tracked (which tool/function)
- Graph visualization available at /graph endpoint

### Testing the Subagent

```bash
# Ensure environment is configured (backend/.env)
# Then run tests
python test_cypher_subagent.py
```

Tests verify:
1. Query generation works
2. Cypher execution works
3. End-to-end flow works

#### Example Test Output
```
Testing Cypher Subagent - Query Generation
------------------------------------------------------------
Question: Which providers treated the most patients?
✓ Query generated successfully

Cypher Query:
MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROVIDER]->(prov:Provider)
RETURN prov.name AS provider_name, count(DISTINCT p) AS patient_count
ORDER BY patient_count DESC
LIMIT 20

Explanation:
Finds all providers and counts distinct patients they've treated.
```

### Extending the Subagent

#### Adding New Query Patterns

Edit [cypher_subagent.py](backend/cypher_subagent.py) and update `SYNTHEA_SCHEMA_DETAILED`:

```python
SYNTHEA_SCHEMA_DETAILED = """
...existing schema...

## NEW QUERY PATTERNS

### Finding Care Plans
11. Get care plans for patient:
    MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)<-[:CARE_PLAN_START]-(cp:CarePlan)
    WHERE p.firstName = 'Name'
    RETURN cp.code, e.date
"""
```

#### Adding Safety Rules

Update the system prompt in `generate_cypher_query()`:

```python
## ADDITIONAL SAFETY RULES

8. **Never delete data** - Only use MATCH and RETURN
9. **Validate dates** - Use datetime() function
10. **Check for null** - Use WHERE field IS NOT NULL
```

### Performance Characteristics

- **Validation**: <1 second (lightweight validation LLM)
- **Tool Selection**: 2-4 seconds (main agent LLM call)
- **Standard Tool Execution**: <1 second (pre-built queries)
- **Cypher Query Generation**: 2-5 seconds (Cypher subagent LLM call within execute_custom_query)
- **Query Execution**: <1 second (Neo4j)
- **Result Synthesis**: 2-4 seconds (main agent LLM call)
- **Total Time (Standard)**: 3-6 seconds (validation + agent + tool + synthesis)
- **Total Time (Complex)**: 5-10 seconds (validation + agent + Cypher subgraph + synthesis)

### Security Considerations

1. **No User Input in Cypher**: User questions passed to LLM, not directly to Cypher
2. **Read-Only Queries**: Subagent instructed to only generate MATCH/RETURN
3. **LIMIT Enforcement**: Prevents large result sets
4. **Error Handling**: Database errors don't expose internals
5. **Query Validation**: Subagent validates before execution

### Future Enhancements

Possible improvements:
1. **Query Caching**: Cache common query patterns
2. **Query Optimization**: Learn from slow queries
3. **Multi-Step Queries**: Break complex questions into multiple queries
4. **Query Validation**: Pre-validate with Cypher parser
5. **Feedback Loop**: Learn from successful/failed queries
6. **Query Templates**: Store and reuse common patterns

### Summary

The Cypher Subagent (implemented as a subgraph within execute_custom_query tool) provides powerful analytics capabilities while maintaining:
- **Safety**: Validated, read-only queries with enforced LIMIT clauses
- **Efficiency**: Only invoked when agent selects execute_custom_query tool
- **Transparency**: Generated queries tracked and shown to user
- **Isolation**: Separate subgraph with own state and routing logic
- **Maintainability**: Deep schema knowledge isolated from main agent
- **Extensibility**: Easy to add new query patterns to subagent prompt

This streamlined architecture (validation → agent → tools → synthesis) combines:
- **Fast pre-built tools** for common patient queries
- **Flexible Cypher subgraph** (within execute_custom_query) for complex analytics
- **Validation** to filter irrelevant queries
- **Self-synthesis** by the agent without separate summary node
- **Query tracking** via Command pattern with reducers
- **Visual representation** available at /graph endpoint

## Patient Similarity Embeddings

### Overview

The patient similarity feature uses Neo4j Graph Data Science (GDS) library to generate high-dimensional embeddings that capture patient similarity based on multiple medical and demographic factors. This enables finding patients with similar medical journeys, which is useful for:

- **Cohort identification**: Find similar patients for clinical studies
- **Treatment planning**: Identify patients with comparable medical profiles
- **Pattern discovery**: Understand common patient trajectories
- **Personalized insights**: Compare a patient's journey to similar cases

### How It Works

The similarity system uses **KNN (K-Nearest Neighbors)** embeddings that combine:

1. **Encounter Similarity (256D)**: Based on types and frequency of medical visits
2. **Procedure Similarity (256D)**: Based on types and frequency of procedures
3. **Drug Similarity (256D)**: Based on types and frequency of medications
4. **Demographic Features**: Age, total encounters, expenses, income, etc.

These are combined into a **775-dimensional feature space** that is then reduced to **256-dimensional KNN embeddings** using FastRP (Fast Random Projection).

### Setup Instructions

The patient similarity embeddings require the **Neo4j Graph Data Science (GDS) plugin** to be installed. See [backend/README_EMBEDDINGS.md](backend/README_EMBEDDINGS.md) for detailed setup instructions.

**Quick Setup:**
```bash
# Install GDS plugin in Neo4j (via Neo4j Desktop or manual installation)
# Then generate embeddings:
cd backend
source ../.venv/bin/activate
python patient_similarity_embeddings.py
```

This will:
1. Create aggregated patient relationships
2. Generate similarity embeddings for encounters, procedures, and medications
3. Create combined KNN similarity embeddings
4. Establish similarity relationships between patients

**Processing Time**: 10-30 minutes depending on database size (for 5,885 patients)

### Using the Tool

Once embeddings are generated, the agent can find similar patients:

**Example Queries:**
- "Find patients similar to John Smith"
- "Who are the most similar patients to Sarah?"
- "Show me patients with similar medical profiles to Williams"

**Tool Response Includes:**
- Similarity score (0.0 to 1.0)
- Patient demographics (age)
- Healthcare utilization metrics (total encounters, procedures, medications)
- Total expenses

### Technical Details

**Similarity Relationship**: `KNN_SIMILARITY`
- Created between patients with similar medical profiles
- Contains `similarityScore` property (higher = more similar)
- Top 25 nearest neighbors stored for each patient

**Embedding Properties**:
- `encounterSimilarityEmbed`: 256D vector
- `procedureSimilarityEmbed`: 256D vector
- `drugSimilarityEmbed`: 256D vector
- `knnSimilarityEmbed`: 256D vector (recommended for queries)

**Query Example** (executed by the tool):
```cypher
MATCH (p:Patient)-[sim:KNN_SIMILARITY]-(similar:Patient)
WHERE p.firstName + ' ' + p.lastName CONTAINS $patient_name
RETURN similar
ORDER BY sim.similarityScore DESC
LIMIT 5
```

### Configuration

The embeddings can be customized in [backend/patient_similarity_embeddings.py](backend/patient_similarity_embeddings.py):

```python
embeddings_gen.generate_all_embeddings(
    embedding_dim=256,           # Dimension of embeddings
    node_similarity_top_k=10,    # Top K for node similarity
    knn_top_k=25,                # Top K for KNN (neighbors per patient)
    similarity_cutoff=0.01       # Minimum similarity threshold
)
```

### Performance Considerations

- **First-time setup**: 10-30 minutes to generate embeddings
- **Query performance**: Sub-second (queries use pre-computed embeddings)
- **Memory usage**: Depends on database size and embedding dimensions
- **Embeddings persistence**: Stored in Neo4j, no regeneration needed unless data changes

For more details, see [backend/README_EMBEDDINGS.md](backend/README_EMBEDDINGS.md).

## Deployment

### Deploying to Another Computer

1. **Copy the entire `agentic_graph_rag` directory**

2. **Install dependencies** (as described in Installation section)

3. **Configure environment variables** in `.env` file

4. **Ensure Neo4j access** - Update NEO4J_URI if database is on a different host

5. **Run the server**

### Production Considerations

**Infrastructure**:
- Use a production ASGI server (Gunicorn with Uvicorn workers)
- Set up proper CORS origins in `server.py`
- Use HTTPS/SSL
- Configure reverse proxy (Nginx/Caddy)

**Security & Access**:
- Implement authentication/authorization
- Add rate limiting (per API key/IP)
- API key management
- Input validation/sanitization

**Operations**:
- Environment-specific configuration
- Logging and monitoring
- Database connection pooling
- Query result caching
- Cost tracking (LLM API usage)

**Current State**: ✅ Functional prototype with error handling, session management, and complete documentation

## Testing & Validation

The project includes a comprehensive test suite covering all major components:

### Test Coverage

**Connection & Database (test_connection.py)**
- ✅ Neo4j connection tested successfully
- ✅ Query functions tested with real data
- ✅ Found 5,885 patients in database

**Cypher Generation (test_cypher.py)**
- ✅ Cypher query generation tested
- ✅ Query validation and safety checks
- ✅ LIMIT clause enforcement

**Subgraph Integration (test_subgraph.py)**
- ✅ Cypher subagent query generation tested
- ✅ Subgraph invocation and state management
- ✅ End-to-end subgraph flow

**Complete System (test_query_tracking.py)**
- ✅ All 8 tools tested individually:
  - Standard tools: procedures, conditions, medications, encounters, search, schema
  - Similarity tool: find_similar_patients with KNN embeddings
  - Custom analytics: execute_custom_query with Cypher subgraph
- ✅ Query tracking system validated
- ✅ Command pattern and reducers tested
- ✅ Agent initialization and routing working
- ✅ API endpoints functional

### Running Tests

```bash
# Navigate to tests directory
cd agentic_graph_rag/backend/tests

# Run all tests
agentic_graph_rag/.venv/bin/pytest -v

# Run specific test
agentic_graph_rag/.venv/bin/pytest test_query_tracking.py::test_get_patient_procedures_tool -v -s

# Run with debug logging
export TOOL_DEBUG_LOGGING=true && agentic_graph_rag/.venv/bin/pytest test_query_tracking.py -v -s
```

