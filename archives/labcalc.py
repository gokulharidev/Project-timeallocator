from lab_master_withSeatAvailability import LabTimetableScheduler
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")  
firebase_admin.initialize_app(cred)
db=firestore.client()

cls_ref = db.collection("timetableLAB_request").document("classes")
docs = cls_ref.get()
docs = tuple(docs.to_dict().values())
print(type(docs))


if docs:
    print("Document Data:", docs.to_dict())
else:
    print("No such document!")

laballoc=LabTimetableScheduler(docs)
laballoc.build_model()
laballoc.solve()
laballoc.save_solution_to_csv("timetable.csv")
print("Timetable saved to timetable.csv")
