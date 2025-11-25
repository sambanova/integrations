"""
Neo4j database connection and query utilities for Synthea chatbot.
"""
import os
import logging
from neo4j import GraphDatabase
from typing import List, Dict, Any, Tuple
from langsmith.run_helpers import traceable


# Configure logger for database operations
db_logger = logging.getLogger("synthea_database")
if os.getenv("AGENT_DEBUG_LOGGING", "false").lower() == "true":
    db_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
    db_logger.addHandler(handler)
    db_logger.propagate = False
else:
    db_logger.setLevel(logging.WARNING)


class Neo4jConnection:
    """Manages Neo4j database connections and queries."""

    def __init__(self, uri: str = None, username: str = None, password: str = None, database: str = "synthea-sample"):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (defaults to neo4j://127.0.0.1:7687)
            username: Database username (defaults to 'neo4j')
            password: Database password (defaults to 'password123')
            database: Database name (defaults to 'synthea-sample')
        """
        self.uri = uri or os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password123")
        self.database = database
        self.driver = None

    def connect(self):
        """Establish connection to Neo4j database."""
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        return self

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()

    @traceable(name="execute_neo4j_query", tags=["neo4j", "database"])
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Execute a Cypher query and return results along with query information.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Tuple of (results, query, parameters) where:
            - results: List of result records as dictionaries
            - query: The executed Cypher query string
            - parameters: The query parameters used
        """
        if not self.driver:
            db_logger.debug("DATABASE: Connecting to Neo4j...")
            self.connect()

        db_logger.debug(f"DATABASE: Executing query: {query[:200]}...")
        db_logger.debug(f"DATABASE: Parameters: {parameters}")

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                records = [dict(record) for record in result]
                db_logger.debug(f"DATABASE: Query returned {len(records)} records")
                return (records, query, parameters or {})
        except Exception as e:
            db_logger.error(f"DATABASE ERROR: {str(e)}")
            raise

    @traceable(name="get_patient_procedures_db", run_type="tool", tags=["neo4j", "patient", "procedures"])
    def get_patient_procedures(self, patient_name: str, limit: int = 30) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Get procedures for a specific patient, limited to most recent entries.

        Args:
            patient_name: Patient name (can be first name, last name, or full name)
            limit: Maximum number of results to return (default: 30)

        Returns:
            Tuple of (results, query, parameters)
        """
        # Check if the name contains a space (indicating a full name search)
        has_space = ' ' in patient_name.strip()

        if has_space:
            # Full name search - match against concatenated first + last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc)
            WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                proc.description AS procedure_description,
                e.date AS encounter_date,
                e.description AS encounter_type
            ORDER BY e.date DESC
            LIMIT $limit
            """
        else:
            # Single name search - match against first name OR last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc)
            WHERE toLower(p.firstName) CONTAINS toLower($patient_name)
               OR toLower(p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                proc.description AS procedure_description,
                e.date AS encounter_date,
                e.description AS encounter_type
            ORDER BY e.date DESC
            LIMIT $limit
            """

        return self.execute_query(query, {"patient_name": patient_name, "limit": limit})

    @traceable(name="get_patient_conditions_db", run_type="tool", tags=["neo4j", "patient", "conditions"])
    def get_patient_conditions(self, patient_name: str, limit: int = 30) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Get conditions/diagnoses for a specific patient, limited to most recent entries.

        Args:
            patient_name: Patient name (can be first name, last name, or full name)
            limit: Maximum number of results to return (default: 30)

        Returns:
            Tuple of (results, query, parameters)
        """
        # Check if the name contains a space (indicating a full name search)
        has_space = ' ' in patient_name.strip()

        if has_space:
            # Full name search - match against concatenated first + last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DIAGNOSIS]->(cond)
            WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                cond.description AS condition_description,
                e.date AS encounter_date
            ORDER BY e.date DESC
            LIMIT $limit
            """
        else:
            # Single name search - match against first name OR last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DIAGNOSIS]->(cond)
            WHERE toLower(p.firstName) CONTAINS toLower($patient_name)
               OR toLower(p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                cond.description AS condition_description,
                e.date AS encounter_date
            ORDER BY e.date DESC
            LIMIT $limit
            """

        return self.execute_query(query, {"patient_name": patient_name, "limit": limit})

    @traceable(name="get_patient_medications_db", run_type="tool", tags=["neo4j", "patient", "medications"])
    def get_patient_medications(self, patient_name: str, limit: int = 30) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Get medications for a specific patient, limited to most recent entries.

        Args:
            patient_name: Patient name (can be first name, last name, or full name)
            limit: Maximum number of results to return (default: 30)

        Returns:
            Tuple of (results, query, parameters)
        """
        # Check if the name contains a space (indicating a full name search)
        has_space = ' ' in patient_name.strip()

        if has_space:
            # Full name search - match against concatenated first + last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DRUG]->(drug:Drug)
            WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                drug.description AS medication,
                e.date AS prescribed_date
            ORDER BY e.date DESC
            LIMIT $limit
            """
        else:
            # Single name search - match against first name OR last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_DRUG]->(drug:Drug)
            WHERE toLower(p.firstName) CONTAINS toLower($patient_name)
               OR toLower(p.lastName) CONTAINS toLower($patient_name)
            RETURN DISTINCT
                p.firstName + ' ' + p.lastName AS patient_name,
                drug.description AS medication,
                e.date AS prescribed_date
            ORDER BY e.date DESC
            LIMIT $limit
            """

        return self.execute_query(query, {"patient_name": patient_name, "limit": limit})

    @traceable(name="get_patient_encounters_db", run_type="tool", tags=["neo4j", "patient", "encounters"])
    def get_patient_encounters(self, patient_name: str, limit: int = 30) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Get encounters for a specific patient, limited to most recent entries.

        Args:
            patient_name: Patient name (can be first name, last name, or full name)
            limit: Maximum number of results to return (default: 30)

        Returns:
            Tuple of (results, query, parameters)
        """
        # Check if the name contains a space (indicating a full name search)
        has_space = ' ' in patient_name.strip()

        if has_space:
            # Full name search - match against concatenated first + last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
            WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($patient_name)
            RETURN
                p.firstName + ' ' + p.lastName AS patient_name,
                e.description AS encounter_type,
                e.date AS encounter_date,
                labels(e) AS encounter_labels
            ORDER BY e.date DESC
            LIMIT $limit
            """
        else:
            # Single name search - match against first name OR last name
            query = """
            MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
            WHERE toLower(p.firstName) CONTAINS toLower($patient_name)
               OR toLower(p.lastName) CONTAINS toLower($patient_name)
            RETURN
                p.firstName + ' ' + p.lastName AS patient_name,
                e.description AS encounter_type,
                e.date AS encounter_date,
                labels(e) AS encounter_labels
            ORDER BY e.date DESC
            LIMIT $limit
            """

        return self.execute_query(query, {"patient_name": patient_name, "limit": limit})

    @traceable(name="search_patients_db", run_type="tool", tags=["neo4j", "patient", "search"])
    def search_patients(self, name: str = None, limit: int = 30) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        Search for patients by name, sorted by relevance using Levenshtein distance.

        Args:
            name: Patient name or partial name (can be first name, last name, or full name)
            limit: Maximum number of results to return (default: 30)

        Returns:
            Tuple of (results, query, parameters)
        """
        if name:
            # Check if the name contains a space (indicating a full name search)
            has_space = ' ' in name.strip()

            if has_space:
                # Full name search - match against concatenated first + last name
                query = """
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
                WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($name)
                WITH p, max(e.date) AS latest_encounter
                RETURN p.id AS patient_id,
                       p.firstName + ' ' + p.lastName AS patient_name,
                       p.birthDate AS birth_date,
                       latest_encounter
                ORDER BY CASE WHEN latest_encounter IS NULL THEN 1 ELSE 0 END, latest_encounter DESC
                LIMIT 200
                """
            else:
                # Single name search - match against first name OR last name
                query = """
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
                WHERE toLower(p.firstName) CONTAINS toLower($name)
                   OR toLower(p.lastName) CONTAINS toLower($name)
                WITH p, max(e.date) AS latest_encounter
                RETURN p.id AS patient_id,
                       p.firstName + ' ' + p.lastName AS patient_name,
                       p.birthDate AS birth_date,
                       latest_encounter
                ORDER BY CASE WHEN latest_encounter IS NULL THEN 1 ELSE 0 END, latest_encounter DESC
                LIMIT 200
                """

            results, executed_query, params = self.execute_query(query, {"name": name})

            # Calculate Levenshtein distance and sort by similarity
            from difflib import SequenceMatcher

            def levenshtein_similarity(s1: str, s2: str) -> float:
                """Calculate similarity ratio (0-1, higher is more similar)."""
                return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

            search_name = name.lower()

            # Score each result based on full patient name similarity
            for result in results:
                result['_similarity_score'] = levenshtein_similarity(search_name, result['patient_name'])

            # Sort by similarity score (descending) and take top N
            results.sort(key=lambda x: x['_similarity_score'], reverse=True)
            results = results[:limit]

            # Remove internal fields
            for result in results:
                del result['_similarity_score']
                if 'latest_encounter' in result:
                    del result['latest_encounter']

            return (results, executed_query, params)
        else:
            # No name provided, just return recent patients
            query = """
            MATCH (p:Patient)
            OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
            WITH p, max(e.date) AS latest_encounter
            RETURN p.id AS patient_id,
                   p.firstName + ' ' + p.lastName AS patient_name,
                   p.birthDate AS birth_date
            ORDER BY CASE WHEN latest_encounter IS NULL THEN 1 ELSE 0 END, latest_encounter DESC
            LIMIT $limit
            """
            return self.execute_query(query, {"limit": limit})

    @traceable(name="execute_custom_cypher", run_type="tool", tags=["neo4j", "cypher", "custom"])
    def execute_custom_cypher(self, cypher_query: str) -> Dict[str, Any]:
        """
        Execute a custom Cypher query and return formatted results.
        Used by the Cypher subagent for complex queries.

        Args:
            cypher_query: Valid Cypher query string

        Returns:
            Dictionary with success status, results, query info, and any error messages
        """
        try:
            # Execute the query
            results, executed_query, params = self.execute_query(cypher_query)

            if not results:
                return {
                    "success": True,
                    "results": [],
                    "message": "Query executed successfully but returned no results.",
                    "result_count": 0,
                    "query": executed_query,
                    "params": params
                }

            return {
                "success": True,
                "results": results,
                "message": f"Query executed successfully. Found {len(results)} results.",
                "result_count": len(results),
                "query": executed_query,
                "params": params
            }

        except Exception as e:
            return {
                "success": False,
                "results": [],
                "message": f"Error executing query: {str(e)}",
                "error": str(e),
                "result_count": 0
            }

    def get_database_schema(self) -> str:
        """
        Get a text description of the database schema.

        Returns:
            Schema description as a string
        """
        query = """
        CALL db.schema.visualization()
        """
        # For now, return a static schema description based on the notebook
        return """
        Synthea Database Schema:

        Main Entities:
        - Patient: Stores patient demographic information (firstName, lastName, birthDate, etc.)
        - Encounter: Healthcare encounters (date, description, type, totalCost - financial cost of encounter)
        - Procedure: Medical procedures performed
        - Condition: Medical conditions/diagnoses
        - Drug: Medications prescribed
        - Provider: Healthcare providers
        - Organization: Healthcare organizations

        Key Relationships:
        - (Patient)-[:HAS_ENCOUNTER]->(Encounter)
        - (Encounter)-[:HAS_PROCEDURE]->(Procedure)
        - (Encounter)-[:HAS_CONDITION]->(Condition)
        - (Encounter)-[:HAS_DRUG]->(Drug)
        - (Encounter)-[:HAS_PROVIDER]->(Provider)
        - (Encounter)-[:HAS_ORGANIZATION]->(Organization)

        Common Query Patterns:
        - To find patient procedures: Patient -> Encounter -> Procedure
        - To find patient conditions: Patient -> Encounter -> Condition
        - To find patient medications: Patient -> Encounter -> Drug
        - To find treatment costs: Patient -> Encounter (access totalCost property)
        """
