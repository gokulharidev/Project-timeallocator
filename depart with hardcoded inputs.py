import os
import pandas as pd
from ortools.sat.python import cp_model

# === CANDIDATES DEFINITION (subject, required number, teacher) ===
candidates = {
    "1st Year": [
        ("c++", 5, "geetha"),
        ("c++ Lab", 6, "geetha"),
        ("VE", 2, "suganthi"),
        ("Tamil", 6, None),
        ("English", 6, None),
        ("Maths", 5, None)
    ],
    "2nd Year": [
        (".NET Lab", 5, "cladju"),
        (".net", 4, "cladju"),
        ("linux Lab", 2, "janai"),
        ("Tamil", 6, None),
        ("English", 6, None),
        ("dos", 5, "vaisnavi"),
        ("elective", 2, "kaliraj")
    ],
    "3rd Year": [
        ("Python Lab", 5, "janani"),
        ("Python", 4, "kaliraj"),
        ("Web Lab", 6, "narmadha"),
        ("Web", 5, "narmadha"),
        ("iot1", 3, "geetha"),
        ("iot2", 3, "kaliraj"),
        ("Free", 4, None)  
    ]
}

# === LOAD THE YEAR-WISE TIMETABLES (File 2 outputs) ===
years_list = ["1st Year", "2nd Year", "3rd Year"]
input_dir = "Yearly_Timetables"
year_tables = {}
for year in years_list:
    file_path = os.path.join(input_dir, f"{year.replace(' ', '_')}.csv")
    year_tables[year] = pd.read_csv(file_path, index_col=0)

days = list(year_tables["1st Year"].index)
periods = list(year_tables["1st Year"].columns)
num_days = len(days)
num_periods = len(periods)

# Identify the candidate index for "Free" in 3rd Year.
free_index_3rd = None
for idx, (subject, required_count, teacher) in enumerate(candidates["3rd Year"]):
    if subject.lower() == "free":
        free_index_3rd = idx
        break
if free_index_3rd is None:
    raise ValueError("No 'Free' candidate found in 3rd Year.")

# === CP MODEL CREATION ===
model = cp_model.CpModel()

# Decision variables:
# X[(year, d, p)] is an integer variable representing the candidate index for that cell.
X = {}
for year in years_list:
    for d in range(num_days):
        for p in range(num_periods):
            X[(year, d, p)] = model.NewIntVar(0, len(candidates[year]) - 1, f"{year}_{d}_{p}")

# Dictionary to hold reified Boolean variables.
# assign_bool[(year, d, p, idx)] is True if candidate at index 'idx' is assigned in cell (d,p) for that year.
assign_bool = {}

# Constraint 1: Each candidate subject appears exactly its required number of times overall.
for year in years_list:
    for idx, (subject, required_count, teacher) in enumerate(candidates[year]):
        occurrence_vars = []
        for d in range(num_days):
            for p in range(num_periods):
                # For 3rd Year, force the last 2 periods of day 1 (index 0) and day 6 (last day) to be "Free"
                if (year == "3rd Year" and 
                    (d == 0 or d == num_days - 1) and 
                    (p in [num_periods - 2, num_periods - 1])):
                    # Only add a Boolean variable if this candidate is "Free"
                    if idx == free_index_3rd:
                        bool_var = model.NewBoolVar(f"{year}_{d}_{p}_{subject}_forced")
                        model.Add(X[(year, d, p)] == idx).OnlyEnforceIf(bool_var)
                        model.Add(X[(year, d, p)] != idx).OnlyEnforceIf(bool_var.Not())
                        occurrence_vars.append(bool_var)
                        assign_bool[(year, d, p, idx)] = bool_var
                    # Skip non-Free candidates in these forced cells.
                    continue
                else:
                    bool_var = model.NewBoolVar(f"{year}_{d}_{p}_{subject}")
                    model.Add(X[(year, d, p)] == idx).OnlyEnforceIf(bool_var)
                    model.Add(X[(year, d, p)] != idx).OnlyEnforceIf(bool_var.Not())
                    occurrence_vars.append(bool_var)
                    assign_bool[(year, d, p, idx)] = bool_var
        model.Add(sum(occurrence_vars) == required_count)

# Constraint 2: Each subject appears at most two times per day.
for year in years_list:
    for idx, (subject, required_count, teacher) in enumerate(candidates[year]):
        for d in range(num_days):
            day_occurrence = []
            for p in range(num_periods):
                if (year == "3rd Year" and (d == 0 or d == num_days - 1) and 
                    (p in [num_periods - 2, num_periods - 1])):
                    if idx == free_index_3rd:
                        day_occurrence.append(assign_bool[(year, d, p, idx)])
                    continue
                day_occurrence.append(assign_bool[(year, d, p, idx)])
            model.Add(sum(day_occurrence) <= 2)

# Constraint 3: Prevent teacher double booking.
# For every day and period across all years, each teacher (ignoring None) is assigned at most once.
teacher_assignments = {}
for year in years_list:
    for d in range(num_days):
        for p in range(num_periods):
            for idx, (subject, req_number, teacher) in enumerate(candidates[year]):
                if teacher is None:
                    continue
                if (year, d, p, idx) not in assign_bool:
                    continue
                teacher_assignments.setdefault(teacher, {}).setdefault((d, p), []).append(assign_bool[(year, d, p, idx)])

for teacher, time_slots in teacher_assignments.items():
    for time_slot, bool_vars in time_slots.items():
        model.Add(sum(bool_vars) <= 1)

# Constraint 4: Prevent a teacher from being assigned for three consecutive periods on the same day.
# For each teacher, on each day, for every three consecutive periods, the total assignments must be at most 2.
for teacher, time_slots in teacher_assignments.items():
    for d in range(num_days):
        for p in range(num_periods - 2):
            triple_vars = []
            # Collect Boolean variables for periods p, p+1, and p+2, if any.
            for pp in [p, p+1, p+2]:
                if (d, pp) in time_slots:
                    triple_vars.extend(time_slots[(d, pp)])
            if triple_vars:
                model.Add(sum(triple_vars) <= 2)
# Constraint 5: Ensure total assignments per teacher are <= 18.
for teacher, time_slots in teacher_assignments.items():
    all_assignments = []
    for (d, p), bool_vars in time_slots.items():
        all_assignments.extend(bool_vars)
    model.Add(sum(all_assignments) <= 18)


# === SOLVE THE MODEL ===
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    output_data = {}
    for year in years_list:
        timetable_final = []
        for d in range(num_days):
            row = []
            for p in range(num_periods):
                cand_index = solver.Value(X[(year, d, p)])
                subject, req_number, teacher = candidates[year][cand_index]
                teacher_str = teacher if teacher is not None else "No Teacher"
                row.append(f"{subject} ({teacher_str})")
            timetable_final.append(row)
        output_data[year] = timetable_final

    output_dir = "Final_Yearly_Timetables"
    os.makedirs(output_dir, exist_ok=True)
    for year in years_list:
        df = pd.DataFrame(output_data[year], columns=periods, index=days)
        df.to_csv(os.path.join(output_dir, f"{year.replace(' ', '_')}_final.csv"))
    print("Final yearly timetables created successfully!")
else:
    print("No solution found!")
