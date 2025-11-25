"""
Unit tests for Neo4j database utilities.
Tests all functions in neo4j_utils.py directly without LLM calls.

This test suite verifies:
1. Database connection and query execution
2. All patient-related query functions (procedures, medications, conditions, encounters)
3. Patient search functionality
4. Custom Cypher query execution
5. Schema retrieval
6. Query tracking functionality

Tests use actual Neo4j database connection and verify:
- Queries return valid data structures
- Queries handle both patient IDs and first names
- Queries return expected fields
- Error handling works correctly
"""
import pytest
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append('..')

from neo4j_utils import Neo4jConnection

# Load environment variables
load_dotenv()


@pytest.fixture(scope="module")
def db_connection():
    """
    Create a database connection that persists for all tests in the module.
    This avoids creating/closing connections for each test.
    """
    conn = Neo4jConnection()
    conn.connect()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def sample_patient_id(db_connection):
    """
    Get a sample patient ID from the database to use in tests.
    This ensures we're testing with real data that exists.
    """
    query = "MATCH (p:Patient) RETURN p.id AS patient_id LIMIT 1"
    results = db_connection.execute_query(query)

    if not results:
        pytest.skip("No patients found in database - cannot run tests")

    return results[0]['patient_id']


@pytest.fixture(scope="module")
def sample_patient_name(db_connection):
    """
    Get a sample patient first name from the database to use in tests.
    """
    query = "MATCH (p:Patient) RETURN p.firstName AS firstName LIMIT 1"
    results = db_connection.execute_query(query)

    if not results:
        pytest.skip("No patients found in database - cannot run tests")

    return results[0]['firstName']


class TestDatabaseConnection:
    """Test basic database connection and query execution."""

    def test_connection_initialization(self):
        """Test that connection can be initialized with default parameters."""
        conn = Neo4jConnection()
        assert conn.uri is not None
        assert conn.username is not None
        assert conn.password is not None
        assert conn.database == "synthea-sample"

    def test_connection_connect_and_close(self):
        """Test that connection can be established and closed."""
        conn = Neo4jConnection()
        conn.connect()
        assert conn.driver is not None
        conn.close()

    def test_execute_query_basic(self, db_connection):
        """Test basic query execution returns results."""
        query = "MATCH (p:Patient) RETURN count(p) AS patient_count"
        results = db_connection.execute_query(query)

        assert isinstance(results, list)
        assert len(results) > 0
        assert 'patient_count' in results[0]
        assert isinstance(results[0]['patient_count'], int)

    def test_execute_query_with_parameters(self, db_connection, sample_patient_id):
        """Test query execution with parameters."""
        query = "MATCH (p:Patient {id: $patient_id}) RETURN p.firstName AS firstName"
        results = db_connection.execute_query(query, {"patient_id": sample_patient_id})

        assert isinstance(results, list)
        # May return empty if patient_id doesn't exist, but should not error

    def test_query_tracking(self, db_connection):
        """Test that queries are tracked in last_executed_query."""
        query = "MATCH (p:Patient) RETURN count(p) AS count LIMIT 1"
        params = {"test_param": "test_value"}

        db_connection.execute_query(query, params)

        assert db_connection.last_executed_query == query
        assert db_connection.last_query_params == params


