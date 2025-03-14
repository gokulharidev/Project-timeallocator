from lab_master_withSeatAvailability import LabTimetableScheduler
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

cls_ref = db.collection("timetableLAB_request").document("classes")
doc_snapshot = cls_ref.get()

# doc_snapshot.to_dict() must be a dictionary. 
# Suppose it's shaped like: {"classes": [("1st Year", "C++", 5), ("2nd Year", ".NET", 5), ...]}
classes_dict = doc_snapshot.to_dict()
print("Document Data:", classes_dict)

# If the document has a key 'classes' that is a list of tuples, do something like:
classes_list = classes_dict.get("classes", [])
if not classes_list:
    print("No classes found in the Firestore document!")
    exit(1)

# 1) Build & Solve
laballoc = LabTimetableScheduler(classes_list)
laballoc.build_model()
solution = laballoc.solve()

# 2) Optionally, save to CSV
laballoc.save_solution_to_csv("timetable.csv")
print("Timetable saved to timetable.csv")

# 3) Push solution to Firestore
if solution is None:
    print("No solution found; nothing to push to Firestore.")
else:
    # For example, store it in the same collection "timetableLAB_request" but in a doc "final_solution"
    db.collection("2025").document("labsolutionBCA").set({"solution": solution})
    print("Solution pushed to Firestore under 'timetableLAB_request/final_solution'.")
