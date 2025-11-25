"""
Test script for the Cypher subgraph (LangGraph implementation).
Tests the refactored subgraph architecture.
"""
import sys
import os
sys.path.append('..')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from cypher_subagent import query_cypher_subgraph, get_cypher_subgraph
from neo4j_utils import Neo4jConnection

def test_subgraph_structure():
    """Test that the subgraph is properly structured."""
    print("=" * 60)
    print("Testing Subgraph Structure")
    print("=" * 60)

    try:
        subgraph = get_cypher_subgraph()
        print("✓ Subgraph created successfully")
        print(f"  Type: {type(subgraph)}")
        return True
    except Exception as e:
        print(f"✗ Failed to create subgraph: {e}")
        return False


def test_simple_query():
    """Test a simple query through the subgraph."""
    print("\n" + "=" * 60)
    print("Testing Simple Query")
    print("=" * 60)

    question = "How many patients are in the database?"
    print(f"\nQuestion: {question}")
    print("-" * 60)

    try:
        response = query_cypher_subgraph(question)
        print("✓ Query executed successfully\n")
        print("Response:")
        print(response)
        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_query():
    """Test a complex analytical query."""
    print("\n" + "=" * 60)
    print("Testing Complex Query")
    print("=" * 60)

    question = "Which procedures were performed most frequently? Show top 10."
    print(f"\nQuestion: {question}")
    print("-" * 60)

    try:
        response = query_cypher_subgraph(question)
        print("✓ Query executed successfully\n")
        print("Response:")
        print(response)
        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_neo4j_connection():
    """Test that Neo4j connection works."""
    print("\n" + "=" * 60)
    print("Testing Neo4j Connection")
    print("=" * 60)

    try:
        conn = Neo4jConnection()
        conn.connect()
        result = conn.execute_query("MATCH (p:Patient) RETURN count(p) as count LIMIT 1")
        print(f"✓ Connected to Neo4j")
        print(f"  Patient count: {result[0]['count']}")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 Cypher Subgraph Test Suite (LangGraph)\n")

    # Check environment
    if not os.getenv("SAMBANOVA_API_KEY"):
        print("⚠️  WARNING: SAMBANOVA_API_KEY not set!")
        print("   Some tests may fail. Set it with:")
        print("   export SAMBANOVA_API_KEY='your-key-here'\n")
        print("   Or add it to .env file\n")

    try:
        # Test 1: Neo4j connection
        test1 = test_neo4j_connection()

        # Test 2: Subgraph structure
        test2 = test_subgraph_structure()

        # Test 3: Simple query
        if os.getenv("SAMBANOVA_API_KEY"):
            test3 = test_simple_query()
        else:
            print("\nSkipping simple query test (no API key)")
            test3 = None

        # Test 4: Complex query
        if os.getenv("SAMBANOVA_API_KEY"):
            test4 = test_complex_query()
        else:
            print("\nSkipping complex query test (no API key)")
            test4 = None

        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Neo4j Connection:  {'✓ PASS' if test1 else '✗ FAIL'}")
        print(f"Subgraph Structure: {'✓ PASS' if test2 else '✗ FAIL'}")
        print(f"Simple Query:       {'✓ PASS' if test3 else '⊘ SKIP' if test3 is None else '✗ FAIL'}")
        print(f"Complex Query:      {'✓ PASS' if test4 else '⊘ SKIP' if test4 is None else '✗ FAIL'}")

        if test1 and test2:
            print("\n✅ Core tests passed! Subgraph is properly structured.")
            if test3 and test4:
                print("✅ All tests passed!")
                sys.exit(0)
            elif test3 is None:
                print("⚠️  Query tests skipped (set OPENAI_API_KEY to run)")
                sys.exit(0)
            else:
                print("⚠️  Some query tests failed")
                sys.exit(1)
        else:
            print("\n❌ Core tests failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
