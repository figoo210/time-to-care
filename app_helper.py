import pandas as pd
import plotly.express as px
import streamlit as st
import folium
from streamlit_folium import st_folium
from tabulate import tabulate
from datetime import datetime
from helpers import *
from db_neo4j import Neo4jConnection


# Load Data
@st.cache_data
def load_data():
    """
    Load the necessary data from sources like hospitals, symptoms, patients, and wait times.
    Cache the data to speed up subsequent loads.
    """
    hospitals = load_hospitals()  # Load hospital data
    symptoms = (
        load_symptom_to_specialization()
    )  # Load symptom-to-specialization mapping
    patients = load_patient_data()  # Load patient data
    wait_times = get_hospital_wait_times()  # Load hospital wait times data
    wait_times_last_week = (
        get_hospital_wait_times_last_week()
    )  # Load hospital wait times data for last week

    # Return the datasets in a dictionary for further use
    return {
        "hospitals": hospitals,
        "symptoms": symptoms,
        "patients": patients,
        "wait_times": wait_times,
        "wait_times_last_week": wait_times_last_week,
    }


# Sidebar Filters
def sidebar_filters(hospitals, symptoms, specializations):
    """
    Render the sidebar filters and return the selected filters for hospitals, symptoms, and specializations.
    """
    st.sidebar.title("Filters")  # Set the sidebar title

    # Filter by hospital names
    hospital_names = [h["name"] for h in hospitals]
    selected_hospitals = st.sidebar.multiselect(
        "Filter by Hospital", hospital_names, default=None
    )

    # Filter by symptoms
    symptom_names = list(symptoms.keys())
    selected_symptoms = st.sidebar.multiselect(
        "Filter by Symptoms", symptom_names, default=None
    )

    # Filter by specializations
    selected_specializations = st.sidebar.multiselect(
        "Filter by Specialization", specializations, default=None
    )

    # Return the selected filters in a dictionary
    return {
        "selected_hospitals": selected_hospitals,
        "selected_symptoms": selected_symptoms,
        "selected_specializations": selected_specializations,
    }


# Add KPIs
@st.cache_data
def calculate_kpis(
    hospitals,
    patients,
    wait_times,
    filter_hospitals=None,
    filter_symptoms=None,
    filter_specializations=None,
):
    """
    Calculate Key Performance Indicators (KPIs) based on provided datasets and optional filters.
    KPIs include total hospitals, total patients, and average wait time.
    """
    # Apply the hospital filters
    if filter_hospitals:
        hospitals = [h for h in hospitals if h["name"] in filter_hospitals]

    # Apply the specialization filters
    if filter_specializations:
        hospitals = [
            h for h in hospitals if h["specialization"] in filter_specializations
        ]

    # Apply symptom filters for patients
    if filter_symptoms:
        patients = [
            p
            for p in patients
            if any(symptom in p["Symptoms"] for symptom in filter_symptoms)
        ]

    # Apply the hospital filter to wait times
    if filter_hospitals:
        wait_times = [
            w for w in wait_times if w["hospital_id"] in {h["name"] for h in hospitals}
        ]

    # Calculate total hospitals, total patients, and average wait time
    total_hospitals = len(hospitals)
    total_patients = len(patients)

    avg_wait_time = (
        f"{sum(w['avg_wait_time'] for w in wait_times) / len(wait_times):.2f}"
        if wait_times
        else "N/A"
    )
    total_patients_in_queue = sum(count_patients_in_queue().values() or [0])

    # Return the KPIs
    return [total_hospitals, total_patients_in_queue, avg_wait_time, total_patients]


def display_kpi_metrics(kpis, kpi_names):
    """
    Display the calculated KPIs in a well-organized layout.
    """
    st.header("KPI Metrics")
    for i, (col, (kpi_name, kpi_value)) in enumerate(
        zip(st.columns(4), zip(kpi_names, kpis))
    ):
        col.metric(label=kpi_name, value=kpi_value)


# Average Wait Times
def display_wait_times(wait_times):
    """
    Display a table of average wait times for each hospital and triage code.
    """
    st.header("Average Wait Times")
    # Create a DataFrame for the wait times
    wait_times = pd.DataFrame(
        wait_times, columns=["Hospital", "Triage Code", "Average Wait Time"]
    )
    # Display the dataframe
    st.dataframe(wait_times)


