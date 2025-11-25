"""
Patient Similarity Embeddings Generator

This script generates patient similarity embeddings using Neo4j Graph Data Science algorithms.
It creates embeddings based on:
1. Encounter similarity (types and frequency of medical encounters)
2. Procedure similarity (types and frequency of procedures)
3. Drug similarity (types and frequency of medications)
4. KNN similarity (combining all embeddings with patient demographics)

Based on the notebook: reference_notebooks/patientJourney_nodeSimilarity.ipynb
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from graphdatascience import GraphDataScience
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PatientSimilarityEmbeddings:
    """Generates and manages patient similarity embeddings in Neo4j."""

    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None,
        database: str = "synthea-sample"
    ):
        """
        Initialize connection to Neo4j and GDS.

        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
            database: Database name
        """
        self.uri = uri or os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password123")
        self.database = database

        # Initialize GDS connection
        logger.info(f"Connecting to Neo4j at {self.uri}")
        self.gds = GraphDataScience(self.uri, auth=(self.username, self.password), database=self.database)

        # Also keep a regular Neo4j driver for custom queries
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))

        logger.info("Connected successfully")

    def close(self):
        """Close database connections."""
        if self.driver:
            self.driver.close()
        logger.info("Connections closed")

    def cleanup_existing_graphs(self):
        """Drop any existing GDS graph projections."""
        logger.info("Cleaning up existing graph projections...")

        graphs_to_drop = [
            'encounterBipartite',
            'encounterSimilarity',
            'procedureBipartite',
            'procedureSimilarity',
            'drugBipartite',
            'drugSimilarity',
            'knnGraph'
        ]

        for graph_name in graphs_to_drop:
            try:
                if self.gds.graph.exists(graph_name)['exists']:
                    self.gds.graph.drop(graph_name)
                    logger.info(f"Dropped graph: {graph_name}")
            except Exception as e:
                logger.debug(f"Graph {graph_name} doesn't exist or error dropping: {e}")

    def prepare_patient_data(self):
        """
        Create aggregated relationships from Patient to Encounter/Procedure/Drug nodes
        with relationship counts.
        """
        logger.info("Preparing patient data with relationship counts...")

        with self.driver.session(database=self.database) as session:
            # Create ENCOUNTER_CODE relationships with counts
            logger.info("Creating ENCOUNTER_CODE relationships...")
            session.run("""
                MATCH (p:Patient)-[:HAS_ENCOUNTER]->(e:Encounter)-[:OF_TYPE]->(s:SNOMED_CT)
                WITH p, s, count(*) AS relCount
                MERGE (p)-[r:ENCOUNTER_CODE]->(s)
                SET r.relCount = relCount
            """)

            # Create PROCEDURE_CODE relationships with counts
            logger.info("Creating PROCEDURE_CODE relationships...")
            session.run("""
                MATCH (p:Patient)-[:HAS_ENCOUNTER]->(:Encounter)-[:HAS_PROCEDURE]->(proc:SNOMED_CT)
                WITH p, proc, count(*) AS relCount
                MERGE (p)-[r:PROCEDURE_CODE]->(proc)
                SET r.relCount = relCount
            """)

            # Create DRUGS_PRESCRIBED relationships with counts
            logger.info("Creating DRUGS_PRESCRIBED relationships...")
            session.run("""
                MATCH (p:Patient)-[:HAS_ENCOUNTER]->(:Encounter)-[:HAS_DRUG]->(drug:Drug)
                WITH p, drug, count(*) AS relCount
                MERGE (p)-[r:DRUGS_PRESCRIBED]->(drug)
                SET r.relCount = relCount
            """)

            # Calculate patient statistics - split into separate queries for performance
            logger.info("Calculating patient statistics...")

            # Total encounters and expenses
            logger.info("  - Calculating total encounters and expenses...")
            session.run("""
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
                WITH p, count(DISTINCT e) AS totalEncounters, sum(COALESCE(e.totalCost, 0)) AS expenses
                SET p.totalEncounters = totalEncounters,
                    p.expenses = expenses
            """)

            # Procedure count
            logger.info("  - Calculating procedure counts...")
            session.run("""
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:PROCEDURE_CODE]->(s:SNOMED_CT)
                WITH p, count(DISTINCT s) AS procedureCount
                SET p.procedureCount = procedureCount
            """)

            # Drug count
            logger.info("  - Calculating drug counts...")
            session.run("""
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:DRUGS_PRESCRIBED]->(drug:Drug)
                WITH p, count(DISTINCT drug) AS drugCount
                SET p.drugCount = drugCount
            """)

            # Emergency encounters
            logger.info("  - Calculating emergency encounter counts...")
            session.run("""
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(emergency:Emergency)
                WITH p, count(DISTINCT emergency) AS emergencyEncounters
                SET p.emergencyEncounters = emergencyEncounters
            """)

            # Calculate age from birthDate
            session.run("""
                MATCH (p:Patient)
                WHERE p.birthDate IS NOT NULL
                WITH p, date(p.birthDate) AS birthDate, date() AS today
                SET p.age = duration.between(birthDate, today).years
            """)

            logger.info("Patient data preparation complete")

    def create_similarity_embeddings(
        self,
        relationship_type: str,
        target_label: str,
        similarity_type: str,
        embedding_property: str,
        embedding_dim: int = 256,
        top_k: int = 10,
        similarity_cutoff: float = 0.01
    ):
        """
        Create similarity embeddings for a specific relationship type.

        Args:
            relationship_type: Type of relationship (e.g., 'ENCOUNTER_CODE')
            target_label: Target node label (e.g., 'SNOMED_CT', 'Drug')
            similarity_type: Name for similarity relationship (e.g., 'ENCOUNTER_SIMILARITY')
            embedding_property: Property name to store embeddings (e.g., 'encounterSimilarityEmbed')
            embedding_dim: Dimension of embeddings (default: 256)
            top_k: Number of top similar patients to connect (default: 10)
            similarity_cutoff: Minimum similarity score (default: 0.01)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {similarity_type}")
        logger.info(f"{'='*60}")

        # Step 1: Create bipartite graph projection
        bipartite_graph_name = f"{similarity_type.lower().replace('_similarity', '')}Bipartite"
        logger.info(f"Step 1: Creating bipartite graph projection '{bipartite_graph_name}'...")

        self.gds.graph.project(
            bipartite_graph_name,
            ['Patient', target_label],
            {relationship_type: {'properties': 'relCount'}}
        )
        logger.info(f"Created bipartite graph '{bipartite_graph_name}'")

        # Step 2: Run Node Similarity algorithm
        logger.info(f"Step 2: Computing node similarity...")
        self.gds.nodeSimilarity.write(
            self.gds.graph.get(bipartite_graph_name),
            relationshipWeightProperty='relCount',
            writeRelationshipType=similarity_type,
            writeProperty='similarityScore',
            similarityCutoff=similarity_cutoff,
            topK=top_k,
            concurrency=4
        )
        logger.info(f"Created {similarity_type} relationships")

        # Drop bipartite graph
        self.gds.graph.drop(self.gds.graph.get(bipartite_graph_name))

        # Step 3: Create similarity graph projection (undirected, Patient nodes only)
        similarity_graph_name = f"{similarity_type.lower().replace('_similarity', '')}Similarity"
        logger.info(f"Step 3: Creating similarity graph '{similarity_graph_name}'...")

        self.gds.graph.project(
            similarity_graph_name,
            'Patient',
            {
                similarity_type: {
                    'orientation': 'UNDIRECTED',
                    'properties': 'similarityScore'
                }
            }
        )
        logger.info(f"Created similarity graph '{similarity_graph_name}'")

        # Get the graph object for algorithms
        g_similarity = self.gds.graph.get(similarity_graph_name)

        # Step 4: Community Detection (Label Propagation)
        community_property = f"{similarity_type.lower().replace('_similarity', '')}Community"
        logger.info(f"Step 4: Running community detection (property: {community_property})...")

        self.gds.labelPropagation.write(
            g_similarity,
            relationshipWeightProperty='similarityScore',
            writeProperty=community_property
        )
        logger.info(f"Communities detected and written to {community_property}")

        # Step 5: Calculate PageRank
        pagerank_property = f"{similarity_type.lower().replace('_similarity', '')}PageRank"
        logger.info(f"Step 5: Calculating PageRank (property: {pagerank_property})...")

        self.gds.pageRank.write(
            g_similarity,
            relationshipTypes=[similarity_type],
            relationshipWeightProperty='similarityScore',
            writeProperty=pagerank_property
        )
        logger.info(f"PageRank calculated and written to {pagerank_property}")

        # Step 6: Generate FastRP embeddings
        logger.info(f"Step 6: Generating {embedding_dim}-dimensional embeddings (property: {embedding_property})...")

        self.gds.fastRP.write(
            g_similarity,
            nodeLabels=['Patient'],
            relationshipTypes=[similarity_type],
            relationshipWeightProperty='similarityScore',
            writeProperty=embedding_property,
            randomSeed=42,
            embeddingDimension=embedding_dim
        )
        logger.info(f"Embeddings generated and written to {embedding_property}")

        # Drop similarity graph
        self.gds.graph.drop(g_similarity)

        logger.info(f"✓ {similarity_type} processing complete\n")

    def create_knn_embeddings(
        self,
        embedding_dim: int = 256,
        top_k: int = 25
    ):
        """
        Create KNN-based embeddings combining all previous embeddings and patient attributes.

        Args:
            embedding_dim: Dimension of final embeddings (default: 256)
            top_k: Number of nearest neighbors (default: 25)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing KNN Combined Similarity")
        logger.info(f"{'='*60}")

        # Step 1: Create graph projection with all properties
        logger.info("Step 1: Creating KNN graph with all properties...")

        # First, set default income if not present
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (p:Patient)
                WHERE p.income IS NULL
                SET p.income = 0
            """)

        self.gds.graph.project(
            'knnGraph',
            'Patient',
            '*',
            nodeProperties=[
                'age', 'expenses', 'income', 'drugCount',
                'procedureCount', 'totalEncounters', 'emergencyEncounters',
                'encounterSimilarityEmbed', 'procedureSimilarityEmbed', 'drugSimilarityEmbed'
            ]
        )
        logger.info(f"Created KNN graph 'knnGraph'")

        # Get graph object
        g_knn = self.gds.graph.get('knnGraph')

        # Step 2: Scale non-embedding properties
        logger.info("Step 2: Scaling demographic and statistical properties...")

        self.gds.alpha.scaleProperties.mutate(
            g_knn,
            nodeProperties=['age', 'expenses', 'income', 'drugCount',
                          'procedureCount', 'totalEncounters', 'emergencyEncounters'],
            scaler='MinMax',
            mutateProperty='scaledProperties'
        )
        logger.info("Properties scaled using MinMax scaler")

        # Step 3: Run KNN algorithm
        logger.info(f"Step 3: Running KNN algorithm (k={top_k})...")

        self.gds.knn.write(
            g_knn,
            topK=top_k,
            nodeProperties=[
                'scaledProperties',
                'encounterSimilarityEmbed',
                'procedureSimilarityEmbed',
                'drugSimilarityEmbed'
            ],
            concurrency=1,
            randomSeed=42,
            writeRelationshipType='KNN_SIMILARITY',
            writeProperty='similarityScore'
        )
        logger.info("KNN relationships created")

        # Drop the initial graph and recreate with KNN relationships
        self.gds.graph.drop(g_knn)

        # Step 4: Create new graph with KNN relationships
        logger.info("Step 4: Creating graph with KNN similarity relationships...")

        self.gds.graph.project(
            'knnSimilarity',
            'Patient',
            {
                'KNN_SIMILARITY': {
                    'orientation': 'UNDIRECTED',
                    'properties': 'similarityScore'
                }
            }
        )
        logger.info(f"Created KNN similarity graph 'knnSimilarity'")

        # Get graph object
        g_knn_similarity = self.gds.graph.get('knnSimilarity')

        # Step 5: Community Detection
        logger.info("Step 5: Running community detection...")

        self.gds.labelPropagation.write(
            g_knn_similarity,
            relationshipWeightProperty='similarityScore',
            writeProperty='knnCommunity'
        )
        logger.info("Communities detected and written to knnCommunity")

        # Step 6: Calculate PageRank
        logger.info("Step 6: Calculating PageRank...")

        self.gds.pageRank.write(
            g_knn_similarity,
            relationshipTypes=['KNN_SIMILARITY'],
            relationshipWeightProperty='similarityScore',
            writeProperty='knnPageRank'
        )
        logger.info("PageRank calculated and written to knnPageRank")

        # Step 7: Generate final FastRP embeddings
        logger.info(f"Step 7: Generating final {embedding_dim}-dimensional embeddings...")

        self.gds.fastRP.write(
            g_knn_similarity,
            nodeLabels=['Patient'],
            relationshipTypes=['KNN_SIMILARITY'],
            relationshipWeightProperty='similarityScore',
            writeProperty='knnSimilarityEmbed',
            randomSeed=42,
            embeddingDimension=embedding_dim
        )
        logger.info("Final embeddings generated and written to knnSimilarityEmbed")

        # Drop graph
        self.gds.graph.drop(g_knn_similarity)

        logger.info(f"✓ KNN Combined Similarity processing complete\n")

    def generate_all_embeddings(
        self,
        embedding_dim: int = 256,
        node_similarity_top_k: int = 10,
        knn_top_k: int = 25,
        similarity_cutoff: float = 0.01
    ):
        """
        Generate all patient similarity embeddings.

        Args:
            embedding_dim: Dimension of embeddings (default: 256)
            node_similarity_top_k: Top K for node similarity (default: 10)
            knn_top_k: Top K for KNN (default: 25)
            similarity_cutoff: Minimum similarity threshold (default: 0.01)
        """
        logger.info("\n" + "="*60)
        logger.info("PATIENT SIMILARITY EMBEDDINGS GENERATION")
        logger.info("="*60 + "\n")

        # Cleanup
        self.cleanup_existing_graphs()

        # Prepare data
        self.prepare_patient_data()

        # Generate encounter similarity embeddings
        self.create_similarity_embeddings(
            relationship_type='ENCOUNTER_CODE',
            target_label='SNOMED_CT',
            similarity_type='ENCOUNTER_SIMILARITY',
            embedding_property='encounterSimilarityEmbed',
            embedding_dim=embedding_dim,
            top_k=node_similarity_top_k,
            similarity_cutoff=similarity_cutoff
        )

        # Generate procedure similarity embeddings
        self.create_similarity_embeddings(
            relationship_type='PROCEDURE_CODE',
            target_label='SNOMED_CT',
            similarity_type='PROCEDURE_SIMILARITY',
            embedding_property='procedureSimilarityEmbed',
            embedding_dim=embedding_dim,
            top_k=node_similarity_top_k,
            similarity_cutoff=similarity_cutoff
        )

        # Generate drug similarity embeddings
        self.create_similarity_embeddings(
            relationship_type='DRUGS_PRESCRIBED',
            target_label='Drug',
            similarity_type='DRUG_SIMILARITY',
            embedding_property='drugSimilarityEmbed',
            embedding_dim=embedding_dim,
            top_k=node_similarity_top_k,
            similarity_cutoff=similarity_cutoff
        )

        # Generate KNN combined embeddings
        self.create_knn_embeddings(
            embedding_dim=embedding_dim,
            top_k=knn_top_k
        )

        logger.info("\n" + "="*60)
        logger.info("ALL EMBEDDINGS GENERATED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info("\nEmbedding properties stored on Patient nodes:")
        logger.info("  - encounterSimilarityEmbed (256D)")
        logger.info("  - procedureSimilarityEmbed (256D)")
        logger.info("  - drugSimilarityEmbed (256D)")
        logger.info("  - knnSimilarityEmbed (256D) - RECOMMENDED for queries")
        logger.info("\nSimilarity relationships created:")
        logger.info("  - ENCOUNTER_SIMILARITY")
        logger.info("  - PROCEDURE_SIMILARITY")
        logger.info("  - DRUG_SIMILARITY")
        logger.info("  - KNN_SIMILARITY - RECOMMENDED for queries")
        logger.info("\n" + "="*60 + "\n")

    def find_similar_patients(
        self,
        patient_name: str,
        k: int = 10,
        similarity_type: str = 'KNN_SIMILARITY'
    ) -> List[Dict[str, Any]]:
        """
        Find K most similar patients to a given patient.

        Args:
            patient_name: Name of the patient (first, last, or full name)
            k: Number of similar patients to return
            similarity_type: Type of similarity to use (default: KNN_SIMILARITY)
                Options: 'KNN_SIMILARITY', 'ENCOUNTER_SIMILARITY',
                        'PROCEDURE_SIMILARITY', 'DRUG_SIMILARITY'

        Returns:
            List of dictionaries containing similar patient information
        """
        logger.info(f"\nFinding {k} most similar patients to '{patient_name}' using {similarity_type}...")

        # Check if the name contains a space
        has_space = ' ' in patient_name.strip()

        if has_space:
            # Full name search
            # Fetch 2x k results to account for bidirectional duplicates
            query = f"""
                MATCH (p:Patient)
                WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower($patient_name)
                WITH p LIMIT 1
                MATCH (p)-[sim:{similarity_type}]-(similar:Patient)
                WHERE id(p) <> id(similar)
                RETURN
                    p.firstName + ' ' + p.lastName AS source_patient,
                    similar.firstName + ' ' + similar.lastName AS similar_patient,
                    similar.age AS age,
                    similar.totalEncounters AS total_encounters,
                    similar.procedureCount AS procedure_count,
                    similar.drugCount AS drug_count,
                    similar.expenses AS expenses,
                    sim.similarityScore AS similarity_score
                ORDER BY sim.similarityScore DESC
                LIMIT $fetch_limit
            """
        else:
            # Single name search
            # Fetch 2x k results to account for bidirectional duplicates
            query = f"""
                MATCH (p:Patient)
                WHERE toLower(p.firstName) CONTAINS toLower($patient_name)
                   OR toLower(p.lastName) CONTAINS toLower($patient_name)
                WITH p LIMIT 1
                MATCH (p)-[sim:{similarity_type}]-(similar:Patient)
                WHERE id(p) <> id(similar)
                RETURN
                    p.firstName + ' ' + p.lastName AS source_patient,
                    similar.firstName + ' ' + similar.lastName AS similar_patient,
                    similar.age AS age,
                    similar.totalEncounters AS total_encounters,
                    similar.procedureCount AS procedure_count,
                    similar.drugCount AS drug_count,
                    similar.expenses AS expenses,
                    sim.similarityScore AS similarity_score
                ORDER BY sim.similarityScore DESC
                LIMIT $fetch_limit
            """

        with self.driver.session(database=self.database) as session:
            # Fetch 2x k results to account for bidirectional duplicates
            fetch_limit = k * 2
            result = session.run(query, {"patient_name": patient_name, "k": k, "fetch_limit": fetch_limit})
            records = [dict(record) for record in result]

        # Deduplicate by similar_patient name (in case of bidirectional relationships)
        seen_patients = set()
        unique_records = []
        for record in records:
            patient_name_key = record['similar_patient']
            if patient_name_key not in seen_patients:
                seen_patients.add(patient_name_key)
                unique_records.append(record)
                if len(unique_records) >= k:
                    break

        if unique_records:
            logger.info(f"\nFound {len(unique_records)} similar patients:")
            for i, record in enumerate(unique_records, 1):
                logger.info(f"  {i}. {record['similar_patient']} (similarity: {record['similarity_score']:.4f})")
        else:
            logger.info(f"No similar patients found for '{patient_name}'")

        return unique_records


def main():
    """Main function to generate embeddings."""
    # Initialize the embeddings generator
    embeddings_gen = PatientSimilarityEmbeddings()

    try:
        # Generate all embeddings
        embeddings_gen.generate_all_embeddings(
            embedding_dim=256,
            node_similarity_top_k=10,
            knn_top_k=25,
            similarity_cutoff=0.01
        )

        # Example: Find similar patients
        logger.info("\n" + "="*60)
        logger.info("EXAMPLE QUERY: Finding similar patients")
        logger.info("="*60)

        # Get a sample patient name to demonstrate
        with embeddings_gen.driver.session(database=embeddings_gen.database) as session:
            result = session.run("""
                MATCH (p:Patient)
                RETURN p.firstName + ' ' + p.lastName AS name
                LIMIT 1
            """)
            sample_patient = result.single()

            if sample_patient:
                patient_name = sample_patient['name']
                similar_patients = embeddings_gen.find_similar_patients(
                    patient_name=patient_name,
                    k=5,
                    similarity_type='KNN_SIMILARITY'
                )

                print("\n" + "="*60)
                print(f"Top 5 patients similar to '{patient_name}':")
                print("="*60)
                for i, patient in enumerate(similar_patients, 1):
                    print(f"\n{i}. {patient['similar_patient']}")
                    print(f"   Similarity Score: {patient['similarity_score']:.4f}")
                    print(f"   Age: {patient.get('age', 'N/A')}")
                    print(f"   Total Encounters: {patient.get('total_encounters', 0)}")
                    print(f"   Procedures: {patient.get('procedure_count', 0)}")
                    print(f"   Medications: {patient.get('drug_count', 0)}")
                    print(f"   Total Expenses: ${patient.get('expenses', 0):,.2f}")

    finally:
        # Close connections
        embeddings_gen.close()


if __name__ == "__main__":
    main()
