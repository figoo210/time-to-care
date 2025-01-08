# Time to Care

## Overview

TimeToCare is designed to optimize the process of identifying the best hospital for patients
based on wait times, location, and medical specialization. The system utilizes modern
database solutions, graph analysis, and a table-based mapping system to provide accurate
and reliable recommendations.

## Installation

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/figoo210/time-to-care.git
   ```

2. Navigate to the project directory:

   ```bash
   cd time-to-care
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file in the respective directories (frontend/backend).
   - Add required configuration values (API keys, database URLs, etc.).
   - Example:

      ```bash
      SQLITE_DB=
      MONGODB_URI=
      NEO4J_URI=
      NEO4J_USER=
      NEO4J_PASSWORD=
      ```

5. Run the application:
   - Data Mapping:

      ```bash
      # Add historical data to SQLite
      python mapping_historical_data.py

      # Add hospitals to Neo4J
      python mapping_hospitals.py

      # Add patients to MongoDB
      python mapping_patient_data.py

      # Add symptoms to Neo4J
      python mapping_symptoms.py

      # Add symptoms to SQLite
      mapping_symptoms_sqlite.py
      ```

   ```bash
   # Start the app
   streamlit run app.py
   ```

## Usage

- Access the application at `http://localhost:8501`.

## License

This project is licensed under the [MIT License](LICENSE).
