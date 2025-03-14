from ortools.sat.python import cp_model
import firebase_admin
from firebase_admin import credentials, firestore

class TimetableScheduler:
    def __init__(self, teacher_total_limit=18):
        """
        Initializes the timetable scheduler.
        
        Args:
            teacher_total_limit (int): Global limit on total assignments per teacher.
        """
        # Initialize Firebase Admin if not already initialized.
        cred = credentials.Certificate("serviceAccountKey.json")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

        # Load candidates and sections from Firestore.
        # Expected structure:
        # /general_request/candidate/<year>/<section>/subjects/<subject_doc>
        self.candidates = {}     # { "1st year": [ (subject, required_count, teacher), ... ], ... }
        self.year_sections = {}  # { "1st year": ["A", "B"], ... }
        cand_ref = self.db.collection("general_request").document("candidate")
        for year_col in cand_ref.collections():
            year = year_col.id  # e.g., "1st year"
            self.year_sections[year] = []
            candidate_list = None  # We'll load candidates from the first section encountered.
            for section_doc in year_col.list_documents():
                sec = section_doc.id  # e.g., "A"
                self.year_sections[year].append(sec)
                # Get subjects from subcollection "subjects" under this section.
                subjects = []
                subj_ref = section_doc.collection("subjects")
                for subj_doc in subj_ref.stream():
                    data = subj_doc.to_dict()
                    # Expected fields: "subject", "required_count", "teacher" (optional)
                    subject_name = data.get("subject")
                    required_count = data.get("required_count")
                    teacher = data.get("teacher", None)
                    if subject_name is not None and required_count is not None:
                        subjects.append((subject_name, required_count, teacher))
                # Assume that all sections for a year share the same candidate list.
                if candidate_list is None and subjects:
                    candidate_list = subjects
            if candidate_list is None:
                raise ValueError(f"No candidate subjects found for year '{year}'.")
            self.candidates[year] = candidate_list

        self.days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
        self.periods = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"]
        self.teacher_total_limit = teacher_total_limit

        self.num_days = len(self.days)
        self.num_periods = len(self.periods)
        self.years_list = list(self.candidates.keys())

        # Identify the candidate index for "Free" in 3rd year.
        self.free_index_3rd = None
        if "3rd year" in self.candidates:
            for idx, (subject, req_count, teacher) in enumerate(self.candidates["3rd year"]):
                if subject.lower() == "free":
                    self.free_index_3rd = idx
                    break
            if self.free_index_3rd is None:
                raise ValueError("No 'Free' candidate found in 3rd year.")

    def solve(self):
        model = cp_model.CpModel()
        
        # Decision variables: X[(year, section, day, period)] holds the candidate index (int) for that cell.
        X = {}
        for year in self.years_list:
            for sec in self.year_sections[year]:
                for d in range(self.num_days):
                    for p in range(self.num_periods):
                        num_candidates = len(self.candidates[year])
                        X[(year, sec, d, p)] = model.NewIntVar(0, num_candidates - 1, f"{year}_{sec}_{d}_{p}")
        
        # Reified Boolean variables: assign_bool[(year, sec, d, p, idx)] is True if candidate idx is assigned.
        assign_bool = {}
        # Constraint 1: Each candidate subject appears exactly its required number of times overall (across sections).
        for year in self.years_list:
            for idx, (subject, required_count, teacher) in enumerate(self.candidates[year]):
                occurrence_vars = []
                for sec in self.year_sections[year]:
                    for d in range(self.num_days):
                        for p in range(self.num_periods):
                            # For 3rd year, force last two periods of Day 1 and Day 6 to be "Free".
                            if (year == "3rd year" and 
                                (d == 0 or d == self.num_days - 1) and 
                                (p in [self.num_periods - 2, self.num_periods - 1])):
                                if idx == self.free_index_3rd:
                                    bool_var = model.NewBoolVar(f"{year}_{sec}_{d}_{p}_{subject}_forced")
                                    model.Add(X[(year, sec, d, p)] == idx).OnlyEnforceIf(bool_var)
                                    model.Add(X[(year, sec, d, p)] != idx).OnlyEnforceIf(bool_var.Not())
                                    occurrence_vars.append(bool_var)
                                    assign_bool[(year, sec, d, p, idx)] = bool_var
                                continue  # Skip non-Free candidates for these forced cells.
                            else:
                                bool_var = model.NewBoolVar(f"{year}_{sec}_{d}_{p}_{subject}")
                                model.Add(X[(year, sec, d, p)] == idx).OnlyEnforceIf(bool_var)
                                model.Add(X[(year, sec, d, p)] != idx).OnlyEnforceIf(bool_var.Not())
                                occurrence_vars.append(bool_var)
                                assign_bool[(year, sec, d, p, idx)] = bool_var
                model.Add(sum(occurrence_vars) == required_count)
        
        # Constraint 2: Each subject appears at most twice per day (across sections).
        for year in self.years_list:
            for idx, (subject, required_count, teacher) in enumerate(self.candidates[year]):
                for d in range(self.num_days):
                    day_occurrence = []
                    for sec in self.year_sections[year]:
                        for p in range(self.num_periods):
                            # For 3rd year, consider forced "Free" cells.
                            if (year == "3rd year" and 
                                (d == 0 or d == self.num_days - 1) and 
                                (p in [self.num_periods - 2, self.num_periods - 1])):
                                if idx == self.free_index_3rd:
                                    day_occurrence.append(assign_bool[(year, sec, d, p, idx)])
                                continue
                            day_occurrence.append(assign_bool[(year, sec, d, p, idx)])
                    model.Add(sum(day_occurrence) <= 2)
        
        # Constraint 3: Prevent teacher double booking: each teacher (if not None) is assigned at most once in the same day/period.
        teacher_assignments = {}
        for year in self.years_list:
            for sec in self.year_sections[year]:
                for d in range(self.num_days):
                    for p in range(self.num_periods):
                        for idx, (subject, req_number, teacher) in enumerate(self.candidates[year]):
                            if teacher is None:
                                continue
                            key = (year, sec, d, p, idx)
                            if key not in assign_bool:
                                continue
                            teacher_assignments.setdefault(teacher, {}).setdefault((d, p), []).append(assign_bool[key])
        for teacher, time_slots in teacher_assignments.items():
            for time_slot, bool_vars in time_slots.items():
                model.Add(sum(bool_vars) <= 1)
        
        # Constraint 4: Prevent a teacher from being scheduled for three consecutive periods on the same day.
        for teacher, time_slots in teacher_assignments.items():
            for d in range(self.num_days):
                for p in range(self.num_periods - 2):
                    triple_vars = []
                    for pp in [p, p + 1, p + 2]:
                        if (d, pp) in time_slots:
                            triple_vars.extend(time_slots[(d, pp)])
                    if triple_vars:
                        model.Add(sum(triple_vars) <= 2)
        
        # Constraint 5: Teacher total assignments limit.
        for teacher, time_slots in teacher_assignments.items():
            all_assignments = []
            for (d, p), bool_vars in time_slots.items():
                all_assignments.extend(bool_vars)
            model.Add(sum(all_assignments) <= self.teacher_total_limit)
        
        # Solve the model.
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            output_data = {}
            for year in self.years_list:
                output_data[year] = {}
                for sec in self.year_sections[year]:
                    timetable = []
                    for d in range(self.num_days):
                        row = []
                        for p in range(self.num_periods):
                            cand_index = solver.Value(X[(year, sec, d, p)])
                            subject, req_number, teacher = self.candidates[year][cand_index]
                            teacher_str = teacher if teacher is not None else "No Teacher"
                            row.append(f"{subject} ({teacher_str})")
                        timetable.append(row)
                    output_data[year][sec] = timetable
            return output_data
        else:
            return None

# Example usage:
if __name__ == "__main__":
    scheduler = TimetableScheduler(teacher_total_limit=18)
    solution = scheduler.solve()
    if solution is not None:
        for year, sections in solution.items():
            for sec, timetable in sections.items():
                print(f"--- {year} Section {sec} ---")
                for row in timetable:
                    print(row)
    else:
        print("No feasible solution found.")
