import pandas as pd
import numpy as np
import random
import time
from datetime import datetime, tzinfo, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2
from bson import ObjectId
from collections import defaultdict
import streamlit as st
from db_sqlite import get_connection, fetch_data
from db_neo4j import Neo4jConnection
from db_mongodb import client
from mapping_hospitals_to_dict import get_hospitals
from scipy.optimize import linear_sum_assignment


# Workflow

# 1. Real-time Data Collection


# Function to add hospital queue data to MongoDB
def add_hospital_queue_data(data):
    # Access the 'time_to_care' database and the 'hospital_queue' collection
    hospital_queue = client["time_to_care"]["hospital_queue"]

    # Insert the data into the MongoDB collection
    hospital_queue.insert_one(data)

    # Return the data that was added
    return data


# Optional Function to simulate real-time data collection
def simulate_real_time_data():
    if st.session_state.get("simulate_data", False):  # Check if simulation is active
        # Generate random data
        data = {
            "hospital_id": random.choice(
                ["Hospital A", "Hospital B", "Hospital C", "Hospital D", "Hospital E"]
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "wait_time": random.randint(1, 120),
            "triage_code": random.choice(["Green", "Yellow", "Red"]),
        }
        # Add the generated data to the MongoDB database
        add_hospital_queue_data(data)
        # Print a message to indicate that the data has been added
        print("Simulated real-time data added to MongoDB database.")
        # Sleep for a few seconds to simulate real-time data collection
        time.sleep(60)  # Sleep for 60 seconds (1 minute)
        simulate_real_time_data()  # Recursively call the function to continue data collection


####################################################################################################


# 2. Data Processing


# Helper function to compute the start of the week
def get_week_start(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    week_start = date_obj - timedelta(days=date_obj.weekday())  # Monday as the start
    return week_start.strftime("%Y-%m-%d")


# Function to update historical wait times with weekly aggregation and date filtering
def update_historical_wait_times(data):
    # Establish SQLite connection
    conn = get_connection()

    # Dictionary to aggregate wait times by week
    weekly_aggregates = defaultdict(list)

    # Process the data to compute weekly aggregates
    for row in data:
        hospital_id = row["hospital_id"]
        date = row["date"]
        triage_code = row["triage_code"]
        wait_time = row["wait_time"]

        # Calculate week_start
        week_start = get_week_start(date)

        # Only process data for weeks starting after December 1, 2024
        if week_start > "2024-12-01":
            key = (hospital_id, triage_code, week_start)
            weekly_aggregates[key].append(wait_time)

    # Prepare data for insertion or update
    aggregated_data = [
        (hospital_id, triage_code, week_start, sum(times) / len(times))
        for (hospital_id, triage_code, week_start), times in weekly_aggregates.items()
    ]

    # Insert or update data in the database
    for hospital_id, triage_code, week_start, avg_wait_time in aggregated_data:
        conn.execute(
            """
            INSERT INTO historical_wait_times (hospital_id, triage_code, week_start, average_wait_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(hospital_id, triage_code, week_start)
            DO UPDATE SET average_wait_time = excluded.average_wait_time
            """,
            (hospital_id, triage_code, week_start, avg_wait_time),
        )

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

    # Return True indicating successful update
    return True


# Function to get the average wait time for a specific hospital and triage code
def get_wait_time_average(hospital_id, triage_code):
    # Establish SQLite connection
    conn = get_connection()

    # Fetch the average wait time for the hospital and triage code
    result = conn.execute(
        """
        SELECT AVG(average_wait_time)
        FROM historical_wait_times
        WHERE hospital_id = ? AND triage_code = ?
        """,
        (hospital_id, triage_code),
    ).fetchone()

    # Close the connection
    conn.close()

    # Return the average wait time or None if no data found
    return result[0] if result and result[0] is not None else None


# Function to retrieve average wait times for all hospitals and triage codes
def get_hospital_wait_times():
    # Establish SQLite connection
    conn = get_connection()

    # Fetch historical wait times grouped by hospital and triage code
    result = conn.execute(
        """
        SELECT hospital_id, triage_code, AVG(average_wait_time) AS avg_wait_time
        FROM historical_wait_times
        GROUP BY hospital_id, triage_code
        """
    ).fetchall()

    # Close the connection
    conn.close()

    # Process the results into a list of dictionaries
    wait_times = [
        {"hospital_id": row[0], "triage_code": row[1], "avg_wait_time": row[2]}
        for row in result
    ]

    # Return the list of wait times
    return wait_times


# Function to get the average wait time for a specific hospital and triage code for the last week
def get_wait_time_average_last_week(hospital_id, triage_code):
    # Establish SQLite connection
    conn = get_connection()

    # Fetch the most recent week_start date
    last_week_start = conn.execute(
        """
        SELECT MAX(week_start)
        FROM historical_wait_times
        """
    ).fetchone()[0]

    # If there is no data, return None
    if not last_week_start:
        conn.close()
        return None

    # Fetch the average wait time for the hospital and triage code for the last week
    result = conn.execute(
        """
        SELECT AVG(average_wait_time)
        FROM historical_wait_times
        WHERE hospital_id = ? AND triage_code = ? AND week_start = ?
        """,
        (hospital_id, triage_code, last_week_start),
    ).fetchone()

    # Close the connection
    conn.close()

    # Return the average wait time or None if no data found
    return result[0] if result and result[0] is not None else None


# Function to retrieve average wait times for all hospitals and triage codes for the last week
def get_hospital_wait_times_last_week():
    # Establish SQLite connection
    conn = get_connection()

    # Fetch the most recent week_start date
    last_week_start = conn.execute(
        """
        SELECT MAX(week_start)
        FROM historical_wait_times
        """
    ).fetchone()[0]

    # If there is no data, return an empty list
    if not last_week_start:
        conn.close()
        return []

    # Fetch historical wait times grouped by hospital and triage code for the last week
    result = conn.execute(
        """
        SELECT hospital_id, triage_code, AVG(average_wait_time) AS avg_wait_time
        FROM historical_wait_times
        WHERE week_start = ?
        GROUP BY hospital_id, triage_code
        """,
        (last_week_start,),
    ).fetchall()

    # Close the connection
    conn.close()

    # Process the results into a list of dictionaries
    wait_times = [
        {"hospital_id": row[0], "triage_code": row[1], "avg_wait_time": row[2]}
        for row in result
    ]

    # Return the list of wait times
    return wait_times


# Function to get the total average wait time for a specific hospital
def get_hospital_average(hospital_id):
    # Establish SQLite connection
    conn = get_connection()

    # Fetch the total average wait time for the hospital
    result = conn.execute(
        """
        SELECT AVG(average_wait_time)
        FROM historical_wait_times
        WHERE hospital_id = ?
        """,
        (hospital_id,),
    ).fetchone()

    # Close the connection
    conn.close()

    # Return the total average wait time or None if no data found
    return result[0] if result and result[0] is not None else None


# Function to load hospital data from the Neo4j database
def load_hospitals():
    # Establish a connection to the Neo4j database
    neo4j_conn = Neo4jConnection()

    if neo4j_conn.is_connected:
        # Query Neo4j for hospital data
        hospitals = neo4j_conn.query(
            "MATCH (h:Hospital) RETURN h.name AS name, h.latitude AS latitude, h.longitude AS longitude, h.specialization AS specialization"
        )
        # Close the connection to the Neo4j database
        neo4j_conn.close()
    else:

        hospitals = get_hospitals()
        print("########################### Using local hospital data.")

    # Process the results into a list of dictionaries
    results = []
    for hospital in hospitals:
        results.append(
            {
                "name": hospital["name"],
                "latitude": hospital["latitude"],
                "longitude": hospital["longitude"],
                "specialization": hospital["specialization"],
            }
        )

    # Return the list of hospital data
    return results


# Function to load patient data from MongoDB
def load_patient_data():
    # Access the 'time_to_care' database and the 'patients' collection
    patients_collection = client["time_to_care"]["patients"]

    # Convert the MongoDB cursor to a list
    patients = list(patients_collection.find())  # Convert cursor to a list

    # Ensure all data is serializable by converting ObjectId to string
    for patient in patients:
        if "_id" in patient:
            patient["_id"] = str(patient["_id"])

    # Return the list of patient data
    return patients


# Function to add a new patient to MongoDB
def add_patient_to_db(patient):
    # Access the 'time_to_care' database and the 'patients' collection
    patients_collection = client["time_to_care"]["patients"]

    # Insert the patient data into the MongoDB collection
    patients_collection.insert_one(patient)

    # Return the data that was added
    return patient


# Function to remove a patient from MongoDB by their ID
def remove_patient_from_db(patient_id):
    # Ensure the patient_id is in ObjectId format if it's a string
    if isinstance(patient_id, str):
        patient_id = ObjectId(patient_id)

    # Access the 'time_to_care' database and the 'patients' collection
    patients_collection = client["time_to_care"]["patients"]

    # Delete the patient with the specified ID
    result = patients_collection.delete_one({"_id": patient_id})

    # Return True if the patient was successfully deleted
    return result.deleted_count > 0


####################################################################################################


# 3.  Symptoms Mapping


# Function to load symptom-to-specialization mapping from Neo4j
def load_symptom_to_specialization():
    # Establish a connection to the Neo4j database
    neo4j_conn = Neo4jConnection()

    # Query Neo4j for symptom-specialization relationships
    results = neo4j_conn.query(
        "MATCH (s:Symptom)-[:TREATED_AT]->(h:Hospital) RETURN s.name AS symptom, h.specialization AS specialization"
    )

    # Close the connection to the Neo4j database
    neo4j_conn.close()

    # Convert the results into a dictionary mapping symptoms to specializations
    symptom_to_specialization = {
        result["symptom"]: result["specialization"] for result in results
    }

    # Return the mapping dictionary
    return symptom_to_specialization


# Function to load symptom-to-specialization mapping from SQLite
def load_symptom_to_specialization_table():
    # Establish a connection to the SQLite database
    sqlite_conn = get_connection()
    sqlite_cursor = sqlite_conn.cursor()

    # Query SQLite for symptom-specialization relationships
    sqlite_cursor.execute("SELECT symptom_name, specialization FROM Symptoms")
    results = sqlite_cursor.fetchall()

    # Close the connection to the SQLite database
    sqlite_conn.close()

    # Convert the results into a dictionary mapping symptoms to specializations
    symptom_to_specialization = {row[0]: row[1] for row in results}

    # Return the mapping dictionary
    return symptom_to_specialization


####################################################################################################


# 4. Hospital Recommendations


# Haversine function to calculate the great-circle distance between two points (latitude and longitude) on Earth
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    # Convert latitude and longitude from degrees to radians
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    # Haversine formula to calculate the great-circle distance
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Return the distance in kilometers
    return R * c


def get_current_queue_size(hospital_name):
    """
    Retrieves the current queue size for a specific hospital by name.

    Args:
        hospital_name (str): The name of the hospital.

    Returns:
        int: The number of patients currently in the queue for the specified hospital.
    """
    # Get the collection
    collection = client["time_to_care"]["hospital_queue"]

    # Get the current timestamp in the format used in the database
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Query the collection to count patients currently in the queue for the hospital
    results = collection.aggregate(
        [
            {
                "$addFields": {
                    "end_time": {
                        "$add": [
                            {"$dateFromString": {"dateString": "$timestamp"}},
                            {"$multiply": ["$wait_time", 60000]},
                        ]
                    }
                }
            },
            {"$match": {"end_time": {"$gte": datetime.now(tz=timezone.utc)}}},
            {"$match": {"hospital_id": hospital_name}},
            {"$count": "active_hospital_queues"},
        ]
    )
    queue_size = list(results)
    return queue_size[0]["active_hospital_queues"] if queue_size else 0


# Recommend a hospital for a single patient
def recommend_hospital(patient, hospitals, symptom_to_specialization, triage_code):
    patient_lat, patient_lon = patient["Latitude"], patient["Longitude"]
    patient_symptoms = patient["Symptoms"]

    # Step 1: Map symptoms to relevant specializations
    relevant_specializations = set(
        symptom_to_specialization[symptom]
        for symptom in patient_symptoms
        if symptom in symptom_to_specialization
    )

    # Step 2: Filter hospitals by specialization
    candidate_hospitals = [
        hospital
        for hospital in hospitals
        if hospital["specialization"] in relevant_specializations
    ]

    # Step 3: Calculate scores (distance + wait time + queue effect)
    scores = []
    for hospital in candidate_hospitals:
        distance = haversine(
            float(patient_lat),
            float(patient_lon),
            float(hospital["latitude"]),
            float(hospital["longitude"]),
        )
        avg_wait_time = get_wait_time_average_last_week(hospital["name"], triage_code)
        current_queue_size = get_current_queue_size(hospital["name"])
        queue_factor = current_queue_size * 2  # Weight for queue size

        # Combine factors into the score
        score = distance + avg_wait_time / 10 + queue_factor
        scores.append(
            {
                "hospital": hospital["name"],
                "score": score,
                "distance": distance,
                "wait_time": avg_wait_time,
                "queue_size": current_queue_size,
                "triage_code": triage_code,
            }
        )

    # Step 4: Sort by score and return the best match
    if scores:
        best_hospital = min(scores, key=lambda x: x["score"])
        # Return as a pandas DataFrame
        return pd.DataFrame([best_hospital])

    # If no hospitals found, return None
    return None


# Recommend hospitals for a group using optimization
def recommend_hospitals_for_group_optimized(
    patients, hospitals, symptom_to_specialization
):
    # Step 1: Group patients by specialization
    specialization_to_patients = defaultdict(list)
    for patient in patients:
        for symptom in patient["Symptoms"]:
            if symptom in symptom_to_specialization:
                specialization = symptom_to_specialization[symptom]
                specialization_to_patients[specialization].append(patient)
                break  # Assign to the first matching specialization

    # Step 2: Assign patients to hospitals
    assignments = []
    for specialization, patient_group in specialization_to_patients.items():
        # Filter hospitals by specialization
        candidate_hospitals = [
            hospital
            for hospital in hospitals
            if hospital["specialization"] == specialization
        ]

        if not candidate_hospitals:
            continue  # Skip if no hospitals match this specialization

        # Step 3: Create cost matrix (patients x hospitals)
        cost_matrix = np.zeros((len(patient_group), len(candidate_hospitals)))

        for i, patient in enumerate(patient_group):
            for j, hospital in enumerate(candidate_hospitals):
                # Calculate distance between patient and hospital
                distance = haversine(
                    float(patient["Latitude"]),
                    float(patient["Longitude"]),
                    float(hospital["latitude"]),
                    float(hospital["longitude"]),
                )
                # Get hospital's average wait time and queue size
                avg_wait_time = get_wait_time_average_last_week(
                    hospital["name"], "Green"
                )
                queue_size = get_current_queue_size(hospital["name"])

                # Compute cost: weighted distance + wait time + queue size
                cost_matrix[i, j] = 1.5 * distance + avg_wait_time / 10 + 2 * queue_size

        # Step 4: Solve assignment problem
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Step 5: Record assignments
        for patient_idx, hospital_idx in zip(row_ind, col_ind):
            patient = patient_group[patient_idx]
            hospital = candidate_hospitals[hospital_idx]
            assignments.append(
                {
                    "patient": patient["Name"],
                    "hospital": hospital["name"],
                    "distance": haversine(
                        float(patient["Latitude"]),
                        float(patient["Longitude"]),
                        float(hospital["latitude"]),
                        float(hospital["longitude"]),
                    ),
                    "wait_time": get_wait_time_average_last_week(
                        hospital["name"], "Green"
                    ),
                    "queue_size": get_current_queue_size(hospital["name"]),
                    "specialization": specialization,
                    "triage_code": "Green",
                }
            )

    # Return the final assignments
    return pd.DataFrame(assignments)


####################################################################################################


# 5. Visualization and Reporting


# Function to count the number of patients on the waiting list for each hospital
def count_waiting_list_patients():
    """
    Counts the number of patients on the waiting list for each hospital,
    considering only those who haven't passed their expected discharge time.

    Returns:
        A list of dictionaries, where each dictionary contains the hospital ID
        and the number of patients still on the waiting list.
    """
    # Get the collection
    collection = client["time_to_care"]["hospital_queue"]

    # Get the current timestamp in a format compatible with MongoDB
    current_timestamp = datetime.now(tz=timezone.utc)

    # Define the aggregation pipeline
    pipeline = [
        {
            "$addFields": {
                "end_time": {
                    "$add": [
                        {
                            "$dateFromString": {"dateString": "$timestamp"}
                        },  # Convert timestamp if it's a string
                        {
                            "$multiply": ["$wait_time", 60000]
                        },  # Convert wait_time to milliseconds
                    ]
                }
            }
        },
        {
            "$match": {
                "end_time": {
                    "$gte": current_timestamp
                }  # Match only those whose end_time hasn't passed
            }
        },
        {
            "$group": {
                "_id": "$hospital_id",  # Group by hospital_id
                "num_patients": {"$sum": 1},  # Count the number of patients
            }
        },
    ]

    # Execute the aggregation pipeline
    result = list(collection.aggregate(pipeline))

    # Process the results into a list of dictionaries
    waiting_list_counts = [
        {"hospital_id": item["_id"], "num_patients": item["num_patients"]}
        for item in result
    ]

    return waiting_list_counts


# Function to count patients on the waiting list for each hospital and their triage code
def count_waiting_list_patients_by_triage():
    """
    Counts the number of patients on the waiting list for each hospital grouped by triage code,
    considering only those who haven't passed their expected discharge time.

    Returns:
        A dictionary where each hospital ID maps to another dictionary
        of triage codes and their corresponding patient counts.
    """
    # Get the collection
    collection = client["time_to_care"]["hospital_queue"]

    # Get the current timestamp in a format compatible with MongoDB
    current_timestamp = datetime.now(tz=timezone.utc)

    # Define the aggregation pipeline
    pipeline = [
        {
            "$addFields": {
                "end_time": {
                    "$add": [
                        {
                            "$dateFromString": {"dateString": "$timestamp"}
                        },  # Convert timestamp if it's a string
                        {
                            "$multiply": ["$wait_time", 60000]
                        },  # Convert wait_time to milliseconds
                    ]
                }
            }
        },
        {
            "$match": {
                "end_time": {
                    "$gte": current_timestamp
                }  # Match only those whose end_time hasn't passed
            }
        },
        {
            "$group": {
                "_id": {
                    "hospital_id": "$hospital_id",
                    "triage_code": "$triage_code",
                },  # Group by hospital_id and triage_code
                "num_patients": {"$sum": 1},  # Count the number of patients
            }
        },
    ]

    # Execute the aggregation pipeline
    result = list(collection.aggregate(pipeline))

    # Process the results into a nested dictionary
    waiting_list_counts = {}
    for item in result:
        hospital_id = item["_id"]["hospital_id"]
        triage_code = item["_id"]["triage_code"]
        num_patients = item["num_patients"]

        if hospital_id not in waiting_list_counts:
            waiting_list_counts[hospital_id] = {}

        waiting_list_counts[hospital_id][triage_code] = num_patients

    return waiting_list_counts


def count_patients_in_queue():
    """
    Calculates the number of patients currently in the queue for each hospital,
    based on the timestamp and wait_time, considering only those who haven't passed
    their expected discharge time.

    Returns:
        A dictionary where each hospital ID maps to the count of patients in the queue.
    """
    # Get the collection
    collection = client["time_to_care"]["hospital_queue"]

    # Get the current timestamp in a format compatible with MongoDB
    current_timestamp = datetime.now(tz=timezone.utc)

    # Define the aggregation pipeline
    pipeline = [
        {
            "$addFields": {
                "end_time": {
                    "$add": [
                        {
                            "$dateFromString": {"dateString": "$timestamp"}
                        },  # Convert timestamp if it's a string
                        {
                            "$multiply": ["$wait_time", 60000]
                        },  # Convert wait_time to milliseconds
                    ]
                }
            }
        },
        {
            "$match": {
                "end_time": {
                    "$gte": current_timestamp
                }  # Match only those whose end_time hasn't passed
            }
        },
        {
            "$group": {
                "_id": "$hospital_id",  # Group by hospital_id
                "num_patients": {"$sum": 1},  # Count the number of patients
            }
        },
    ]

    # Execute the aggregation pipeline
    result = list(collection.aggregate(pipeline))

    # Process the results into a dictionary
    patients_in_queue = {item["_id"]: item["num_patients"] for item in result}

    return patients_in_queue
