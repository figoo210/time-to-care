import csv


def get_hospitals():
    # Read hospital data
    hospital_data = {}
    with open("./files/hospital_data.csv", mode="r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            hospital_data[row["Hospital"]] = {"Specialization": row["Specialization"]}

    # Read hospital geospatial data and merge with hospital data
    with open("./files/hospital_geospatial_data.csv", mode="r") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            if row["Hospital"] in hospital_data:
                hospital_data[row["Hospital"]].update(
                    {"Latitude": row["Latitude"], "Longitude": row["Longitude"]}
                )

    # Create Hospital dict
    hospitals = []
    for hospital, data in hospital_data.items():
        hospitals.append(
            {
                "name": hospital,
                "specialization": data["Specialization"],
                "latitude": data["Latitude"],
                "longitude": data["Longitude"],
            }
        )
    return hospitals
