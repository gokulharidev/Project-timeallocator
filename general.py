import firebase_admin
from firebase_admin import credentials, firestore
import json
import re
import csv

# ========== STEP 1: FIREBASE SETUP & FETCH SCHEDULE ==========

# Initialize Firebase Admin SDK (Replace 'serviceAccountKey.json' with your key file)
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Firestore database reference
db = firestore.client()

def fetch_schedule_for_all_days():
    """
    Fetches and sorts schedule data for Day 1 to Day 6 from Firestore.
    Returns a dict:
    {
        "Day 1": { "Period 1": "...", "Period 2": "...", ... },
        "Day 2": { ... },
        ...
        "Day 6": { ... }
    }
    """
    schedule_data = {}
    for i in range(1, 7):  # Day 1 to Day 6
        schedule_ref = (
            db.collection("2025")
            .document("labsolutionBCA")
            .collection(f"Day {i}")
            .document("schedule")
        )
        try:
            doc = schedule_ref.get()
            if doc.exists:
                data = doc.to_dict()  # Convert document to dict
                # Sort periods by the numeric value in the key (Period 1, Period 2, etc.)
                sorted_data = {
                    k: v for k, v in sorted(data.items(), key=lambda x: int(x[0].split()[-1]))
                }
                schedule_data[f"Day {i}"] = sorted_data
            else:
                schedule_data[f"Day {i}"] = {}
        except Exception as e:
            schedule_data[f"Day {i}"] = {}
            print(f"Error fetching data for Day {i}: {e}")
    return schedule_data

def remove_year_prefix(subject):
    """
    Removes '1st Year', '2nd Year', or '3rd Year' prefix from the subject string.
    e.g. '1st Year_C++ Lab' -> 'C++ Lab'
    """
    return re.sub(r"^(1st Year|2nd Year|3rd Year)[_\s]+", "", subject)

def separate_by_year(schedule_data):
    """
    Splits the fetched schedule into three dictionaries:
      - first_year
      - second_year
      - third_year
    Preserves day/period structure, removing 'Year' prefixes from subjects.
    Periods not matching a year are set to "Empty" in that year's schedule.
    """
    first_year = {}
    second_year = {}
    third_year = {}
    
    for day, periods in schedule_data.items():
        # Initialize each day in each year
        first_year[day] = {}
        second_year[day] = {}
        third_year[day] = {}
        
        if isinstance(periods, dict):
            for period, subject in periods.items():
                # 1st Year
                if "1st Year" in subject:
                    first_year[day][period] = remove_year_prefix(subject)
                else:
                    first_year[day][period] = "Empty"
                
                # 2nd Year
                if "2nd Year" in subject:
                    second_year[day][period] = remove_year_prefix(subject)
                else:
                    second_year[day][period] = "Empty"
                
                # 3rd Year
                if "3rd Year" in subject:
                    third_year[day][period] = remove_year_prefix(subject)
                else:
                    third_year[day][period] = "Empty"
        else:
            # If there's no valid dict for the day
            first_year[day] = periods
            second_year[day] = periods
            third_year[day] = periods

    return first_year, second_year, third_year

# ========== STEP 2: FETCH EXTRA SUBJECTS FROM FIRESTORE ==========
def fetch_extra_subjects():
    """
    Fetch the extra_subject document from /general_request/extra_subject.
    Expected structure:
    {
      "1st Year": {"English": 6, "Tamil": 6, "maths": 5},
      "2nd Year": {"DOS": 5, "English": 6, "Tamil": 6},
      "3rd Year": {"Data Mining": 5, "Python": 6}
    }
    Returns a dict with these mappings.
    """
    try:
        extra_ref = db.collection("general_request").document("extra_subject")
        doc = extra_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print("No extra_subject data found.")
            return {}
    except Exception as e:
        print(f"Error fetching extra subjects: {e}")
        return {}

# ========== STEP 3: FILL EMPTY SLOTS WITH EXTRA SUBJECTS ==========
def fill_extra_subjects(year_schedule, extra_subjects):
    """
    For a given year's schedule (day -> period -> subject),
    and a dictionary of extra_subjects = { "English": 6, "Tamil": 6, ... },
    fill the "Empty" slots with these extra subjects, ensuring:
      - Each extra subject can only appear once per day.
      - We only place it as many times as requested.
      - We fill from Day 1 -> Day 6 in order, placing at most one occurrence per day.
    Returns the updated year_schedule.
    """
    # Example: extra_subjects = {"English": 6, "Tamil": 6, "maths": 5}
    # We try to place 'English' 6 times across the week, 1 time max per day in an empty slot.

    for subject, required_count in extra_subjects.items():
        count_remaining = required_count
        
        # Try placing this subject day-by-day until we've placed it required_count times.
        for day in year_schedule:
            if count_remaining <= 0:
                break  # Done placing this subject
            
            # Check if this day already has 'subject' (to ensure one occurrence max per day)
            already_present = any(
                year_schedule[day][period] == subject for period in year_schedule[day]
            )
            if already_present:
                continue  # Skip this day if subject already placed
            
            # Place subject in the first available empty slot
            placed_in_day = False
            for period in year_schedule[day]:
                if year_schedule[day][period] == "Empty" and not placed_in_day:
                    year_schedule[day][period] = subject
                    count_remaining -= 1
                    placed_in_day = True
                    break  # Only one per day
    return year_schedule

