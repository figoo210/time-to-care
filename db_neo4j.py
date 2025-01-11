from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import os
from dotenv import load_dotenv

load_dotenv()


class Neo4jConnection:
    def __init__(
        self,
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
    ):
        try:
            # Attempt to create the driver
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            # Explicitly test the connection
            with self._driver.session() as session:
                session.run("RETURN 1")  # Run a simple test query
            self.is_connected = True
            print("Connected successfully to Neo4j.")
        except ServiceUnavailable as e:
            print("############### Failed to create the driver:", e)
            self.is_connected = False
        except Exception as e:
            # Catch any other unexpected errors
            print(f"############### An unexpected error occurred: {e}")
            self.is_connected = False

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
                name: $Name,
                latitude: $Latitude,
                longitude: $Longitude,
                triageCode: $triageCode
            })
        """
        self.query(query, patient_data)

    def add_symptom_relationships(self, patient_name, symptoms):
        """
        Creates relationships between a patient and their existing symptoms.

        Args:
            patient_name (str): Name of the patient.
            symptoms (list): List of patient's symptoms.
        """
        query = """
            MATCH (p:Patient {name: $patient_name}), (s:Symptom)
            WHERE s.name IN $symptoms
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