class TestSearchPatients:
    """Test patient search functionality."""

    def test_search_patients_with_name(self, db_connection):
        """Test searching for patients by name."""
        # First get a real patient name
        query = "MATCH (p:Patient) RETURN p.firstName AS name LIMIT 1"
        result = db_connection.execute_query(query)

        if not result:
            pytest.skip("No patients in database")

        patient_name = result[0]['name']

        # Now search for that patient
        results = db_connection.search_patients(name=patient_name)

        assert isinstance(results, list)
        assert len(results) > 0
        assert 'patient_id' in results[0]
        assert 'patient_name' in results[0]
        assert 'birth_date' in results[0]

        # Verify the name appears in results
        assert any(patient_name.lower() in r['patient_name'].lower() for r in results)

    def test_search_patients_partial_name(self, db_connection):
        """Test searching with partial name."""
        # Search for "John" - common name likely to exist
        results = db_connection.search_patients(name="a")  # Single letter should match many

        assert isinstance(results, list)
        # Should return up to 10 results (LIMIT 10)
        assert len(results) <= 10

        if results:
            assert 'patient_id' in results[0]
            assert 'patient_name' in results[0]

    def test_search_patients_no_name(self, db_connection):
        """Test searching without providing a name (should return first 10 patients)."""
        results = db_connection.search_patients(name=None)

        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 10
        assert 'patient_id' in results[0]
        assert 'patient_name' in results[0]
        assert 'birth_date' in results[0]

    def test_search_patients_case_insensitive(self, db_connection):
        """Test that search is case-insensitive."""
        # Get a patient name
        query = "MATCH (p:Patient) WHERE p.firstName IS NOT NULL RETURN p.firstName AS name LIMIT 1"
        result = db_connection.execute_query(query)

        if not result or not result[0]['name']:
            pytest.skip("No patients with names in database")

        patient_name = result[0]['name']

        # Search with uppercase
        results_upper = db_connection.search_patients(name=patient_name.upper())
        # Search with lowercase
        results_lower = db_connection.search_patients(name=patient_name.lower())

        # Both should return results
        assert len(results_upper) > 0
        assert len(results_lower) > 0


class TestPatientProcedures:
    """Test get_patient_procedures functionality."""

    def test_get_patient_procedures_by_id(self, db_connection, sample_patient_id):
        """Test getting procedures by patient ID."""
        results = db_connection.get_patient_procedures(sample_patient_id)

        assert isinstance(results, list)

        # If results exist, verify structure
        if results:
            assert 'patient_name' in results[0]
            assert 'procedure_description' in results[0]
            assert 'encounter_date' in results[0]
            assert 'encounter_type' in results[0]

    def test_get_patient_procedures_by_name(self, db_connection, sample_patient_name):
        """Test getting procedures by patient first name."""
        results = db_connection.get_patient_procedures(sample_patient_name)

        assert isinstance(results, list)

        # If results exist, verify structure
        if results:
            assert 'patient_name' in results[0]
            assert sample_patient_name in results[0]['patient_name']

    def test_get_patient_procedures_nonexistent_patient(self, db_connection):
        """Test getting procedures for non-existent patient returns empty list."""
        results = db_connection.get_patient_procedures("NONEXISTENT_PATIENT_12345")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_get_patient_procedures_query_tracking(self, db_connection, sample_patient_id):
        """Test that procedure query is tracked."""
        db_connection.get_patient_procedures(sample_patient_id)

        assert db_connection.last_executed_query is not None
        assert "HAS_PROCEDURE" in db_connection.last_executed_query
        assert db_connection.last_query_params == {"patient_id": sample_patient_id}


class TestPatientConditions:
    """Test get_patient_conditions functionality."""

    def test_get_patient_conditions_by_id(self, db_connection, sample_patient_id):
        """Test getting conditions by patient ID."""
        results = db_connection.get_patient_conditions(sample_patient_id)

        assert isinstance(results, list)

        # If results exist, verify structure
        if results:
            assert 'patient_name' in results[0]
            assert 'condition_description' in results[0]
            assert 'encounter_date' in results[0]

    def test_get_patient_conditions_by_name(self, db_connection, sample_patient_name):
        """Test getting conditions by patient first name."""
        results = db_connection.get_patient_conditions(sample_patient_name)

        assert isinstance(results, list)

        if results:
            assert 'patient_name' in results[0]
            assert sample_patient_name in results[0]['patient_name']

    def test_get_patient_conditions_nonexistent_patient(self, db_connection):
        """Test getting conditions for non-existent patient returns empty list."""
        results = db_connection.get_patient_conditions("NONEXISTENT_PATIENT_12345")

        assert isinstance(results, list)
        assert len(results) == 0


