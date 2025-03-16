import firebase_admin
from firebase_admin import credentials, firestore
import csv
from ortools.sat.python import cp_model

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Fetch classes from Firestore
def fetch_classes_from_firestore():
    classes_ref = db.collection("timetableLAB_request").document("classes")
    classes_doc = classes_ref.get()
    
    if not classes_doc.exists:
        print("No class data found in Firestore.")
        return []

    classes_data = classes_doc.to_dict()
    classes_list = [[data["year"], data["subject"], data["required_count"]] for data in classes_data.values()]
    
    return classes_list

# Timetable Model
days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
periods = [1, 2, 3, 4, 5]
model = cp_model.CpModel()

# Variables
classes = fetch_classes_from_firestore()
if not classes:
    print("No classes found. Exiting.")
    exit()

timetable = {}
for day in days:
    for period in periods:
        for cls in classes:
            timetable[(day, period, cls[1])] = model.NewBoolVar(f"{day}_{period}_{cls[1]}")

# Constraints
for cls in classes:
    num_periods_assigned = sum(timetable[(day, period, cls[1])] for day in days for period in periods)
    model.Add(num_periods_assigned == cls[2])

for day in days:
    for cls in classes:
        num_periods_assigned = sum(timetable[(day, period, cls[1])] for period in periods)
        model.Add(num_periods_assigned <= 1)

for day in days:
    for period in periods:
        num_classes_assigned = sum(timetable[(day, period, cls[1])] for cls in classes)
        model.Add(num_classes_assigned <= 1)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

# Function to push timetable to Firestore
def push_timetable_to_firestore(timetable_solution):
    timetable_ref = db.collection("2025").document("labsolutionBCA")
    
    for day, periods in timetable_solution.items():
        try:
            day_ref = timetable_ref.collection(day).document("schedule")
            day_ref.set(periods)
            print(f"✅ Successfully stored {day} in Firestore: {periods}")
        except Exception as e:
            print(f"❌ Error storing {day}: {e}")

# Store solution if feasible
if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    timetable_solution = {}
    
    for day in days:
        day_schedule = {}
        for period in periods:
            assigned = "Empty"
            for cls in classes:
                if solver.Value(timetable[(day, period, cls[1])]):
                    assigned = f"{cls[0]}_{cls[1]}"
                    break
            day_schedule[f"Period {period}"] = assigned
        timetable_solution[day] = day_schedule

    # Push to Firestore
    push_timetable_to_firestore(timetable_solution)
    print("✅ Timetable successfully stored in Firestore.")
else:
    print("❌ No solution found.")
