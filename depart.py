from ortools.sat.python import cp_model

class TimetableScheduler:
    def __init__(self, candidates, year_sections, teacher_total_limit=18):
        """
        Initializes the timetable scheduler.
        
        Args:
            candidates (dict): A dictionary where keys are year names (e.g., "1st Year") and values are
                lists of tuples (subject, required_count, teacher). For example:
                {
                    "1st Year": [("c++", 5, "geetha"), ...],
                    "2nd Year": [(".NET Lab", 5, "cladju"), ...],
                    "3rd Year": [("Python Lab", 5, "janani"), ..., ("Free", 4, None)]
                }
            year_sections (dict): A dictionary mapping each year to a list of section identifiers. For example:
                { "1st Year": ["A", "B"], "2nd Year": ["A", "B", "C"], "3rd Year": ["A"] }
            days (list): A list of day names. For example: ["Day 1", "Day 2", ..., "Day 6"]
            periods (list): A list of period names. For example: ["Period 1", "Period 2", ..., "Period 5"]
            teacher_total_limit (int): (Optional) Global limit on total assignments per teacher.
        """
        self.candidates = candidates
        self.year_sections = year_sections
        self.days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
        self.periods = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5"]
        self.teacher_total_limit = teacher_total_limit
        
        self.num_days = len(self. days)
        self.num_periods = len(self.periods)
        self.years_list = list(candidates.keys())
        
        # Identify the candidate index for "Free" in 3rd Year.
        self.free_index_3rd = None
        if "3rd Year" in self.candidates:
            for idx, (subject, required_count, teacher) in enumerate(self.candidates["3rd Year"]):
                if subject.lower() == "free":
                    self.free_index_3rd = idx
                    break
            if self.free_index_3rd is None:
                raise ValueError("No 'Free' candidate found in 3rd Year.")

    def solve(self):
        model = cp_model.CpModel()
        
        # Decision variables: X[(year, section, day, period)] holds the candidate index for that cell.
        X = {}
        for year in self.years_list:
            for sec in self.year_sections[year]:
                for d in range(self.num_days):
                    for p in range(self.num_periods):
                        X[(year, sec, d, p)] = model.NewIntVar(
                            0, len(self.candidates[year]) - 1,
                            f"{year}_{sec}_{d}_{p}"
                        )
        
        # Dictionary to hold reified Boolean variables.
        # assign_bool[(year, sec, d, p, idx)] is True if candidate at index idx is assigned to that cell.
        assign_bool = {}
        
        # Constraint 1: Each candidate subject appears exactly its required number of times overall (across sections).
        for year in self.years_list:
            for idx, (subject, required_count, teacher) in enumerate(self.candidates[year]):
                occurrence_vars = []
                for sec in self.year_sections[year]:
                    for d in range(self.num_days):
                        for p in range(self.num_periods):
                            # For 3rd Year, force the last two periods of day 1 and day 6 to be "Free".
                            if (year == "3rd Year" and 
                                (d == 0 or d == self.num_days - 1) and 
                                (p in [self.num_periods - 2, self.num_periods - 1])):
                                if idx == self.free_index_3rd:
                                    bool_var = model.NewBoolVar(f"{year}_{sec}_{d}_{p}_{subject}_forced")
                                    model.Add(X[(year, sec, d, p)] == idx).OnlyEnforceIf(bool_var)
                                    model.Add(X[(year, sec, d, p)] != idx).OnlyEnforceIf(bool_var.Not())
                                    occurrence_vars.append(bool_var)
                                    assign_bool[(year, sec, d, p, idx)] = bool_var
                                # Skip non-Free candidates for these forced cells.
                                continue
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
                            if (year == "3rd Year" and 
                                (d == 0 or d == self.num_days - 1) and 
                                (p in [self.num_periods - 2, self.num_periods - 1])):
                                if idx == self.free_index_3rd:
                                    day_occurrence.append(assign_bool[(year, sec, d, p, idx)])
                                continue
                            day_occurrence.append(assign_bool[(year, sec, d, p, idx)])
                    model.Add(sum(day_occurrence) <= 2)
        
        # Constraint 3: Prevent teacher double booking.
        # For every day and period across all years and sections, each teacher (ignoring None) is assigned at most once.
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
        # For each teacher, on each day, any three consecutive periods must have at most 2 assignments.
        for teacher, time_slots in teacher_assignments.items():
            for d in range(self.num_days):
                for p in range(self.num_periods - 2):
                    triple_vars = []
                    # Collect assignments for periods p, p+1, and p+2 (across all sections).
                    for pp in [p, p + 1, p + 2]:
                        if (d, pp) in time_slots:
                            triple_vars.extend(time_slots[(d, pp)])
                    if triple_vars:
                        model.Add(sum(triple_vars) <= 2)
        
        # Constraint 5: Ensure that a teacher's total number of assignments is <= teacher_total_limit.
        for teacher, time_slots in teacher_assignments.items():
            all_assignments = []
            for (d, p), bool_vars in time_slots.items():
                all_assignments.extend(bool_vars)
            model.Add(sum(all_assignments) <= self.teacher_total_limit)
        
        # Solve the model.
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Prepare the output data as a nested dictionary:
            # { year: { section: timetable } } where timetable is a list of rows (days)
            output_data = {}
            for year in self.years_list:
                output_data[year] = {}
                for sec in self.year_sections[year]:
                    timetable_final = []
                    for d in range(self.num_days):
                        row = []
                        for p in range(self.num_periods):
                            cand_index = solver.Value(X[(year, sec, d, p)])
                            subject, req_number, teacher = self.candidates[year][cand_index]
                            teacher_str = teacher if teacher is not None else "No Teacher"
                            row.append(f"{subject} ({teacher_str})")
                        timetable_final.append(row)
                    output_data[year][sec] = timetable_final
            return output_data
        else:
            return None

