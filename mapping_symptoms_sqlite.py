from db_sqlite import get_connection
import json


# Load symptoms data from JSON file
with open("./files/symptoms_data.json", "r") as file:
    symptoms_data = json.load(file)

# Initialize SQLite connection
sqlite_conn = get_connection()
sqlite_cursor = sqlite_conn.cursor()


# Insert data into SQLite table
for symptom in symptoms_data:
    symptom_name = symptom["Symptom"]
    specialization = symptom["Specialization"]
    sqlite_cursor.execute("""
        INSERT INTO Symptoms (symptom_name, specialization)
        VALUES (?, ?)
    """, (symptom_name, specialization))

# Commit and close SQLite connection
sqlite_conn.commit()
sqlite_conn.close()

