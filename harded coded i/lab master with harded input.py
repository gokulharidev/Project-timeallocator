from ortools.sat.python import cp_model
import csv

# Data
classes = [
    ("1st Year", "C++", 5),
    ("2nd Year", "Linux", 2),
    ("2nd Year", ".NET", 5),
    ("3rd Year", "Python", 4),
    ("3rd Year", "Web", 6)
]

labs = ["Lab 1", "Lab 2"]

days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
periods = [1, 2, 3, 4, 5]

# Model
model = cp_model.CpModel()

# Variables
timetable = {}
for day in days:
    for period in periods:
        for cls in classes:
            timetable[(day, period, cls[1])] = model.NewBoolVar(f"{day}_{period}_{cls[1]}")

# Constraints
# 1. Each class must have the required number of periods
for cls in classes:
    num_periods_assigned = sum(timetable[(day, period, cls[1])] for day in days for period in periods)
    model.Add(num_periods_assigned == cls[2])

# 2. One subject should be placed only once at one day
for day in days:
    for cls in classes:
        num_periods_assigned = sum(timetable[(day, period, cls[1])] for period in periods)
        model.Add(num_periods_assigned <= 1)

# 3. Each period can only have one class assigned
for day in days:
    for period in periods:
        num_classes_assigned = sum(timetable[(day, period, cls[1])] for cls in classes)
        model.Add(num_classes_assigned <= 1)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

# Print solution
if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    with open('timetable.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Day/Period"] + [f"Period {p}" for p in periods])
        for day in days:
            row = [day]
            
            for period in periods:
                assigned = False
                for cls in classes:
                    if solver.Value(timetable[(day, period, cls[1])]):
                        row.append(f"{cls[0]}_{cls[1]}")
                        assigned = True
                        break
                if not assigned:
                    row.append("Empty")
            writer.writerow(row)
    print("Timetable saved to timetable.csv")
else:
    print("No solution found.")