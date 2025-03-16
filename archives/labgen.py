from ortools.sat.python import cp_model
import csv
import firebase_admin
from firebase_admin import credentials, firestore

class LabTimetableScheduler:
    def __init__(self, classes, labs, days, periods):
        self.classes = classes
        self.labs = labs
        self.days = days
        self.periods = periods
        self.model = cp_model.CpModel()
        self.timetable = {}

    def fetch_classes_from_firestore(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

        db = firestore.client()

        # Reference to Firestore document
        classes_ref = db.collection("timetableLAB_request").document("classes")
        classes_doc = classes_ref.get()

        if not classes_doc.exists:
            print("No class data found in Firestore.")
            return []

        # Extract data
        classes_data = classes_doc.to_dict()

        # Convert map to list format
        classes_list = [[data["year"], data["subject"], data["required_count"]] for data in classes_data.values()]

        return classes_list

    def build_model(self):
        """Builds the constraint model for timetable scheduling."""
        # Variables
        for day in self.days:
            for period in self.periods:
                for cls in self.classes:
                    self.timetable[(day, period, cls[1])] = self.model.NewBoolVar(f"{day}_{period}_{cls[1]}")

        # Constraints
        # 1. Each class must have the required number of periods
        for cls in self.classes:
            num_periods_assigned = sum(self.timetable[(day, period, cls[1])] for day in self.days for period in self.periods)
            self.model.Add(num_periods_assigned == cls[2])

        # 2. One subject should be placed only once per day
        for day in self.days:
            for cls in self.classes:
                num_periods_assigned = sum(self.timetable[(day, period, cls[1])] for period in self.periods)
                self.model.Add(num_periods_assigned <= 1)

        # 3. Each period can only have one class assigned
        for day in self.days:
            for period in self.periods:
                num_classes_assigned = sum(self.timetable[(day, period, cls[1])] for cls in self.classes)
                self.model.Add(num_classes_assigned <= 1)

    def solve(self):
        """Solves the model and returns the solution."""
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)
        if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
            solution = []
            for day in self.days:
                row = [day]
                for period in self.periods:
                    assigned = False
                    for cls in self.classes:
                        if solver.Value(self.timetable[(day, period, cls[1])]):
                            row.append(f"{cls[0]}_{cls[1]}")
                            assigned = True
                            break
                    if not assigned:
                        row.append("Empty")
                solution.append(row)
            return solution
        else:
            return None

    def save_solution_to_csv(self, filename):
        solution = self.solve()
        if solution:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Day/Period"] + [f"Period {p}" for p in self.periods])
                writer.writerows(solution)
            print(f"Timetable saved to {filename}")
        else:
            print("No solution found.")

if __name__ == "__main__":
    scheduler = LabTimetableScheduler([], [], [], []) 
    class_list = scheduler.fetch_classes_from_firestore()
    print(class_list)
    scheduler.build_model()
    scheduler.save_solution_to_csv("timetable.csv")