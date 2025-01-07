import csv
from db_neo4j import Neo4jConnection

# Initialize Neo4j connection
neo4j_conn = Neo4jConnection()

# Read hospital data
hospital_data = {}
with open('./files/hospital_data.csv', mode='r') as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        hospital_data[row['Hospital']] = {'Specialization': row['Specialization']}

# Read hospital geospatial data and merge with hospital data
with open('./files/hospital_geospatial_data.csv', mode='r') as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        if row['Hospital'] in hospital_data:
            hospital_data[row['Hospital']].update({
                'Latitude': row['Latitude'],
                'Longitude': row['Longitude']
            })

# Create Hospital nodes in Neo4j
for hospital, data in hospital_data.items():
    query = """
    CREATE (h:Hospital {name: $name, specialization: $specialization, latitude: $latitude, longitude: $longitude})
    """
    params = {
        'name': hospital,
        'specialization': data['Specialization'],
        'latitude': data['Latitude'],
        'longitude': data['Longitude']
    }
    neo4j_conn.query(query, params)

# Close Neo4j connection
neo4j_conn.close()