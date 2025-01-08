import streamlit as st
from app_helper import *
from config import set_page_config


def main():
    set_page_config()

    data = load_data()

    # Title
    st.title("Time To Care: Hospital Navigation System")

    # Sidebar Actions
    st.sidebar.title("Actions")

    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()  # Clear the cache data

    success = manage_patient_form_internal(data["symptoms"])
    if success:
        st.cache_data.clear()
    simulate_hospitals_realtime_data()

    # Sidebar Filters
    specializations = list(set(h["specialization"] for h in data["hospitals"]))
    filters = sidebar_filters(data["hospitals"], data["symptoms"], specializations)

    # Calculate KPIs based on filters
    kpis = calculate_kpis(
        hospitals=data["hospitals"],
        patients=data["patients"],
        wait_times=data["wait_times_last_week"],
        filter_hospitals=filters["selected_hospitals"],
        filter_symptoms=filters["selected_symptoms"],
        filter_specializations=filters["selected_specializations"],
    )
    kpi_names = [
        "Total Hospitals",
        "Patients in the Queue",
        "Average Wait Time (Minutes)",
        "Unassigned Patients",
    ]
    display_kpi_metrics(kpis, kpi_names)

    # Display tables
    combined_hospital_patient_counts(filters)

    display_hospitals_wait_times(
        data["hospitals"], data["wait_times_last_week"], filters
    )

    display_patients_on_waiting_list(data["patients"], data["symptoms"], filters)

    # Recommended Hospitals
    manage_hospital_recommendation(
        data["patients"], data["hospitals"], data["symptoms"]
    )


if __name__ == "__main__":
    main()
