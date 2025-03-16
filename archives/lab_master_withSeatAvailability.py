from ortools.sat.python import cp_model
import csv
import firebase_admin
from firebase_admin import credentials, firestore
import re

class LabTimetableScheduler:
    def __init__(self, classes=None):
        """
        Initializes the scheduler with input data.
        
        Args:
            classes (list of tuples): Each tuple is (year, subject, required_count).
                If not provided, classes are loaded from Firestore.
        """
        # Initialize Firebase if not already done.
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        
        # Load classes from Firestore if not given.
        if classes is None:
            self.classes = self.load_classes_from_firestore()
        else:
            self.classes = classes
        
        self.labs = []             # List of lab names.
        self.labs_data = {}        # Lab details (e.g. seat availability).
        self.days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
        self.periods = [1, 2, 3, 4, 5]
        self.slot_map = {}         # Map to store slot assignments
        
        self.model = cp_model.CpModel()
        self.timetable = {}        # Decision variables.
        self.solver = cp_model.CpSolver()
        self.solution = None       # Cache for the solved timetable.

    def load_classes_from_firestore(self):
        """
        Loads class subjects from Firestore.
        
        Expected Firestore structure:
        
            Collection: timetableLAB_request
                Document: classes
                    Subcollection: <year>    e.g., "1st year", "2nd year", etc.
                        Document: <section>   e.g., "A", "B", ...
                            Subcollection: subjects
                                Documents: e.g., "subject 1", "subject 2", ...
        
        Each subject document should include at least:
            - "subject": a string (e.g., "C++")
            - "required_count": an integer
        
        Returns:
            A list of tuples (year, subject, required_count)
        """
        classes_list = []
        classes_doc = self.db.collection("timetableLAB_request").document("classes")
        # Iterate over subcollections for each year.
        for year_col in classes_doc.collections():
            year_name = year_col.id  # e.g., "1st year" (adjust casing as needed)
            # For each year, iterate over its section documents.
            for section_doc in year_col.list_documents():
                # Optional: you can use section_doc.id if you want to differentiate sections.
                # Now, get the "subjects" subcollection.
                subjects_ref = section_doc.collection("subjects")
                for subj_doc in subjects_ref.stream():
                    subj_data = subj_doc.to_dict()
                    subject_name = subj_data.get("subject")
                    required_count = subj_data.get("required_count")
                    if subject_name is not None and required_count is not None:
                        # We ignore section details here and simply add the tuple.
                        classes_list.append((year_name, subject_name, required_count))
        return classes_list

    def load_slot_map_from_firestore(self):
        """
        Loads slot map data from Firestore.
        
        Expected format in Firestore:
        Collection: timetableLAB_request
            Document: slot
                Fields: 
                    slot1: "class : C++ Lab, sub_count:5, Year : 3"
                    slot2: "..."
                    slotN: "..."
        
        Returns:
            Dictionary mapping slot names to parsed class info
        """
        slot_map = {}
        # Corrected reference to 'slot' document instead of 'slot_map'
        slot_ref = self.db.collection("timetableLAB_request").document("slot")
        doc_snapshot = slot_ref.get()
        
        if not doc_snapshot.exists:
            print("No slot data found in Firestore at /timetableLAB_request/slot")
            return slot_map
        
        slot_data = doc_snapshot.to_dict()
        if not slot_data:
            print("Slot document exists but is empty.")
            return slot_map
        
        print(f"Raw slot data from Firestore: {slot_data}")
        
        # Parse each slot entry (slot1, slot2, etc.)
        for slot_name, slot_info_str in slot_data.items():
            if not slot_name.startswith("slot"):
                print(f"Warning: Unexpected field name in slot document: {slot_name}")
                continue
                
            # Parse the slot info string using regex
            class_match = re.search(r'class\s*:\s*([^,]+)', slot_info_str)
            count_match = re.search(r'sub_count\s*:\s*(\d+)', slot_info_str)
            year_match = re.search(r'Year\s*:\s*(\d+)', slot_info_str)
            
            if class_match and count_match and year_match:
                class_name = class_match.group(1).strip()
                sub_count = int(count_match.group(1))
                year = year_match.group(1)
                
                slot_map[slot_name] = {
                    'class': class_name,
                    'sub_count': sub_count,
                    'year': year
                }
            else:
                print(f"Warning: Could not parse slot info for {slot_name}: {slot_info_str}")
        
        return slot_map

    def export_slot_map_to_csv(self, filename="slot_map.csv"):
        """
        Exports the slot map data from Firestore to a CSV file.
        
        Args:
            filename (str): The name of the CSV file to create.
        """
        slot_map = self.load_slot_map_from_firestore()
        
        if not slot_map:
            print("No slot map data to export.")
            return
        
        # Define CSV fields
        fieldnames = ["slot", "class", "sub_count", "year"]
        
        # Write to CSV
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for slot_name, info in slot_map.items():
                writer.writerow({
                    "slot": slot_name,
                    "class": info.get("class", ""),
                    "sub_count": info.get("sub_count", ""),
                    "year": info.get("year", "")
                })
        
        print(f"Successfully exported {len(slot_map)} slot mappings to {filename}")
        return slot_map

    def export_classes_to_csv(self, filename="classes_data.csv"):
        """
        Exports the classes data from Firestore to a CSV file.
        
        Args:
            filename (str): The name of the CSV file to create.
        """
        classes_doc = self.db.collection("timetableLAB_request").document("classes")
        all_classes = []
        
        # Iterate over subcollections for each year
        for year_col in classes_doc.collections():
            year_name = year_col.id
            
            # For each year, iterate over its section documents
            for section_doc in year_col.list_documents():
                section_id = section_doc.id
                
                # Get the "subjects" subcollection
                subjects_ref = section_doc.collection("subjects")
                
                # Fetch all subjects in this section
                for subject_doc in subjects_ref.stream():
                    subject_data = subject_doc.to_dict()
                    subject_id = subject_doc.id
                    
                    # Extract relevant fields
                    subject_name = subject_data.get("subject", "Unknown")
                    required_count = subject_data.get("required_count", 0)
                    
                    # Add to our data structure with all details
                    all_classes.append({
                        "year": year_name,
                        "section": section_id,
                        "subject_id": subject_id,
                        "subject_name": subject_name,
                        "required_count": required_count
                    })
        
        if not all_classes:
            print(f"No data found in Firestore path: /timetableLAB_request/classes")
            return
        
        # Define the CSV field names (columns)
        fieldnames = ["year", "section", "subject_id", "subject_name", "required_count"]
        
        # Write the data to a CSV file
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write the header
            writer.writeheader()
            
            # Write all rows
            for class_data in all_classes:
                writer.writerow(class_data)
        
        print(f"Successfully exported {len(all_classes)} classes to {filename}")
        return all_classes

    def load_lab_data_from_firebase(self):
        """
        Loads lab data from Firestore.
        Expected structure in Firestore document 'lab_seatAvaliability' under the collection 
        'timetableLAB_request':
            {
                "Lab 1": { "seatAvailability": 30 },
                "Lab 2": { "seatAvailability": 25 }
            }
        """
        labs_ref = self.db.collection("timetableLAB_request").document("lab_seatAvaliability")
        doc_snapshot = labs_ref.get()
        
        if not doc_snapshot.exists:
            raise ValueError("No lab data found in Firestore under 'timetableLAB_request/lab_seatAvaliability'.")
        
        labs_data = doc_snapshot.to_dict()
        if labs_data is None:
            raise ValueError("Lab document is empty or has no data.")
            
        # Debug print to see what data is actually coming from Firestore
        print("Raw lab data from Firestore:", labs_data)
        
        # Check if the document structure matches what we expect
        valid_labs = {}
        for lab_name, lab_info in labs_data.items():
            if isinstance(lab_info, dict) and "seatAvailability" in lab_info:
                valid_labs[lab_name] = lab_info
            else:
                print(f"Warning: Lab '{lab_name}' has invalid structure: {lab_info}")
        
        if not valid_labs:
            raise ValueError("No valid lab data found. Expected structure: {'Lab name': {'seatAvailability': number}}")
        
        self.labs_data = valid_labs
        self.labs = list(valid_labs.keys())
        print("Processed labs:", self.labs)
        print("With data:", self.labs_data)

    def build_model(self):
        # Create decision variables: one BoolVar for each (day, period, lab, subject)
        for day in self.days:
            for period in self.periods:
                for lab in self.labs:
                    for cls in self.classes:
                        subject = cls[1]
                        var_name = f"{day}_{period}_{lab}_{subject}"
                        self.timetable[(day, period, lab, subject)] = self.model.NewBoolVar(var_name)

        # Constraint 1: Each class must appear exactly its required number of times.
        for (year, subject, required_count) in self.classes:
            self.model.Add(
                sum(
                    self.timetable[(day, period, lab, subject)]
                    for day in self.days
                    for period in self.periods
                    for lab in self.labs
                ) == required_count
            )

        # Constraint 2: Each subject is placed at most once per day (across all labs and periods).
        for day in self.days:
            for (year, subject, _) in self.classes:
                self.model.Add(
                    sum(
                        self.timetable[(day, period, lab, subject)]
                        for period in self.periods
                        for lab in self.labs
                    ) <= 1
                )

        # Constraint 3: Each period in each lab can have at most one class assigned.
        for day in self.days:
            for period in self.periods:
                for lab in self.labs:
                    self.model.Add(
                        sum(
                            self.timetable[(day, period, lab, cls[1])]
                            for cls in self.classes
                        ) <= 1
                    )

        # Constraint 4: Seat availability.
        # If a class requires more seats than a lab has, force that assignment to 0.
        for (year, subject, required_count) in self.classes:
            for lab in self.labs:
                lab_info = self.labs_data.get(lab, {})
                lab_seats = lab_info.get("seatAvailability", 0)
                if required_count > lab_seats:
                    for day in self.days:
                        for period in self.periods:
                            self.model.Add(self.timetable[(day, period, lab, subject)] == 0)

    def solve(self):
        # Use cached solution if available.
        if self.solution is not None:
            return self.solution
        
        self.load_lab_data_from_firebase()
        self.build_model()
        status = self.solver.Solve(self.model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution = {}
            for day in self.days:
                solution[day] = {}
                for period in self.periods:
                    solution[day][period] = {}
                    for lab in self.labs:
                        assignment = "Empty"
                        for cls in self.classes:
                            year, subject, _ = cls
                            if self.solver.Value(self.timetable[(day, period, lab, subject)]):
                                assignment = f"{year}_{subject}"
                                break
                        solution[day][period][lab] = assignment
            self.solution = solution
            return solution
        else:
            self.solution = None
            return None

    def save_solution_to_csv(self, filename="timetable.csv"):
        solution = self.solve()
        if solution is None:
            print("No solution found.")
            return

        header = ["Day/Period"]
        for period in self.periods:
            for lab in self.labs:
                header.append(f"{lab} P{period}")

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            for day in self.days:
                row = [day]
                for period in self.periods:
                    for lab in self.labs:
                        row.append(solution[day][period][lab])
                writer.writerow(row)

        print(f"Timetable saved to {filename}")

if __name__ == "__main__":
    # If no classes list is provided, they are loaded from Firestore.
    scheduler = LabTimetableScheduler()
    
    # Export the classes data from Firestore to CSV
    scheduler.export_classes_to_csv("class_data.csv")
    
    # Export the slot map data from Firestore to CSV
    scheduler.export_slot_map_to_csv("slot_map.csv")
    
    # Still run the original timetable scheduling functionality
    scheduler.save_solution_to_csv()