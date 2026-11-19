"""
Grade and Attendance Tracker
Course: 2026CSAE100 - Computational Thinking and Programming
Bennett University | Team: Aditya Punia, Ved Prabhakar, Hardik Upadhyay, Tarun Nanak Shai

A menu-driven program to record subject-wise marks and attendance, analyse them,
and tell the student which subjects need attention first.

Data is stored in plain files (CSV / TXT):
    marks.csv       subject, assessment, obtained, max
    attendance.csv  subject, attended, total_classes
    settings.txt    threshold=<percentage>
"""

import csv
import os

PASS_MARK = 40.0          # marks % below this is flagged
DEFAULT_THRESHOLD = 75.0  # default minimum attendance %
BAR_WIDTH = 20


# ============================================================ INPUT VALIDATION
def read_text(prompt):
    """Read a non-empty string."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  Error: this field cannot be empty.")


def read_number(prompt, minimum=0.0, maximum=None, allow_equal_min=True):
    """Read a number, re-asking until it is valid."""
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("  Error: please enter a valid number.")
            continue
        if value < minimum or (value == minimum and not allow_equal_min):
            word = "at least" if allow_equal_min else "greater than"
            print(f"  Error: value must be {word} {minimum:g}.")
            continue
        if maximum is not None and value > maximum:
            print(f"  Error: value cannot exceed {maximum:g}.")
            continue
        return value


def read_int(prompt, minimum=0, maximum=None):
    """Read a whole number within limits."""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  Error: please enter a whole number.")
            continue
        if value < minimum:
            print(f"  Error: value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"  Error: value cannot exceed {maximum}.")
            continue
        return value


# ============================================================== CALCULATIONS
def marks_summary(subject):
    """Return (total_obtained, total_max, percentage)."""
    obtained = sum(a["obtained"] for a in subject["assessments"])
    maximum = sum(a["max"] for a in subject["assessments"])
    percentage = (obtained / maximum * 100) if maximum > 0 else 0.0
    return obtained, maximum, percentage


def attendance_percentage(subject):
    """Attendance % = attended / total * 100 (0 if no classes held)."""
    total = subject["total_classes"]
    return (subject["attended"] / total * 100) if total > 0 else 0.0


def attendance_status(subject, threshold):
    if attendance_percentage(subject) >= threshold:
        return "Meets threshold"
    return "BELOW threshold"


def overall_average(records):
    """Mean of the per-subject marks percentages (0 if no subjects)."""
    if not records["subjects"]:
        return 0.0
    percents = [marks_summary(s)[2] for s in records["subjects"].values()]
    return sum(percents) / len(percents)


def classes_needed(subject, threshold):
    """Consecutive classes to attend to reach the threshold (None = impossible)."""
    attended, total = subject["attended"], subject["total_classes"]
    if total == 0 or attended / total * 100 >= threshold:
        return 0
    if threshold >= 100:
        return None
    needed = 0
    while (attended + needed) / (total + needed) * 100 < threshold:
        needed += 1
    return needed


def safe_to_miss(subject, threshold):
    """How many future classes can be missed while staying at/above the threshold."""
    attended, total = subject["attended"], subject["total_classes"]
    if total == 0 or attended / total * 100 < threshold:
        return 0
    missed = 0
    while missed < 500 and attended / (total + missed + 1) * 100 >= threshold:
        missed += 1
    return missed


def marks_needed(subject, target, next_max):
    """Marks needed in one more assessment (out of next_max) to reach target %.
    Returns 0 if already achieved, None if not achievable."""
    obtained, maximum, _ = marks_summary(subject)
    required = target / 100 * (maximum + next_max) - obtained
    if required <= 0:
        return 0.0
    if required > next_max:
        return None
    return round(required + 1e-9, 2)


def risk_score(subject, threshold):
    """Higher score = needs attention sooner.
    score = attendance shortfall (points below threshold)
          + marks shortfall (points below the pass mark)."""
    att_gap = max(0.0, threshold - attendance_percentage(subject))
    marks_gap = max(0.0, PASS_MARK - marks_summary(subject)[2])
    return att_gap + marks_gap


def rank_by_risk(records):
    """List of (subject, score) with score > 0, highest risk first."""
    threshold = records["threshold"]
    scored = [(name, risk_score(s, threshold)) for name, s in records["subjects"].items()]
    scored = [item for item in scored if item[1] > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def make_bar(percentage):
    """Text bar for 0-100 %."""
    filled = int(round(min(max(percentage, 0), 100) / 100 * BAR_WIDTH))
    return "#" * filled + "." * (BAR_WIDTH - filled)


# ============================================================ FILE HANDLING
def new_records():
    return {"threshold": DEFAULT_THRESHOLD, "subjects": {}}


def file_paths(folder="."):
    return (os.path.join(folder, "marks.csv"),
            os.path.join(folder, "attendance.csv"),
            os.path.join(folder, "settings.txt"))


def load_records(folder="."):
    """Load records from the data files. Missing files -> empty records.
    Bad rows are skipped with a warning instead of crashing."""
    marks_path, att_path, set_path = file_paths(folder)
    records = new_records()

    try:  # settings
        if os.path.exists(set_path):
            with open(set_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("threshold="):
                        value = float(line.split("=", 1)[1])
                        if 0 <= value <= 100:
                            records["threshold"] = value
    except (OSError, ValueError):
        print("Warning: could not read settings.txt. Using default threshold.")

    try:  # attendance (also defines which subjects exist)
        if os.path.exists(att_path):
            with open(att_path, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        attended = int(row["attended"])
                        total = int(row["total_classes"])
                        name = row["subject"].strip()
                        if not name or attended < 0 or attended > total:
                            raise ValueError
                        records["subjects"][name] = {
                            "assessments": [], "attended": attended, "total_classes": total}
                    except (ValueError, KeyError, TypeError, AttributeError):
                        print(f"Warning: skipped an invalid row in attendance.csv: {row}")
    except (OSError, csv.Error) as err:
        print(f"Warning: could not read attendance.csv ({err}).")

    try:  # marks
        if os.path.exists(marks_path):
            with open(marks_path, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        name = row["subject"].strip()
                        got, top = float(row["obtained"]), float(row["max"])
                        if name not in records["subjects"] or top <= 0 or got < 0 or got > top:
                            raise ValueError
                        records["subjects"][name]["assessments"].append(
                            {"name": row["assessment"].strip(), "obtained": got, "max": top})
                    except (ValueError, KeyError, TypeError, AttributeError):
                        print(f"Warning: skipped an invalid row in marks.csv: {row}")
    except (OSError, csv.Error) as err:
        print(f"Warning: could not read marks.csv ({err}).")

    return records


def save_records(records, folder="."):
    """Write all data files; return True on success."""
    marks_path, att_path, set_path = file_paths(folder)
    try:
        with open(att_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["subject", "attended", "total_classes"])
            for name, s in records["subjects"].items():
                writer.writerow([name, s["attended"], s["total_classes"]])
        with open(marks_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["subject", "assessment", "obtained", "max"])
            for name, s in records["subjects"].items():
                for a in s["assessments"]:
                    writer.writerow([name, a["name"], a["obtained"], a["max"]])
        with open(set_path, "w", encoding="utf-8") as f:
            f.write(f"threshold={records['threshold']}\n")
        return True
    except OSError as err:
        print(f"Error: could not save records ({err}).")
        return False


# ================================================================== DISPLAY
def find_subject(records, name):
    """Case-insensitive lookup; returns the stored key or None."""
    for key in records["subjects"]:
        if key.lower() == name.lower():
            return key
    return None


def print_subject(name, subject, threshold):
    obtained, maximum, pct = marks_summary(subject)
    print(f"\n  Subject: {name}")
    if subject["assessments"]:
        for a in subject["assessments"]:
            print(f"    - {a['name']}: {a['obtained']:g}/{a['max']:g}")
    else:
        print("    (no assessments entered)")
    print(f"    Marks     : {obtained:g}/{maximum:g}  ({pct:.2f}%)")
    print(f"    Attendance: {subject['attended']}/{subject['total_classes']}  "
          f"({attendance_percentage(subject):.2f}%)  -> {attendance_status(subject, threshold)}")


def view_all(records):
    if not records["subjects"]:
        print("\nNo subjects recorded yet.")
        return
    for name, subject in records["subjects"].items():
        print_subject(name, subject, records["threshold"])


def show_summary(records):
    subjects, threshold = records["subjects"], records["threshold"]
    if not subjects:
        print("\nNo subjects recorded yet.")
        return
    print(f"\n{'Subject':<18}{'Marks %':>9}{'Attend %':>10}  Status")
    print("-" * 60)
    for name, s in subjects.items():
        print(f"{name[:17]:<18}{marks_summary(s)[2]:>8.2f}%"
              f"{attendance_percentage(s):>9.2f}%  {attendance_status(s, threshold)}")
    print("-" * 60)
    print(f"Overall average marks: {overall_average(records):.2f}%   "
          f"(attendance threshold: {threshold:g}%)")

    ranking = rank_by_risk(records)
    if not ranking:
        print("\nAll subjects are on track.")
        return
    print("\nPriority ranking (needs attention first):")
    for position, (name, score) in enumerate(ranking, start=1):
        s = subjects[name]
        reasons = []
        if attendance_percentage(s) < threshold:
            need = classes_needed(s, threshold)
            reasons.append("attendance low (cannot reach threshold)" if need is None
                           else f"attendance low (attend next {need} classes)")
        if marks_summary(s)[2] < PASS_MARK:
            reasons.append(f"marks below {PASS_MARK:g}%")
        print(f"  {position}. {name}  [risk {score:.1f}]  - " + "; ".join(reasons))


def show_planner(records):
    subjects, threshold = records["subjects"], records["threshold"]
    if not subjects:
        print("\nNo subjects recorded yet.")
        return
    print(f"\nAttendance planner (threshold {threshold:g}%)")
    for name, s in subjects.items():
        if attendance_percentage(s) >= threshold:
            print(f"  {name}: on track - you can miss up to {safe_to_miss(s, threshold)} more class(es).")
        else:
            need = classes_needed(s, threshold)
            msg = "cannot reach threshold" if need is None else f"attend the next {need} class(es) in a row"
            print(f"  {name}: below threshold - {msg}.")


def show_chart(records):
    if not records["subjects"]:
        print("\nNo subjects recorded yet.")
        return
    print("\nMarks % and Attendance % (each # = 5%)")
    for name, s in records["subjects"].items():
        print(f"  {name[:14]:<14} Marks  |{make_bar(marks_summary(s)[2])}| {marks_summary(s)[2]:5.1f}%")
        print(f"  {'':<14} Attend |{make_bar(attendance_percentage(s))}| {attendance_percentage(s):5.1f}%")


def marks_target_tool(records):
    key = find_subject(records, read_text("Subject name: "))
    if not key:
        print("  Subject not found.")
        return
    s = records["subjects"][key]
    pct = marks_summary(s)[2]
    print(f"  Current marks in {key}: {pct:.2f}%")
    target = read_number("  Target overall percentage (0-100): ", 0, 100)
    top = read_number("  Maximum marks of the next assessment: ", 0, None, allow_equal_min=False)
    need = marks_needed(s, target, top)
    if need is None:
        print(f"  Not achievable with one assessment of {top:g} marks.")
    elif need == 0:
        print("  Target already achieved - any score keeps you at or above it.")
    else:
        print(f"  You need at least {need:g} out of {top:g} to reach {target:g}%.")


def generate_report(records, path="report.txt"):
    """Write a plain-text performance report; return True on success."""
    subjects, threshold = records["subjects"], records["threshold"]
    lines = ["GRADE AND ATTENDANCE REPORT", "=" * 60,
             f"Subjects: {len(subjects)}    Attendance threshold: {threshold:g}%",
             f"Overall average marks: {overall_average(records):.2f}%", ""]
    lines.append(f"{'Subject':<18}{'Marks %':>9}{'Attend %':>10}  Status")
    lines.append("-" * 60)
    for name, s in subjects.items():
        lines.append(f"{name[:17]:<18}{marks_summary(s)[2]:>8.2f}%"
                     f"{attendance_percentage(s):>9.2f}%  {attendance_status(s, threshold)}")
    lines.append("")
    ranking = rank_by_risk(records)
    if ranking:
        lines.append("Priority ranking:")
        for i, (name, score) in enumerate(ranking, 1):
            lines.append(f"  {i}. {name} (risk {score:.1f})")
    else:
        lines.append("All subjects are on track.")
    if subjects:
        best = max(subjects, key=lambda n: marks_summary(subjects[n])[2])
        worst = min(subjects, key=lambda n: marks_summary(subjects[n])[2])
        lines += ["", f"Strongest subject: {best} ({marks_summary(subjects[best])[2]:.2f}%)",
                  f"Weakest subject  : {worst} ({marks_summary(subjects[worst])[2]:.2f}%)"]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except OSError as err:
        print(f"Error: could not write report ({err}).")
        return False


# =============================================================== OPERATIONS
def read_one_assessment():
    label = read_text("  Assessment name: ")
    max_marks = read_number("    Maximum marks: ", 0, None, allow_equal_min=False)
    got = read_number("    Marks obtained: ", 0, max_marks)
    return {"name": label, "obtained": got, "max": max_marks}


def read_assessments():
    count = read_int("  Number of assessments (0 to skip): ", 0, 50)
    return [read_one_assessment() for _ in range(count)]


def read_attendance():
    total = read_int("  Total classes held: ", 0)
    attended = read_int("  Classes attended: ", 0, total)
    return attended, total


def add_subject(records):
    name = read_text("Subject name: ")
    if find_subject(records, name):
        print("  A subject with this name already exists. Use Update instead.")
        return
    assessments = read_assessments()
    attended, total = read_attendance()
    records["subjects"][name] = {"assessments": assessments,
                                 "attended": attended, "total_classes": total}
    print(f"  Subject '{name}' added.")
    print_subject(name, records["subjects"][name], records["threshold"])


def update_subject(records):
    key = find_subject(records, read_text("Subject name to update: "))
    if not key:
        print("  Subject not found.")
        return
    subject = records["subjects"][key]
    print("  1. Replace all assessments\n  2. Add one assessment\n  3. Update attendance")
    choice = read_int("  Choice: ", 1, 3)
    if choice == 1:
        subject["assessments"] = read_assessments()
    elif choice == 2:
        subject["assessments"].append(read_one_assessment())
    else:
        subject["attended"], subject["total_classes"] = read_attendance()
    print("  Record updated.")
    print_subject(key, subject, records["threshold"])


def delete_subject(records):
    key = find_subject(records, read_text("Subject name to delete: "))
    if not key:
        print("  Subject not found.")
        return
    if input(f"  Delete '{key}'? (y/n): ").strip().lower() == "y":
        del records["subjects"][key]
        print("  Subject deleted.")
    else:
        print("  Cancelled.")


def set_threshold(records):
    print(f"  Current threshold: {records['threshold']:g}%")
    records["threshold"] = read_number("  New threshold (0-100): ", 0, 100)
    print("  Threshold updated.")


# ===================================================================== MENU
MENU = """
======= Grade and Attendance Tracker =======
  1. Add subject
  2. View all subjects
  3. Update subject
  4. Delete subject
  5. Summary and priority ranking
  6. Attendance planner
  7. Marks target calculator
  8. Bar chart
  9. Generate report file (report.txt)
 10. Set attendance threshold
 11. Exit
"""


def main(folder="."):
    records = load_records(folder)
    print("Welcome! Records loaded." if records["subjects"] else "Welcome! Starting new records.")
    actions = {
        "1": add_subject, "2": view_all, "3": update_subject, "4": delete_subject,
        "5": show_summary, "6": show_planner, "7": marks_target_tool,
        "8": show_chart, "10": set_threshold,
        "9": lambda r: print("  Report saved to report.txt." if generate_report(
            r, os.path.join(folder, "report.txt")) else "  Report not saved."),
    }
    while True:
        print(MENU)
        choice = input("Enter choice (1-11): ").strip()
        if choice == "11":
            save_records(records, folder)
            print("Records saved. Goodbye!")
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid choice. Please enter a number from 1 to 11.")
            continue
        action(records)
        save_records(records, folder)


if __name__ == "__main__":
    main()
