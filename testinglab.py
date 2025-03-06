
from lab_master import LabTimetableScheduler

    # and supply data dynamically (for example, after fetching it from Firebase).
classes = [
    ("1st Year", "C++", 5),
    ("2nd Year", "Linux", 2),
    ("2nd Year", ".NET", 5),
    ("3rd Year", "Python", 4),
    ("3rd Year", "Web", 6)
]
labs = ["Lab 1"] 
scheduler = LabTimetableScheduler(classes, labs)
solution = scheduler.solve()
if solution:
    for day in solution:
        print(f"{day}:")
        for period in solution[day]:
            print(f"  Period {period}: {solution[day][period]}")
else:
    print("No solution found.")
