import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firestore with service account key
cred = credentials.Certificate("serviceAccountKey.json")  # Update with actual file path
firebase_admin.initialize_app(cred)

db = firestore.client()

# Define years and sections
years = ["1st Year", "2nd Year", "3rd Year"]
sections = ["A"]  # Add more sections as needed

# Initialize dictionary to store fetched data
fetched_data = {}

# Fetch data for all years and sections
for year in years:
    fetched_data[year] = {}
    for section in sections:
        path = f"depart_request/candidate/{year}/{section}"
        section_doc_ref = db.document(path)
        section_doc = section_doc_ref.get()

        if section_doc.exists:
            fetched_data[year][section] = section_doc.to_dict()
        else:
            fetched_data[year][section] = "No Data"

# Display fetched data
for year, sections_data in fetched_data.items():
    print(f"\n=== {year} ===")
    for section, subjects in sections_data.items():
        print(f"\n  --- Section {section} ---")
        if subjects == "No Data":
            print("    No Data Available")
        else:
            for key, subject_data in subjects.items():
                print(f"    {key}:")
                if isinstance(subject_data, dict):  # Check if value is a dictionary
                    for sub_key, sub_value in subject_data.items():
                        print(f"      {sub_key}: {sub_value}")
                else:
                    print(f"      Value: {subject_data}")
