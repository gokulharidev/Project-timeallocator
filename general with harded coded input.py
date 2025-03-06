import pandas as pd
import os
import random
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Check if CSV exists before proceeding
csv_file = 'timetable.csv'
if not os.path.exists(csv_file):
    logging.error(f"Error: '{csv_file}' not found.")
    exit(1)

# Load the CSV file
try:
    data = pd.read_csv(csv_file, index_col=0)
except Exception as e:
    logging.error(f"Error loading '{csv_file}': {e}")
    exit(1)

# Define year groups and associated lab subjects
years = {
    "1st Year": ["1st Year_C++ Lab"],
    "2nd Year": ["2nd Year_.NET Lab", "2nd Year_Linux Lab"],
    "3rd Year": ["3rd Year_Web Lab", "3rd Year_Python Lab"]
}

# Define extra subject lists
extra_subjects = {
    "1st Year": ["Tamil", "English", "Maths"],
    "2nd Year": ["Tamil", "English", "dos"]
}

# Define candidate subjects with required number and teacher
candidates = {
    "1st Year": [("C++ Lab", 6, "Geetha"), ("Tamil", 6, None), ("English", 6, None), ("Maths", 5, None)],
    "2nd Year": [(".NET Lab", 5, "Cladju"), ("Tamil", 6, None), ("English", 6, None)],
    "3rd Year": [("Python Lab", 5, "Janani"), ("Web Lab", 6, "Narmadha")]
}

# Get the days and periods from the CSV
days, periods = list(data.index), list(data.columns)

# Initialize year data
year_data = {year: [["Empty"] * len(periods) for _ in range(len(days))] for year in years.keys()}

def populate_lab_sessions():
    """Assigns lab sessions from the timetable to the respective years."""
    for day_idx, day in enumerate(days):
        for period_idx, period in enumerate(periods):
            subject = data.loc[day, period]
            if subject != "Empty":
                for year, subjects in years.items():
                    if subject in subjects:
                        lab_subject = subject.split("_")[1]  # Extract subject name
                        if year_data[year][day_idx][period_idx] == "Empty":
                            year_data[year][day_idx][period_idx] = lab_subject
                        else:
                            year_data[year][day_idx][period_idx] += ", " + lab_subject

def ensure_subject_count():
    """Ensures each subject appears the exact number of times as mentioned in the candidates list."""
    for year, subject_list in candidates.items():
        for subject, required_count, _ in subject_list:
            current_count = sum(row.count(subject) for row in year_data[year])

            if current_count < required_count:
                missing = required_count - current_count
                empty_slots = [(i, j) for i in range(len(days)) for j in range(len(periods)) if year_data[year][i][j] == "Empty"]

                if len(empty_slots) < missing:
                    logging.warning(f"Not enough empty slots for {subject} in {year}. Assigning {len(empty_slots)} instead of {missing}.")
                    missing = len(empty_slots)

                for i, j in random.sample(empty_slots, missing):
                    year_data[year][i][j] = subject
                    current_count += 1

            elif current_count > required_count:
                excess = current_count - required_count
                subject_slots = [(i, j) for i in range(len(days)) for j in range(len(periods)) if year_data[year][i][j] == subject]

                for i, j in random.sample(subject_slots, excess):
                    year_data[year][i][j] = "Empty"
                    current_count -= 1

            logging.info(f"{subject} in {year} adjusted to {required_count} occurrences.")

def save_timetables():
    """Saves each year's timetable as a separate CSV file."""
    output_dir = "Yearly_Timetables"
    os.makedirs(output_dir, exist_ok=True)
    for year, table in year_data.items():
        df = pd.DataFrame(table, columns=periods, index=days)
        file_path = os.path.join(output_dir, f"{year.replace(' ', '_')}.csv")
        df.to_csv(file_path)
    logging.info("CSV files created successfully!")

# Run functions in sequence
populate_lab_sessions()
ensure_subject_count()
save_timetables()
