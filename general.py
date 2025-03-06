import pandas as pd
import os
import random
import logging

class TimetableProcessor:
    def __init__(self, csv_file, years, candidates):
        """
        Initializes the processor with required inputs.

        Args:
            csv_file (str): Path to the timetable CSV file.
            years (dict): Dictionary mapping year groups to their lab subjects.
            candidates (dict): Dictionary of subjects with required occurrences and teachers.
        """
        self.csv_file = csv_file
        self.years = years
        self.candidates = candidates
        self.year_data = {}
        self.days = []
        self.periods = []
        self.data = None
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    def load_csv(self):
        """Loads the timetable CSV file and initializes data structures."""
        if not os.path.exists(self.csv_file):
            logging.error(f"Error: '{self.csv_file}' not found.")
            return False
        
        try:
            self.data = pd.read_csv(self.csv_file, index_col=0)
            self.days, self.periods = list(self.data.index), list(self.data.columns)
            self.year_data = {year: [["Empty"] * len(self.periods) for _ in range(len(self.days))] for year in self.years.keys()}
            return True
        except Exception as e:
            logging.error(f"Error loading '{self.csv_file}': {e}")
            return False

    def populate_lab_sessions(self):
        """Assigns lab sessions from the timetable to the respective years."""
        for day_idx, day in enumerate(self.days):
            for period_idx, period in enumerate(self.periods):
                subject = self.data.loc[day, period]
                if subject != "Empty":
                    for year, subjects in self.years.items():
                        if subject in subjects:
                            lab_subject = subject.split("_")[1]  # Extract subject name
                            if self.year_data[year][day_idx][period_idx] == "Empty":
                                self.year_data[year][day_idx][period_idx] = lab_subject
                            else:
                                self.year_data[year][day_idx][period_idx] += ", " + lab_subject

    def ensure_subject_count(self):
        """Ensures each subject appears exactly as many times as specified in candidates."""
        for year, subject_list in self.candidates.items():
            for subject, required_count, _ in subject_list:
                current_count = sum(row.count(subject) for row in self.year_data[year])
                empty_slots = [(i, j) for i in range(len(self.days)) for j in range(len(self.periods)) if self.year_data[year][i][j] == "Empty"]
                subject_slots = [(i, j) for i in range(len(self.days)) for j in range(len(self.periods)) if self.year_data[year][i][j] == subject]
                
                if current_count < required_count:
                    missing = required_count - current_count
                    if len(empty_slots) < missing:
                        logging.warning(f"Not enough empty slots for {subject} in {year}. Assigning {len(empty_slots)} instead of {missing}.")
                        missing = len(empty_slots)
                    for i, j in random.sample(empty_slots, missing):
                        self.year_data[year][i][j] = subject

                elif current_count > required_count:
                    excess = current_count - required_count
                    for i, j in random.sample(subject_slots, excess):
                        self.year_data[year][i][j] = "Empty"

                logging.info(f"{subject} in {year} adjusted to {required_count} occurrences.")

    def save_timetables(self, output_dir="Yearly_Timetables"):
        """Saves each year's timetable as a separate CSV file."""
        os.makedirs(output_dir, exist_ok=True)
        for year, table in self.year_data.items():
            df = pd.DataFrame(table, columns=self.periods, index=self.days)
            file_path = os.path.join(output_dir, f"{year.replace(' ', '_')}.csv")
            df.to_csv(file_path)
        logging.info("CSV files created successfully!")

    def process_timetable(self):
        """Executes the full processing workflow."""
        if not self.load_csv():
            return
        self.populate_lab_sessions()
        self.ensure_subject_count()
        self.save_timetables()