class TestPatientMedications:
    """Test get_patient_medications functionality."""

    def test_get_patient_medications_by_id(self, db_connection, sample_patient_id):
        """Test getting medications by patient ID."""
        results = db_connection.get_patient_medications(sample_patient_id)

        assert isinstance(results, list)

        if results:
            assert 'patient_name' in results[0]
            assert 'medication' in results[0]
            assert 'prescribed_date' in results[0]

    def test_get_patient_medications_by_name(self, db_connection, sample_patient_name):
        """Test getting medications by patient first name."""
        results = db_connection.get_patient_medications(sample_patient_name)

        assert isinstance(results, list)

        if results:
            assert 'patient_name' in results[0]
            assert sample_patient_name in results[0]['patient_name']

    def test_get_patient_medications_nonexistent_patient(self, db_connection):
        """Test getting medications for non-existent patient returns empty list."""
        results = db_connection.get_patient_medications("NONEXISTENT_PATIENT_12345")

        assert isinstance(results, list)
        assert len(results) == 0


class TestPatientEncounters:
    """Test get_patient_encounters functionality."""

    def test_get_patient_encounters_by_id(self, db_connection, sample_patient_id):
        """Test getting encounters by patient ID."""
        results = db_connection.get_patient_encounters(sample_patient_id)

        assert isinstance(results, list)

        if results:
            assert 'patient_name' in results[0]
            assert 'encounter_type' in results[0]
            assert 'encounter_date' in results[0]
            assert 'encounter_labels' in results[0]
            assert isinstance(results[0]['encounter_labels'], list)

    def test_get_patient_encounters_by_name(self, db_connection, sample_patient_name):
        """Test getting encounters by patient first name."""
        results = db_connection.get_patient_encounters(sample_patient_name)

        assert isinstance(results, list)

        if results:
            assert 'patient_name' in results[0]
            assert sample_patient_name in results[0]['patient_name']

    def test_get_patient_encounters_nonexistent_patient(self, db_connection):
        """Test getting encounters for non-existent patient returns empty list."""
        results = db_connection.get_patient_encounters("NONEXISTENT_PATIENT_12345")

        assert isinstance(results, list)
        assert len(results) == 0


class TestCustomCypherExecution:
    """Test execute_custom_cypher functionality."""

    def test_execute_custom_cypher_valid_query(self, db_connection):
        """Test executing a valid custom Cypher query."""
        query = "MATCH (p:Patient) RETURN count(p) AS patient_count"
        result = db_connection.execute_custom_cypher(query)

        assert isinstance(result, dict)
        assert result['success'] is True
        assert 'results' in result
        assert 'message' in result
        assert 'result_count' in result
        assert result['result_count'] > 0
        assert len(result['results']) > 0

    def test_execute_custom_cypher_no_results(self, db_connection):
        """Test executing query that returns no results."""
        query = "MATCH (p:Patient {id: 'NONEXISTENT_12345'}) RETURN p"
        result = db_connection.execute_custom_cypher(query)

        assert isinstance(result, dict)
        assert result['success'] is True
        assert result['result_count'] == 0
        assert len(result['results']) == 0
        assert "no results" in result['message'].lower()

    def test_execute_custom_cypher_invalid_query(self, db_connection):
        """Test executing an invalid Cypher query."""
        query = "INVALID CYPHER QUERY SYNTAX"
        result = db_connection.execute_custom_cypher(query)

        assert isinstance(result, dict)
        assert result['success'] is False
        assert 'error' in result
        assert result['result_count'] == 0
        assert "error" in result['message'].lower()

    def test_execute_custom_cypher_complex_query(self, db_connection):
        """Test executing a complex aggregation query."""
        query = """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)
        RETURN p.firstName + ' ' + p.lastName AS patient_name,
               count(e) AS encounter_count
        ORDER BY encounter_count DESC
        LIMIT 5
        """
        result = db_connection.execute_custom_cypher(query)

        assert isinstance(result, dict)
        assert result['success'] is True

        if result['result_count'] > 0:
            assert 'patient_name' in result['results'][0]
            assert 'encounter_count' in result['results'][0]


