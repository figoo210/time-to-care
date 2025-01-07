import json
from db_mongodb import client

# Load the JSON data from the file
with open('./files/patient_data.json', 'r') as file:
    patient_data = json.load(file)

# Connect to MongoDB
db = client['time_to_care']
collection = db['patients']

# Insert the data into the MongoDB collection
collection.insert_many(patient_data)

print("Data inserted successfully")