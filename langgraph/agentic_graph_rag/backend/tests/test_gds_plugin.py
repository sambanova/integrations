"""
Test script to verify the Neo4j Graph Data Science (GDS) plugin is installed.
Required for patient similarity search (find_similar_patients tool).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from neo4j_utils import Neo4jConnection


def test_gds_plugin():
    """Check that the GDS plugin is installed and accessible."""
    print("Testing Neo4j Graph Data Science (GDS) plugin...")

    try:
        conn = Neo4jConnection()
        conn.connect()

        records, _, _ = conn.execute_query("RETURN gds.version() AS version")
        if records:
            version = records[0]["version"]
            print(f"✓ GDS plugin is installed (version {version})")
            conn.close()
            return True
        else:
            print("✗ GDS plugin query returned no results")
            conn.close()
            return False

    except Exception as e:
        error = str(e)
        if "gds" in error.lower() or "not correctly installed" in error.lower() or "unknown function" in error.lower():
            print("✗ GDS plugin is NOT installed")
            print("\nTo install the Graph Data Science plugin:")
            print("  Neo4j Desktop : open your project → select the database → Plugins tab → install 'Graph Data Science Library'")
            print("  Neo4j AuraDB  : enable GDS from the instance settings in the Aura console")
            print("\nThe GDS plugin is required for patient similarity search.")
        else:
            print(f"✗ Error checking GDS plugin: {error}")
        return False


if __name__ == "__main__":
    success = test_gds_plugin()
    sys.exit(0 if success else 1)
