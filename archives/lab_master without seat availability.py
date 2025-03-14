from ortools.sat.python import cp_model
import csv

class LabTimetableScheduler:
    def __init__(self, classes, labs):
        """
        Initializes the scheduler with input data.
        
        Args:
            classes (list of tuples): Each tuple is (year, subject, required_count).
                For example: [("1st Year", "C++", 5), ("2nd Year", ".NET", 5), ...]
            labs (list): A list of lab names (e.g., ["Lab 1", "Lab 2"]).
            days (list): A list of days (e.g., ["Day 1", "Day 2", ..., "Day 6"]).
            periods (list): A list of periods (e.g., [1, 2, 3, 4, 5]).
        """
        self.classes = classes
        self.labs = labs
        self.days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
        self.periods = [1, 2, 3, 4, 5]
        
        self.model = cp_model.CpModel()
        self.timetable = {}  # decision variables will be stored here
        self.solver = cp_model.CpSolver()

    def build_model(self):
        # Create decision variables.
        # For every combination (day, period, lab, subject), create a Boolean variable.
        for day in self.days:
            for period in self.periods:
                for lab in self.labs:
                    for cls in self.classes:
                        subject = cls[1]
                        var_name = f"{day}_{period}_{lab}_{subject}"
                        self.timetable[(day, period, lab, subject)] = self.model.NewBoolVar(var_name)

        # Constraint 1: Each class must appear exactly its required number of times overall.
        for cls in self.classes:
            subject = cls[1]
            required_count = cls[2]
            self.model.Add(
                sum(
                    self.timetable[(day, period, lab, subject)]
                    for day in self.days
                    for period in self.periods
                    for lab in self.labs
                ) == required_count
            )

        # Constraint 2: Each subject is placed at most once per day (summing over all labs and periods).
        for day in self.days:
            for cls in self.classes:
                subject = cls[1]
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

    def solve(self):
        self.build_model()
        status = self.solver.Solve(self.model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Construct solution as a nested dictionary:
            # { day: { period: { lab: assignment } } }
            solution = {}
            for day in self.days:
                solution[day] = {}
                for period in self.periods:
                    solution[day][period] = {}
                    for lab in self.labs:
                        assignment = "Empty"
                        for cls in self.classes:
                            subject = cls[1]
                            if self.solver.Value(self.timetable[(day, period, lab, subject)]):
                                # Format the output as "Year_Subject"
                                assignment = f"{cls[0]}_{subject}"
                                break
                        solution[day][period][lab] = assignment
            return solution
        else:
            return None

    def save_solution_to_csv(self, filename="timetable.csv"):
        solution = self.solve()
        if solution is None:
            print("No solution found.")
            return

        # Create header: first column is "Day/Period", then one column per lab-period combination.
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

