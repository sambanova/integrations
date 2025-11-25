import sys
sys.path.append('.')
from neo4j_utils import Neo4jConnection
from dotenv import load_dotenv

load_dotenv()

db = Neo4jConnection()
db.connect()

print("=" * 70)
print("TEST 8: Cypher subgraph - 'Which procedures were performed most frequently?'")
print("=" * 70)

# This is the likely query the LLM would generate
test_query = """
MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:HAS_PROCEDURE]->(proc)
RETURN proc.description AS procedure_name, count(*) AS procedure_count
ORDER BY procedure_count DESC
LIMIT 10
"""

print(f"Testing query:\n{test_query}\n")

result = db.execute_custom_cypher(test_query)
print(f"Type of result: {type(result)}")
print(f"Success: {result['success']}")
print(f"Result count: {result['result_count']}")

if result['success'] and result['result_count'] > 0:
    print(f"\nTop 10 most frequent procedures:")
    for i, proc in enumerate(result['results'], 1):
        print(f"  {i}. {proc['procedure_name']}: {proc['procedure_count']} times")
    print(f"\n✅ TEST PASSES - Query returns {result['result_count']} procedures")
else:
    print(f"\n⚠️  Issue: {result.get('message', 'No message')}")

db.close()
