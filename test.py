import firebase_admin
from firebase_admin import credentials, firestore
import pprint

# ---------- Firebase Initialization ----------
# Replace 'serviceAccountKey.json' with your actual Firebase service account key file.
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------- Define Years and Sections ----------
years = ["1st Year", "2nd Year", "3rd Year"]
sections = ["A"]  # You can add more sections if needed

# ---------- Fetch Raw Candidate Data from Firestore ----------
# We'll store the raw Firestore data for each year (using only section "A")
raw_candidates = {}
for year in years:
    for section in sections:
        # Construct the Firestore document path: /depart_request/candidate/<year>/<section>
        doc_ref = db.collection("depart_request").document("candidate").collection(year).document(section)
        doc = doc_ref.get()
        if doc.exists:
            # Save the raw dictionary for this year.
            raw_candidates[year] = doc.to_dict()
        else:
            print(f"No candidate data found for {year} section {section}")

# ---------- Function to Convert Raw Data ----------
def convert_candidate_data(raw_data):
    """
    Converts a raw candidate dictionary into a list of tuples sorted by the numeric suffix of keys.
    Each tuple is of the form: (name, credits, teacher)
    For example, given:
    {
        'subject_5': {'credits': 6, 'teacher': None, 'name': 'English'},
        'subject_4': {'credits': 6, 'teacher': None, 'name': 'Tamil'},
        'subject_3': {'credits': 2, 'teacher': 'suganthi', 'name': 'VE'},
        'subject_6': {'credits': 5, 'teacher': None, 'name': 'Maths'},
        'subject_2': {'credits': 6, 'teacher': 'geetha', 'name': 'c++ Lab'},
        'subject_1': {'credits': 5, 'teacher': 'geetha', 'name': 'c++'}
    }
    it produces:
    [('c++', 5, 'geetha'),
     ('c++ Lab', 6, 'geetha'),
     ('VE', 2, 'suganthi'),
     ('Tamil', 6, None),
     ('English', 6, None),
     ('Maths', 5, None)]
    """
    # Sort items by the numeric suffix of the key, e.g. 'subject_1', 'subject_2', ...
    sorted_items = sorted(raw_data.items(), key=lambda x: int(x[0].split('_')[-1]))
    # Build and return the list of tuples
    return [
        (info.get("name"), info.get("credits"), info.get("teacher"))
        for key, info in sorted_items
    ]

# ---------- Build Final Candidates Structure ----------
candidates = {}
for year in years:
    if year in raw_candidates:
        candidates[year] = convert_candidate_data(raw_candidates[year])
    else:
        candidates[year] = []  # If no data, store an empty list

# ---------- Print the Final Structure ----------
pprint.pprint(candidates)