# Tables
def display_patients_on_waiting_list(patients, symptoms_to_specialization, filters):
    """
    Display a table of patients on the waiting list with applied filters for symptoms and specializations.
    """
    st.header("Unassigned Patients")

    # Apply filters based on symptoms
    if filters["selected_symptoms"]:
        patients = [
            p
            for p in patients
            if any(symptom in filters["selected_symptoms"] for symptom in p["Symptoms"])
        ]

    # Apply filters based on specializations using symptom-to-specialization mapping
    if filters["selected_specializations"]:
        patients = [
            p
            for p in patients
            if any(
                symptoms_to_specialization.get(symptom)
                in filters["selected_specializations"]
                for symptom in p["Symptoms"]
            )
        ]

    # If no patients match the filters, show a message
    if not patients:
        st.write("No patients found matching the selected filters.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            # Display patient data in a table format
            patients_df = pd.DataFrame(patients)
            st.dataframe(patients_df[["Name", "Symptoms"]])

        with col2:
            # Prepare data for the chart
            symptom_counts = {}
            for patient in patients:
                for symptom in patient["Symptoms"]:
                    symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1

            # Create a DataFrame for the chart
            chart_df = pd.DataFrame.from_dict(
                symptom_counts, orient="index", columns=["Count"]
            )
            chart_df.index.name = "Symptom"
            chart_df = chart_df.reset_index()  # Reset index to make 'Symptom' a column

            # Create a bar chart using Plotly Express
            fig = px.bar(
                chart_df,
                x="Symptom",
                y="Count",
                title="Patient Counts by Symptom",
                labels={"Count": "Number of Patients"},
                text="Count",  # Add values as text on top of bars
            )
            fig.update_traces(textposition="inside", textfont_size=14)
            st.plotly_chart(fig)


def display_hospitals_wait_times(hospitals, wait_times, filters):
    """
    Display the average wait times for hospitals based on applied filters.
    """

    st.header("Hospitals Average Wait Times (Last Week)")
    # Apply hospital and specialization filters
    if filters["selected_hospitals"]:
        hospitals = [h for h in hospitals if h["name"] in filters["selected_hospitals"]]
    if filters["selected_specializations"]:
        hospitals = [
            h
            for h in hospitals
            if h["specialization"] in filters["selected_specializations"]
        ]

    # Filter wait times by selected hospitals
    filtered_wait_times = [
        wt for wt in wait_times if wt["hospital_id"] in [h["name"] for h in hospitals]
    ]

    # Create a DataFrame for easier manipulation
    wait_times_df = pd.DataFrame(filtered_wait_times)

    # Group by hospital and triage code, calculate average wait time
    grouped_df = (
        wait_times_df.groupby(["hospital_id", "triage_code"])["avg_wait_time"]
        .mean()
        .reset_index()
    )

    # Pivot the DataFrame for better visualization
    pivot_df = grouped_df.pivot_table(
        index="hospital_id", columns="triage_code", values="avg_wait_time", fill_value=0
    )

    color_map = {
        "Red": "red",
        "Yellow": "yellow",
        "Green": "green",
    }

    col1, col2 = st.columns(2)
    with col1:
        # Create a plotly bar chart
        fig = px.bar(
            pivot_df,
            barmode="group",
            title="Average Wait Times by Hospital and Triage Code",
            color_discrete_map=color_map,
        )
        st.plotly_chart(fig)

    with col2:
        # Display the table
        st.dataframe(pivot_df)


def create_plotly_chart(counts_by_hospital_triage):
    """
    Creates a plotly bar chart of patient counts by hospital and triage code.

    Args:
        counts_by_hospital_triage: A dictionary containing the patient counts.

    Returns:
        A plotly figure object.
    """

    # Convert the dictionary to a pandas DataFrame
    df = (
        pd.DataFrame.from_dict(counts_by_hospital_triage, orient="index")
        .stack()
        .reset_index()
    )
    df.columns = ["Hospital", "Triage Code", "Patients Number"]

    color_map = {
        "Red": "red",
        "Yellow": "yellow",
        "Green": "green",
    }

    # Create the bar chart
    fig = px.bar(
        df,
        x="Hospital",
        y="Patients Number",
        color="Triage Code",
        barmode="group",
        title="Patient Counts by Hospital and Triage Code",
        color_discrete_map=color_map,
    )

    return fig


def combined_hospital_patient_counts(filters):
    """
    Display the number of patients by hospital and triage code in a combined table
    with applied filters.

    Args:
        filters: A dictionary containing the applied filters (e.g., selected_hospitals, selected_specializations).
    """
    st.header("Hospital-wise Patient Counts")

    # Get patient counts
    patient_counts_per_hospital = count_waiting_list_patients()
    counts_by_hospital_triage = count_waiting_list_patients_by_triage()

    # Filter patient_counts_per_hospital (if needed)
    if filters.get("selected_hospitals"):
        patient_counts_per_hospital = [
            h
            for h in patient_counts_per_hospital
            if h["hospital_id"] in filters["selected_hospitals"]
        ]

        counts_by_hospital_triage = {
            h: counts_by_hospital_triage[h]
            for h in counts_by_hospital_triage
            if h in filters["selected_hospitals"]
        }

    # Extract keys from the first dictionary to use as headers
    headers = {"Hospital", "Total Patients"}

    # Find all unique triage codes
    all_triage_codes = set()
    for triage_counts in counts_by_hospital_triage.values():
        all_triage_codes.update(triage_counts.keys())

    # Create a list to hold the table data
    table_data = []

    # Iterate through hospitals
    for hospital_data in patient_counts_per_hospital:
        hospital_id = hospital_data["hospital_id"]
        row_data = [
            hospital_id,
            hospital_data["num_patients"],
        ]  # Add hospital ID and total count
        for triage_code in all_triage_codes:
            row_data.append(
                counts_by_hospital_triage.get(hospital_id, {}).get(triage_code, 0)
            )
        table_data.append(row_data)

    # Create headers
    headers = ["Hospital", "Total Patients"] + list(all_triage_codes)

    # Display the table
    st.code(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Create and display the Plotly chart
    fig = create_plotly_chart(counts_by_hospital_triage)
    st.plotly_chart(fig)


# Actions
def manage_patient_form_internal(symptoms_data):
    """
    Sidebar form to add new patients, including their symptoms, latitude, and longitude.
    """
    # Toggle button for form visibility
    show_form = st.sidebar.checkbox("Add New Patient", value=False)

    # Display form if toggled on
    if show_form:
        st.sidebar.header("Add New Patient")
        with st.sidebar.form("Add Patient Form", clear_on_submit=True):
            # Collect patient details
            name = st.text_input("Name")
            symptoms = st.multiselect("Symptoms", options=symptoms_data)
            latitude = st.text_input("Latitude")
            longitude = st.text_input("Longitude")

            # Submit button
            submitted = st.form_submit_button("Submit")

            if submitted:
                if name and symptoms:
                    # Add the new patient (replace with actual database API)
                    new_patient = {
                        "Name": name,
                        "Symptoms": symptoms,
                        "Latitude": latitude,
                        "Longitude": longitude,
                    }
                    # Add patient to database (replace with actual function)
                    add_patient_to_db(new_patient)
                    st.sidebar.success(f"New patient {name} added successfully!")
                    return True
                else:
                    st.sidebar.error("Please fill out all required fields.")
    return False


# Checkbox to simulate real-time data from hospitals
def simulate_hospitals_realtime_data():
    """
    Checkbox to simulate real-time data from hospitals.
    """
    if st.sidebar.checkbox("Simulate Real-Time Data", value=False):
        st.sidebar.info(
            "Simulating real-time data from hospitals. This will update the data every minute."
        )
        simulate_real_time_data()


def recommend_hospital_for_patient(patients, symptom_to_specialization, hospitals):
    """
    Form for recommending a hospital based on patient symptoms and triage code.
    """
    st.header("Recommend a Hospital for a Patient")
    with st.form("Recommend a Hospital Form", clear_on_submit=True):
        # Select a patient
        patient_names = [p["Name"] for p in patients]
        patient_name = st.selectbox("Select Patient", options=patient_names, index=None)
        triage_code = st.selectbox(
            "Select Triage Code", options=["Green", "Yellow", "Red"], index=None
        )

        # Submit button
        submitted = st.form_submit_button("Submit")
        if submitted:
            selected_patient = next(p for p in patients if p["Name"] == patient_name)
            recommended_hospital = recommend_hospital(
                selected_patient, hospitals, symptom_to_specialization, triage_code
            )
            st.session_state["selected_patient"] = selected_patient
            st.session_state["recommended_hospital"] = recommended_hospital
            return selected_patient, recommended_hospital
    return None, None


def display_hospital_recommendation(patient, recommended_hospital):
    """
    Display the hospital recommendation for a selected patient.
    """
    st.header("Hospital Recommendation")
    st.write("Patient Symptoms:", patient["Symptoms"])

    # If a recommendation is found, display the details
    if not recommended_hospital.empty:
        hospital_info = recommended_hospital.iloc[0]
        hospital_name = hospital_info["hospital"]
        hospital_data = [
            ["Hospital Name", hospital_name],
            ["Score", round(hospital_info["score"], 2)],
            ["Distance (km)", round(hospital_info["distance"], 2)],
            ["Waiting Time (Minutes)", round(hospital_info["wait_time"], 2)],
        ]
        # Display hospital information as a table
        st.code(
            tabulate(hospital_data, headers=["Attribute", "Value"], tablefmt="grid")
        )

        accepted = st.button("Accept Recommendation and See the Map")
        if accepted:
            st.session_state["recommendation_accepted"] = True
            st.session_state["selected_hospital_name"] = hospital_name
            st.success(f"Recommendation accepted for {hospital_name}!")
            # Save the hospital queue data and remove patient from database (replace with actual functions)
            add_hospital_queue_data(
                {
                    "hospital_id": hospital_name,
                    "triage_code": hospital_info["triage_code"],
                    "wait_time": round(hospital_info["wait_time"], 2),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                }
            )
            remove_patient_from_db(patient["_id"])
            # Connect to Neo4J to add the patient
            neo4j = Neo4jConnection()
            patient["triageCode"] = hospital_info["triage_code"]
            neo4j.create_patient_node(patient_data=patient)
            neo4j.add_symptom_relationships(
                patient_name=patient["Name"], symptoms=patient["Symptoms"]
            )

    else:
        st.warning("No hospital recommendation available.")


def display_map(hospitals, patients, symptom_to_specialization):
    """
    Display map with patient and hospital information.
    """
    # Ensure session state variables exist
    if "selected_patient" not in st.session_state:
        st.session_state["selected_patient"] = None
    if "recommended_hospital" not in st.session_state:
        st.session_state["recommended_hospital"] = pd.DataFrame()
    if "recommendation_accepted" not in st.session_state:
        st.session_state["recommendation_accepted"] = False
    if "selected_hospital_name" not in st.session_state:
        st.session_state["selected_hospital_name"] = None

    # Recommend hospital
    if not st.session_state["recommendation_accepted"]:
        recommend_hospital_for_patient(patients, symptom_to_specialization, hospitals)

    selected_patient = st.session_state["selected_patient"]
    recommended_hospital = st.session_state["recommended_hospital"]

    # Display recommendation
    if selected_patient and not st.session_state["recommendation_accepted"]:
        display_hospital_recommendation(selected_patient, recommended_hospital)

    # Create the map
    starting_location = (45.470999, 9.184322)
    m = folium.Map(location=starting_location, zoom_start=13, key="patient_map")

    # Add hospital markers
    for row in hospitals:
        folium.Marker(
            location=(row["latitude"], row["longitude"]),
            popup=f"{row['name']} ({row['specialization']})",
            icon=folium.Icon(color="red"),
        ).add_to(m)

    # Add patient marker and line if recommendation is accepted
    if st.session_state["recommendation_accepted"] and selected_patient:
        folium.Marker(
            location=(
                float(selected_patient["Latitude"]),
                float(selected_patient["Longitude"]),
            ),
            popup=f"Patient: {selected_patient['Name']} ({selected_patient['Symptoms']})",
            icon=folium.Icon(color="green"),
        ).add_to(m)

        # Add a line to the recommended hospital
        if not recommended_hospital.empty:
            hospital_name = recommended_hospital.iloc[0]["hospital"]
            hospital_info = next(
                (h for h in hospitals if h["name"] == hospital_name), None
            )
            st.write("Recommended Hospital assigned successfully!")
            if st.button("Another Recommendation"):
                st.session_state["recommendation_accepted"] = False
                st.session_state["selected_hospital_name"] = None
                st.cache_data.clear()
            folium.PolyLine(
                locations=[
                    (
                        float(selected_patient["Latitude"]),
                        float(selected_patient["Longitude"]),
                    ),
                    (hospital_info["latitude"], hospital_info["longitude"]),
                ],
                color="blue",
                weight=3,
                opacity=0.6,
            ).add_to(m)

    # Display the map
    st_folium(m, width="100%", height=500)
