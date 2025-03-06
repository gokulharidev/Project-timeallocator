from general import TimetableProcessor

# Fetch these dynamically from Firebase
csv_file = "timetable.csv"
years_data = {
    "1st Year": ["1st Year_C++ Lab"],
    "2nd Year": ["2nd Year_.NET Lab", "2nd Year_Linux Lab"],
    "3rd Year": ["3rd Year_Web Lab", "3rd Year_Python Lab"]
}
candidates_data = {
    "1st Year": [("C++ Lab", 6, "Geetha")],
    "2nd Year": [(".NET Lab", 5, "Cladju")],
    "3rd Year": [("Python Lab", 5, "Janani"), ("Web Lab", 6, "Narmadha")]
}

processor = TimetableProcessor(csv_file, years_data, candidates_data)
processor.process_timetable()
