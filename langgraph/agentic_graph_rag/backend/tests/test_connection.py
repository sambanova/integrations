"""
Test script to verify Neo4j connection and basic queries.
"""
import sys
sys.path.append('..')

from neo4j_utils import Neo4jConnection

def test_connection():
    """Test Neo4j connection."""
    print("Testing Neo4j connection...")
    try:
        conn = Neo4jConnection()
        conn.connect()
        print("✓ Successfully connected to Neo4j")

        # Test a simple query
        print("\nTesting basic query...")
        result = conn.execute_query("MATCH (p:Patient) RETURN count(p) as patient_count")
        if result:
            print(f"✓ Query successful: Found {result[0]['patient_count']} patients")
        else:
            print("✗ Query returned no results")

        # Test patient search
        print("\nTesting patient search...")
        patients = conn.search_patients("Ethan")
        if patients:
            print(f"✓ Found {len(patients)} patients matching 'Ethan'")
            for p in patients[:3]:
                print(f"  - {p['patient_name']}")
        else:
            print("✗ No patients found")

        # Test procedures query
        print("\nTesting procedures query for 'Ethan766'...")
        procedures = conn.get_patient_procedures("Ethan766")
        if procedures:
            print(f"✓ Found {len(procedures)} procedures")
            print(f"  Sample: {procedures[0]['procedure_description']}")
        else:
            print("⚠ No procedures found for Ethan766 (patient may not exist with this exact name)")

        conn.close()
        print("\n✓ All tests completed successfully!")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease check:")
        print("1. Neo4j is running")
        print("2. Database name is 'synthea-sample'")
        print("3. Connection details in .env are correct")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
