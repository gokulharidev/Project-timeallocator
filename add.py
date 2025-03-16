import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Candidate data
candidates = {
    "1st Year": [("C++ Lab", 6, "Geetha"), ("Tamil", 6, None), ("English", 6, None), ("Maths", 5, None)],
    "2nd Year": [(".NET Lab", 5, "Cladju"), ("Tamil", 6, None), ("English", 6, None)],
    "3rd Year": [("Python Lab", 5, "Janani"), ("Web Lab", 6, "Narmadha")]
}

def add_candidates_to_firestore():
    for year, subjects in candidates.items():
        year_doc_ref = db.collection("general_request").document(year)
        subject_data = {}

        for subject, count, staff in subjects:
            subject_data[subject] = {
                "count": count,
                "staff_id": staff  # Firestore supports None as null
            }
        
        # Upload to Firestore
        year_doc_ref.set(subject_data)
        print(f"✅ Data added for {year}")

# Run
if __name__ == "__main__":
    add_candidates_to_firestore()
