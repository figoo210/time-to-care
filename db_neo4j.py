from neo4j import GraphDatabase


class Neo4jConnection:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="qwe123123"):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def query(self, query, parameters=None, db="neo4j"):
        session = None
        response = None
        try:
            session = (
                self._driver.session(database=db)
                if db is not None
                else self._driver.session()
            )
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response

    def create_patient_node(self, patient_data):
        """
        Creates a patient node in the Neo4j graph database.

        Args:
            patient_data (dict): A dictionary containing patient information.
                - name (str): Patient's name.
                - latitude (float): Patient's latitude.
                - longitude (float): Patient's longitude.
                - symptoms (list): List of patient's symptoms.
                - triageCode (str): Patient's triage code.
        """
        query = """
            CREATE (p:Patient {
                name: $name,
                latitude: $latitude,
                longitude: $longitude,
                triageCode: $triageCode
            })
        """
        self.query(query, patient_data)

    def add_symptom_relationships(self, patient_name, symptoms):
        """
        Creates relationships between a patient and their symptoms.

        Args:
            patient_name (str): Name of the patient.
            symptoms (list): List of patient's symptoms.
        """
        query = """
        MATCH (p:Patient {name: $patient_name})
        UNWIND $symptoms AS symptom
        CREATE (s:Symptom {name: symptom})
        WITH p, s
        CREATE (p)-[r:HAS_SYMPTOM]->(s)
        """
        self.query(query, {"patient_name": patient_name, "symptoms": symptoms})

    def find_busy_hospitals(self):
        """
        Identifies hospitals with a high number of patients.

        Returns:
            list: A list of dictionaries containing hospital names and patient counts.
        """
        query = """
        MATCH (p:Patient)-[:TREATED_AT]->(h:Hospital)
        WITH h, count(p) AS patient_count
        ORDER BY patient_count DESC
        RETURN h.name AS hospital, patient_count
        """
        results = self.query(query)
        return [{"hospital": row[0], "patient_count": row[1]} for row in results]

    def calculate_average_travel_distance(self):
        """
        Calculates the average travel distance between patients and assigned hospitals.

        Returns:
            float: The average travel distance in kilometers.
        """
        query = """
        MATCH (p:Patient)-[:TREATED_AT]->(h:Hospital)
        RETURN distance(point({latitude: p.latitude, longitude: p.longitude}), point({latitude: h.latitude, longitude: h.longitude})) AS distance_km
        """
        results = self.query(query)
        distances = [row[0] for row in results]
        return sum(distances) / len(distances) if distances else 0

    def identify_bottlenecks_by_symptoms(self):
        """
        Identifies symptoms that frequently lead to long wait times or high patient volumes.

        Returns:
            list: A list of dictionaries containing symptom names and associated metrics.
        """
        query = """
        MATCH (p:Patient)-[:HAS_SYMPTOM]->(s:Symptom)
        WITH s, count(p) AS patient_count
        ORDER BY patient_count DESC
        RETURN s.name AS symptom, patient_count
        """
        results = self.query(query)
        return [{"symptom": row[0], "patient_count": row[1]} for row in results]
