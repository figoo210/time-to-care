import time
import random
import threading
from db_mongodb import client
from db_sqlite import get_connection, insert_data
from db_neo4j import Neo4jConnection

# MongoDB setup
mongo_db = client['time_to_care.hospital_queue']
mongo_collection = mongo_db['hospital_queue']

# SQLite setup
sqlite_conn = get_connection()

# Neo4j setup
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def push_to_mongo():
    while True:
        patient_id = f'patient_{random.randint(1, 100)}'
        status = random.choice(['waiting', 'in_treatment', 'discharged'])
        mongo_collection.insert_one({'patient_id': patient_id, 'status': status, 'timestamp': time.time()})
        time.sleep(1)

def update_sqlite():
    while True:
        for update in mongo_collection.find():
            sqlite_cursor.execute('INSERT INTO queue_updates (patient_id, status) VALUES (?, ?)',
                                  (update['patient_id'], update['status']))
            sqlite_conn.commit()
        time.sleep(5)

def update_neo4j():
    while True:
        with neo4j_driver.session() as session:
            for update in mongo_collection.find():
                session.run('MERGE (p:Patient {id: $patient_id}) '
                            'SET p.status = $status, p.timestamp = $timestamp',
                            patient_id=update['patient_id'], status=update['status'], timestamp=update['timestamp'])
        time.sleep(5)

def test_matching_algorithm():
    scenarios = [
        {'patient_id': 'patient_1', 'status': 'waiting'},
        {'patient_id': 'patient_2', 'status': 'in_treatment'},
        {'patient_id': 'patient_3', 'status': 'discharged'}
    ]

    for scenario in scenarios:
        mongo_collection.insert_one({'patient_id': scenario['patient_id'], 'status': scenario['status'], 'timestamp': time.time()})
        time.sleep(1)
        print(f"Inserted scenario: {scenario}")

if __name__ == "__main__":
    threading.Thread(target=push_to_mongo).start()
    threading.Thread(target=update_sqlite).start()
    threading.Thread(target=update_neo4j).start()
    threading.Thread(target=test_matching_algorithm).start()