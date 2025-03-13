from depart import TimetableScheduler
# Example usage (for testing or integration):
    # Define sample input data.
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
year_sections = {
    "1st Year": ["A", "B"],
    "2nd Year": ["A", "B"],
    "3rd Year": ["A"]
}
scheduler =TimetableScheduler(candidates, year_sections,)
solution = scheduler.solve()

if solution:
    for year, sections in solution.items():
        for sec, timetable in sections.items():
            print(f"--- {year} Section {sec} ---")
            for row in timetable:
                print(row)
            print()
else:
    print("No solution found!")