class TestDatabaseSchema:
    """Test get_database_schema functionality."""

    def test_get_database_schema_returns_string(self, db_connection):
        """Test that schema retrieval returns a string."""
        schema = db_connection.get_database_schema()

        assert isinstance(schema, str)
        assert len(schema) > 0

    def test_get_database_schema_contains_key_elements(self, db_connection):
        """Test that schema contains expected entities and relationships."""
        schema = db_connection.get_database_schema()

        # Check for main entities
        assert "Patient" in schema
        assert "Encounter" in schema
        assert "Procedure" in schema
        assert "Drug" in schema

        # Check for key relationships
        assert "HAS_ENCOUNTER" in schema
        assert "HAS_PROCEDURE" in schema
        assert "HAS_DRUG" in schema


class TestQueryWithRealPatientData:
    """
    Integration tests using real patient data to verify queries work end-to-end.
    These tests find a patient with actual data and verify all queries work.
    """

    @pytest.fixture(scope="class")
    def patient_with_data(self, db_connection):
        """
        Find a patient who has procedures, medications, and conditions.
        This ensures we can test with meaningful data.
        """
        # Find a patient with at least one procedure
        query = """
        MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc)
        RETURN p.id AS patient_id, p.firstName AS first_name,
               p.firstName + ' ' + p.lastName AS full_name
        LIMIT 1
        """
        results = db_connection.execute_query(query)

        if not results:
            pytest.skip("No patients with procedures found")

        return results[0]

    def test_full_patient_data_retrieval(self, db_connection, patient_with_data):
        """Test retrieving all types of data for a patient with known data."""
        patient_id = patient_with_data['patient_id']

        # Get procedures
        procedures = db_connection.get_patient_procedures(patient_id)
        print(f"\nPatient {patient_with_data['full_name']} procedures: {len(procedures)}")

        # Get medications
        medications = db_connection.get_patient_medications(patient_id)
        print(f"Patient {patient_with_data['full_name']} medications: {len(medications)}")

        # Get conditions
        conditions = db_connection.get_patient_conditions(patient_id)
        print(f"Patient {patient_with_data['full_name']} conditions: {len(conditions)}")

        # Get encounters
        encounters = db_connection.get_patient_encounters(patient_id)
        print(f"Patient {patient_with_data['full_name']} encounters: {len(encounters)}")

        # At minimum, we know this patient has procedures
        assert len(procedures) > 0, "Patient should have procedures"
        assert len(encounters) > 0, "Patient should have encounters"

        # Print sample data for debugging
        if procedures:
            print(f"\nSample procedure: {procedures[0]}")
        if medications:
            print(f"Sample medication: {medications[0]}")
        if encounters:
            print(f"Sample encounter: {encounters[0]}")


class TestEmptyResultHandling:
    """
    Test that functions handle empty results correctly.
    This addresses the issue where tools sometimes return empty strings.
    """

    def test_procedures_empty_result_structure(self, db_connection):
        """Test that get_patient_procedures returns proper structure even with no results."""
        results = db_connection.get_patient_procedures("NONEXISTENT_PATIENT")

        assert isinstance(results, list), "Should return a list, not a string"
        assert results == [], "Should return empty list, not empty string"

    def test_medications_empty_result_structure(self, db_connection):
        """Test that get_patient_medications returns proper structure even with no results."""
        results = db_connection.get_patient_medications("NONEXISTENT_PATIENT")

        assert isinstance(results, list), "Should return a list, not a string"
        assert results == [], "Should return empty list, not empty string"

    def test_conditions_empty_result_structure(self, db_connection):
        """Test that get_patient_conditions returns proper structure even with no results."""
        results = db_connection.get_patient_conditions("NONEXISTENT_PATIENT")

        assert isinstance(results, list), "Should return a list, not a string"
        assert results == [], "Should return empty list, not empty string"

    def test_encounters_empty_result_structure(self, db_connection):
        """Test that get_patient_encounters returns proper structure even with no results."""
        results = db_connection.get_patient_encounters("NONEXISTENT_PATIENT")

        assert isinstance(results, list), "Should return a list, not a string"
        assert results == [], "Should return empty list, not empty string"

    def test_search_patients_empty_result_structure(self, db_connection):
        """Test that search_patients returns proper structure even with no results."""
        results = db_connection.search_patients("ZZZZZ_NONEXISTENT_NAME_ZZZZZ")

        assert isinstance(results, list), "Should return a list, not a string"
        assert results == [], "Should return empty list, not empty string"
