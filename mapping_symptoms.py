import json
from db_neo4j import Neo4jConnection

# Load symptoms data from JSON file
with open("./files/symptoms_data.json", "r") as file:
    symptoms_data = json.load(file)

# Initialize Neo4j connection
conn = Neo4jConnection()

# Create Symptom nodes and relationships with Hospital nodes
for symptom in symptoms_data:
    symptom_name = symptom["Symptom"]
    specialization = symptom["Specialization"]

    # Create Symptom node
    conn.query(
        "MERGE (s:Symptom {name: $symptom_name})",
        parameters={"symptom_name": symptom_name},
    )

    # Create relationship with Hospital node based on specialization
    conn.query(
        """
        MATCH (s:Symptom {name: $symptom_name})
        MATCH (h:Hospital {specialization: $specialization})
        MERGE (s)-[:TREATED_AT]->(h)
        """,
        parameters={"symptom_name": symptom_name, "specialization": specialization},
    )

# Close the connection
conn.close()
