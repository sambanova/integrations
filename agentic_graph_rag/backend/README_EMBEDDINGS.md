# Patient Similarity Embeddings

This document explains how to set up and use patient similarity embeddings in your Neo4j database.

## Prerequisites

The patient similarity embeddings script requires the **Neo4j Graph Data Science (GDS) plugin** to be installed on your Neo4j server.

### Installing Neo4j GDS Plugin

The GDS plugin must be installed on the Neo4j server itself. There are two approaches:

#### Option 1: Neo4j Desktop (Easiest)
1. Open Neo4j Desktop
2. Select your database
3. Click on the "Plugins" tab
4. Find "Graph Data Science Library"
5. Click "Install"
6. Restart the database

#### Option 2: Neo4j Server (Manual Installation)
1. Download the GDS plugin from: https://neo4j.com/deployment-center/#gds-tab
2. Copy the JAR file to your Neo4j `plugins` directory
3. Add to `neo4j.conf`:
   ```
   dbms.security.procedures.unrestricted=gds.*
   dbms.security.procedures.allowlist=gds.*
   ```
4. Restart Neo4j

#### Verify Installation
Run this Cypher query in Neo4j Browser:
```cypher
RETURN gds.version()
```

If successful, it will return the GDS version number.

## Usage

### Generate All Embeddings

Once GDS is installed, run the script:

```bash
cd /Users/varunbk/repo/ai-starter-kit/agentic_graph_rag/backend
source ../.venv/bin/activate
python patient_similarity_embeddings.py
```

This will:
1. Create aggregated patient relationships (ENCOUNTER_CODE, PROCEDURE_CODE, DRUGS_PRESCRIBED)
2. Generate encounter similarity embeddings (256D)
3. Generate procedure similarity embeddings (256D)
4. Generate drug similarity embeddings (256D)
5. Generate combined KNN similarity embeddings (256D)
6. Create similarity relationships between patients

### Query Similar Patients

After embeddings are generated, you can use the `find_similar_patients()` function or run Cypher queries:

#### Using the Script Function
```python
from patient_similarity_embeddings import PatientSimilarityEmbeddings

embeddings_gen = PatientSimilarityEmbeddings()
similar_patients = embeddings_gen.find_similar_patients(
    patient_name="John Smith",
    k=10,
    similarity_type='KNN_SIMILARITY'
)
embeddings_gen.close()
```

#### Using Cypher Query
```cypher
// Find 10 most similar patients to "John Smith"
MATCH (p:Patient)
WHERE toLower(p.firstName + ' ' + p.lastName) CONTAINS toLower('john smith')
WITH p LIMIT 1
MATCH (p)-[sim:KNN_SIMILARITY]-(similar:Patient)
RETURN
    p.firstName + ' ' + p.lastName AS source_patient,
    similar.firstName + ' ' + similar.lastName AS similar_patient,
    similar.age AS age,
    similar.totalEncounters AS total_encounters,
    sim.similarityScore AS similarity_score
ORDER BY sim.similarityScore DESC
LIMIT 10
```

## Embedding Types

The script creates four types of embeddings:

1. **encounterSimilarityEmbed** (256D)
   - Based on shared encounter types and frequencies
   - Use relationship: `ENCOUNTER_SIMILARITY`

2. **procedureSimilarityEmbed** (256D)
   - Based on shared procedures and frequencies
   - Use relationship: `PROCEDURE_SIMILARITY`

3. **drugSimilarityEmbed** (256D)
   - Based on shared medications and frequencies
   - Use relationship: `DRUG_SIMILARITY`

4. **knnSimilarityEmbed** (256D) - **RECOMMENDED**
   - Combines all embeddings + demographics (age, expenses, income, etc.)
   - Use relationship: `KNN_SIMILARITY`
   - Most comprehensive similarity measure

## Configuration

You can customize the embedding generation in the script:

```python
embeddings_gen.generate_all_embeddings(
    embedding_dim=256,           # Dimension of embeddings
    node_similarity_top_k=10,    # Top K for node similarity
    knn_top_k=25,                # Top K for KNN
    similarity_cutoff=0.01       # Minimum similarity threshold
)
```

## What the Script Does

### Stage 1: Data Preparation
- Creates direct relationships from patients to encounter/procedure/drug codes
- Counts frequency of each relationship (`relCount` property)
- Calculates patient statistics (age, expenses, encounter counts, etc.)

### Stage 2: Similarity Computation (for Encounters, Procedures, Drugs)
For each type:
1. Creates bipartite graph projection (Patient → Codes/Drugs)
2. Runs Node Similarity algorithm (weighted Jaccard similarity)
3. Creates similarity relationships between patients
4. Runs community detection (Label Propagation)
5. Calculates PageRank scores
6. Generates FastRP embeddings (256D)

### Stage 3: KNN Combined Similarity
1. Scales demographic/statistical properties (MinMax)
2. Runs KNN algorithm on combined feature space (775 dimensions):
   - 7 scaled properties (age, expenses, income, etc.)
   - 256D encounter embeddings
   - 256D procedure embeddings
   - 256D drug embeddings
3. Finds 25 nearest neighbors for each patient
4. Runs community detection and PageRank
5. Generates final FastRP embeddings (256D)

## Troubleshooting

### Error: "GDS library is not correctly installed"
- Make sure you installed the GDS plugin on the Neo4j server (not just the Python library)
- Verify with: `RETURN gds.version()` in Neo4j Browser
- Restart Neo4j after installing the plugin

### Out of Memory Errors
- Reduce `embedding_dim` (try 128 or 64)
- Reduce `top_k` values
- Process fewer relationships by increasing `similarity_cutoff`

### Long Processing Time
- This is normal for large datasets
- The script logs progress at each step
- Each embedding type takes several minutes to process
- Total time depends on database size (typically 10-30 minutes for 1000+ patients)