# ========== STEP 4: UPLOAD FINAL SCHEDULES TO FIRESTORE ==========

def convert_schedule_dict_to_list(schedule_dict):
    """
    Convert a dictionary of the form:
        {
          "Day 1": {"Period 1": "Empty", "Period 2": "Math", ...},
          "Day 2": {...},
          ...
        }
    into a list of day objects with ordered period objects:
        [
          {
            "dayName": "Day 1",
            "periods": [
              {"periodName": "Period 1", "subject": "Empty"},
              {"periodName": "Period 2", "subject": "Math"},
              ...
            ]
          },
          ...
        ]
    """
    day_list = []
    for day_key in sorted(schedule_dict.keys(), key=lambda d: int(d.split()[-1])):
        period_map = schedule_dict[day_key]
        period_list = []
        for period_key in sorted(period_map.keys(), key=lambda p: int(p.split()[-1])):
            subject = period_map[period_key]
            # Include teacher info if available
            # If the slot is a dict, it may have a "teacher" key.
            if isinstance(subject, dict):
                period_list.append({
                    "periodName": period_key,
                    "subject": subject.get("subject", "Empty"),
                    "teacher": subject.get("teacher", "")
                })
            else:
                period_list.append({
                    "periodName": period_key,
                    "subject": subject,
                    "teacher": ""  # default blank if not provided
                })
        day_list.append({
            "dayName": day_key,
            "periods": period_list
        })
    return day_list

def upload_final_schedules(first_year_schedule, second_year_schedule, third_year_schedule):
    # Convert each schedule dict to a list (to preserve order in Firestore)
    first_year_list = convert_schedule_dict_to_list(first_year_schedule)
    second_year_list = convert_schedule_dict_to_list(second_year_schedule)
    third_year_list = convert_schedule_dict_to_list(third_year_schedule)

    # Prepare the data to store
    doc_data = {
        "1st Year": first_year_list,
        "2nd Year": second_year_list,
        "3rd Year": third_year_list
    }

    # Reference the document at /2025/generaltimetable
    doc_ref = db.collection("2025").document("generaltimetable")
    doc_ref.set(doc_data)
    print("Uploaded final schedules to /2025/generaltimetable successfully.")
    return doc_data

# ========== STEP 5: STORE OUTPUT TO CSV FILE ==========
import csv
import os
def save_schedule_to_csv(schedule, filename):
    """
    Saves a given schedule dictionary to a CSV file.
    CSV format:
    Day/Period,Period 1,Period 2,Period 3,Period 4,Period 5
    """
    # Assume each day has the same period keys
    sample_day = next(iter(schedule.values()))
    header = ["Day/Period"] + list(sample_day.keys())
    
    # Create output folder if it doesn't exist
    output_folder = "final_schedules"
    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, filename)
    
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for day, periods in schedule.items():
            row = [day] + [periods.get(period, "Empty") for period in header[1:]]
            writer.writerow(row)
    print(f"Saved {filepath} successfully.")


def main():
    # 1) Fetch the weekly schedule from Firestore
    schedule_data = fetch_schedule_for_all_days()
    
    # 2) Separate into 1st, 2nd, 3rd year schedules
    first_year_schedule, second_year_schedule, third_year_schedule = separate_by_year(schedule_data)
    
    # 3) Fetch extra subjects from /general_request/extra_subject
    extra_data = fetch_extra_subjects()
    
    # 4) Fill empty slots for each year
    if "1st Year" in extra_data:
        first_year_schedule = fill_extra_subjects(first_year_schedule, extra_data["1st Year"])
    if "2nd Year" in extra_data:
        second_year_schedule = fill_extra_subjects(second_year_schedule, extra_data["2nd Year"])
    if "3rd Year" in extra_data:
        third_year_schedule = fill_extra_subjects(third_year_schedule, extra_data["3rd Year"])
    
    # 5) Save schedules to CSV files
    save_schedule_to_csv(first_year_schedule, "1st_Year.csv")
    save_schedule_to_csv(second_year_schedule, "2nd_Year.csv")
    save_schedule_to_csv(third_year_schedule, "3rd_Year.csv")
    
    # 6) Upload final schedules to Firestore
    upload_final_schedules(first_year_schedule, second_year_schedule, third_year_schedule)

# Run main
if __name__ == "__main__":
    main()
