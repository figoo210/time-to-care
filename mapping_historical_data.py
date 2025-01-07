import json
from db_sqlite import get_connection, insert_data
from datetime import datetime, timedelta


# Load historical data
with open("./files/historical_patient_data.json", "r") as file:
    historical_data = json.load(file)


# Helper function to compute the start of the week
def get_week_start(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    week_start = date_obj - timedelta(days=date_obj.weekday())  # Monday as the start
    return week_start.strftime("%Y-%m-%d")


# Aggregate historical data into weekly averages
weekly_aggregates = {}
for hospital in historical_data:
    hospital_id = hospital["Hospital"]
    for day_data in hospital["Daily_Data"]:
        date = day_data["Date"]
        week_start = get_week_start(date)
        for patient in day_data["Patients"]:
            triage_code = patient["Triage_Code"]
            wait_time = patient["Wait_Time_Minutes"]

            key = (hospital_id, triage_code, week_start)
            if key not in weekly_aggregates:
                weekly_aggregates[key] = []
            weekly_aggregates[key].append(wait_time)

# Calculate averages and insert into the table
aggregated_data = [
    (hospital_id, triage_code, week_start, sum(times) / len(times))
    for (hospital_id, triage_code, week_start), times in weekly_aggregates.items()
]

print("Inserting historical data into SQLite...")
connection = get_connection()
for data in aggregated_data:
    insert_data(connection, "historical_wait_times", data)
print("Historical data inserted into SQLite!")
