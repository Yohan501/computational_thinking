"""Grade and Attendance Tracker.

Uses only the Python standard library (csv, math, os, datetime, fractions).
Run:  python tracker.py
Test: python -m unittest test_tracker -v
"""
import csv
import datetime
import math
import os
from fractions import Fraction

DEFAULT_THRESHOLD = 75.0   # minimum attendance percentage
MARKS_TARGET = 40.0        # minimum marks percentage considered "safe"
BAR_WIDTH = 20

ATTENDANCE_FILE = "attendance.csv"
MARKS_FILE = "marks.csv"
SETTINGS_FILE = "settings.txt"
REPORT_FILE = "report.txt"


# --------------------------------------------------------------------------
# Data structure
# --------------------------------------------------------------------------
def new_records():
    return {"subjects": {}, "threshold": DEFAULT_THRESHOLD}


def find_subject(records, name):
    """Case-insensitive lookup. Returns the stored subject name or None."""
    wanted = name.strip().lower()
    for key in records["subjects"]:
        if key.lower() == wanted:
            return key
    return None


def fmt(x):
    return f"{x:g}"


# --------------------------------------------------------------------------
# Calculations
# --------------------------------------------------------------------------
def marks_summary(subject):
    """Return (total obtained, total max, percentage)."""
    got = sum(a["obtained"] for a in subject["assessments"])
    top = sum(a["max"] for a in subject["assessments"])
    pct = got * 100 / top if top else 0.0
    return got, top, pct


def attendance_percentage(subject):
    total = subject["total_classes"]
    if total <= 0:
        return 0.0
    return subject["attended"] * 100 / total


def attendance_status(subject, threshold):
    if attendance_percentage(subject) >= threshold:
        return "Meets threshold"
    return "BELOW threshold"


def classes_needed(subject, threshold):
    """Consecutive classes to attend to reach the threshold (None if impossible)."""
    att, total = subject["attended"], subject["total_classes"]
    thr = Fraction(str(threshold))
    if att * 100 >= thr * total:
        return 0
    if thr >= 100:
        return None
    return math.ceil((thr * total - 100 * att) / (100 - thr))


def overall_average(records):
    pcts = [marks_summary(s)[2] for s in records["subjects"].values()
            if s["assessments"]]
    return sum(pcts) / len(pcts) if pcts else 0.0


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
def safe_to_miss(subject, threshold):
    """Classes that can still be missed while staying at/above the threshold."""
    att, total = subject["attended"], subject["total_classes"]
    thr = Fraction(str(threshold))
    if thr <= 0 or att * 100 < thr * total:
        return 0
    return max(0, math.floor(Fraction(att * 100) / thr) - total)


def marks_needed(subject, target_pct, additional_max):
    """Marks needed in future assessments worth `additional_max` to reach target_pct.

    Returns 0.0 if already met, None if impossible.
    """
    got, top, _ = marks_summary(subject)
    need = target_pct / 100 * (top + additional_max) - got
    if need <= 0:
        return 0.0
    if need > additional_max:
        return None
    return round(need, 2)


def risk_score(subject, threshold):
    """Sum of attendance gap and marks gap (0 means no risk)."""
    score = 0.0
    if subject["total_classes"] > 0:
        score += max(0.0, threshold - attendance_percentage(subject))
    _, top, pct = marks_summary(subject)
    if top > 0:
        score += max(0.0, MARKS_TARGET - pct)
    return score


def rank_by_risk(records):
    """[(name, score)] for subjects at risk, highest risk first."""
    thr = records["threshold"]
    ranked = [(n, risk_score(s, thr)) for n, s in records["subjects"].items()]
    ranked = [item for item in ranked if item[1] > 0]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def make_bar(pct, width=BAR_WIDTH):
    pct = max(0.0, min(100.0, pct))
    filled = int(round(pct / 100 * width))
    return "#" * filled + "." * (width - filled)


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------
def read_text(prompt):
    while True:
        value = input(prompt + ": ").strip()
        if value:
            return value
        print("Input cannot be empty.")


def read_number(prompt, lo=0, hi=None):
    while True:
        raw = input(prompt + ": ").strip()
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number.")
            continue
        if not math.isfinite(value):
            print("Please enter a finite number.")
            continue
        if value < lo:
            print(f"Value must be at least {fmt(lo)}.")
            continue
        if hi is not None and value > hi:
            print(f"Value must be at most {fmt(hi)}.")
            continue
        return value


def read_int(prompt, lo=0, hi=None):
    while True:
        raw = input(prompt + ": ").strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value < lo:
            print(f"Value must be at least {lo}.")
            continue
        if hi is not None and value > hi:
            print(f"Value must be at most {hi}.")
            continue
        return value


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------
def _read_csv(path, required):
    """Return a list of row dicts, or [] if the file is missing/unusable."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not set(required) <= set(reader.fieldnames or []):
                print(f"Warning: {os.path.basename(path)} has missing columns; ignored.")
                return []
            return list(reader)
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError, csv.Error) as err:
        print(f"Warning: could not read {os.path.basename(path)} ({err}).")
        return []


def load_records(data_dir="."):
    records = new_records()

    # settings
    try:
        with open(os.path.join(data_dir, SETTINGS_FILE), encoding="utf-8") as f:
            for line in f:
                key, _, value = line.partition("=")
                if key.strip() == "threshold":
                    try:
                        thr = float(value.strip())
                        if not (math.isfinite(thr) and 1 <= thr <= 100):
                            raise ValueError
                        records["threshold"] = thr
                    except ValueError:
                        print("Warning: invalid threshold in settings; using default.")
    except FileNotFoundError:
        pass
    except (OSError, UnicodeDecodeError) as err:
        print(f"Warning: could not read settings ({err}).")

    # attendance
    rows = _read_csv(os.path.join(data_dir, ATTENDANCE_FILE),
                     ("subject", "attended", "total_classes"))
    for n, row in enumerate(rows, start=2):
        try:
            name = (row["subject"] or "").strip()
            attended = int(row["attended"])
            total = int(row["total_classes"])
            if not name or attended < 0 or attended > total:
                raise ValueError
            if find_subject(records, name):
                raise ValueError
        except (ValueError, TypeError):
            print(f"Warning: skipped bad row {n} in {ATTENDANCE_FILE}.")
            continue
        records["subjects"][name] = {"assessments": [], "attended": attended,
                                     "total_classes": total}

    # marks
    rows = _read_csv(os.path.join(data_dir, MARKS_FILE),
                     ("subject", "assessment", "obtained", "max"))
    for n, row in enumerate(rows, start=2):
        try:
            key = find_subject(records, row["subject"] or "")
            aname = (row["assessment"] or "").strip()
            obtained = float(row["obtained"])
            top = float(row["max"])
            if (key is None or not aname or not math.isfinite(obtained)
                    or not math.isfinite(top) or top <= 0
                    or obtained < 0 or obtained > top):
                raise ValueError
        except (ValueError, TypeError):
            print(f"Warning: skipped bad row {n} in {MARKS_FILE}.")
            continue
        records["subjects"][key]["assessments"].append(
            {"name": aname, "obtained": obtained, "max": top})
    return records


def save_records(records, data_dir="."):
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, ATTENDANCE_FILE), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["subject", "attended", "total_classes"])
            for name, s in records["subjects"].items():
                w.writerow([name, s["attended"], s["total_classes"]])
        with open(os.path.join(data_dir, MARKS_FILE), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["subject", "assessment", "obtained", "max"])
            for name, s in records["subjects"].items():
                for a in s["assessments"]:
                    w.writerow([name, a["name"], float(a["obtained"]), float(a["max"])])
        with open(os.path.join(data_dir, SETTINGS_FILE), "w", encoding="utf-8") as f:
            f.write(f"threshold={float(records['threshold'])}\n")
        return True
    except OSError as err:
        print(f"Error: could not save data ({err}).")
        return False


def build_report(records):
    thr = records["threshold"]
    lines = ["GRADE AND ATTENDANCE REPORT",
             f"Generated: {datetime.date.today().isoformat()}",
             f"Attendance threshold: {fmt(thr)}%", "=" * 60]
    if not records["subjects"]:
        lines.append("No subjects recorded.")
    for name, s in records["subjects"].items():
        got, top, mpct = marks_summary(s)
        apct = attendance_percentage(s)
        lines += [
            f"{name}",
            f"  Marks:      {fmt(got)}/{fmt(top)} ({mpct:.1f}%)",
            f"  Attendance: {s['attended']}/{s['total_classes']} ({apct:.1f}%) "
            f"- {attendance_status(s, thr)}",
            f"  Safe to miss: {safe_to_miss(s, thr)} class(es)",
        ]
        need = classes_needed(s, thr)
        if need:
            lines.append(f"  Must attend next {need} class(es) in a row to reach {fmt(thr)}%")
        elif need is None:
            lines.append("  Threshold can no longer be reached by attending alone")
        lines.append("-" * 60)
    lines.append(f"Overall marks average: {overall_average(records):.1f}%")
    ranked = rank_by_risk(records)
    if ranked:
        lines.append("Subjects at risk (highest first):")
        lines += [f"  {i}. {n} (risk {sc:.1f})" for i, (n, sc) in enumerate(ranked, 1)]
    else:
        lines.append("No subjects at risk.")
    return "\n".join(lines) + "\n"


def generate_report(records, path=REPORT_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_report(records))
        return True
    except OSError as err:
        print(f"Error: could not write report ({err}).")
        return False


# --------------------------------------------------------------------------
# Menu operations
# --------------------------------------------------------------------------
def _read_assessment():
    name = read_text("  Assessment name")
    top = read_number("  Maximum marks", 1)
    got = read_number("  Marks obtained", 0, top)
    return {"name": name, "obtained": got, "max": top}


def _read_attendance(subject):
    total = read_int("Total classes held", 0)
    subject["total_classes"] = total
    subject["attended"] = read_int("Classes attended", 0, total)


def add_subject(records):
    name = read_text("Subject name")
    if find_subject(records, name):
        print("That subject already exists.")
        return
    subject = {"assessments": [], "attended": 0, "total_classes": 0}
    count = read_int("Number of assessments", 0, 50)
    for i in range(count):
        print(f"Assessment {i + 1}:")
        subject["assessments"].append(_read_assessment())
    _read_attendance(subject)
    records["subjects"][name] = subject
    print(f"Added {name}.")


def update_subject(records):
    key = find_subject(records, read_text("Subject name"))
    if key is None:
        print("Subject not found.")
        return
    s = records["subjects"][key]
    print("1) Edit marks of an assessment  2) Add assessment  3) Update attendance")
    choice = read_int("Choice", 1, 3)
    if choice == 1:
        if not s["assessments"]:
            print("No assessments to edit.")
            return
        for i, a in enumerate(s["assessments"], 1):
            print(f"  {i}. {a['name']}: {fmt(a['obtained'])}/{fmt(a['max'])}")
        a = s["assessments"][read_int("Assessment number", 1, len(s["assessments"])) - 1]
        a["obtained"] = read_number("New marks obtained", 0, a["max"])
    elif choice == 2:
        s["assessments"].append(_read_assessment())
    else:
        _read_attendance(s)
    print("Updated.")


def delete_subject(records):
    key = find_subject(records, read_text("Subject name"))
    if key is None:
        print("Subject not found.")
        return
    if read_text(f"Delete {key}? (y/n)").lower().startswith("y"):
        del records["subjects"][key]
        print("Deleted.")
    else:
        print("Cancelled.")


def view_subjects(records):
    if not records["subjects"]:
        print("No subjects recorded.")
        return
    for name, s in records["subjects"].items():
        got, top, pct = marks_summary(s)
        print(f"\n{name}: marks {fmt(got)}/{fmt(top)} ({pct:.1f}%), "
              f"attendance {s['attended']}/{s['total_classes']} "
              f"({attendance_percentage(s):.1f}%)")
        for a in s["assessments"]:
            print(f"    - {a['name']}: {fmt(a['obtained'])}/{fmt(a['max'])}")


def dashboard(records):
    thr = records["threshold"]
    if not records["subjects"]:
        print("No subjects recorded.")
        return
    for name, s in records["subjects"].items():
        apct, mpct = attendance_percentage(s), marks_summary(s)[2]
        print(f"{name}")
        print(f"  Attendance [{make_bar(apct)}] {apct:5.1f}%  {attendance_status(s, thr)}")
        print(f"  Marks      [{make_bar(mpct)}] {mpct:5.1f}%")
    print(f"\nOverall marks average: {overall_average(records):.1f}%")


def set_threshold(records):
    records["threshold"] = read_number("New attendance threshold (1-100)", 1, 100)
    print(f"Threshold set to {fmt(records['threshold'])}%.")


def marks_calculator(records):
    key = find_subject(records, read_text("Subject name"))
    if key is None:
        print("Subject not found.")
        return
    target = read_number("Target overall percentage", 0, 100)
    extra = read_number("Maximum marks still to come", 1)
    need = marks_needed(records["subjects"][key], target, extra)
    if need is None:
        print("Not possible: even full marks would not reach that target.")
    elif need == 0:
        print("Target already secured.")
    else:
        print(f"You need {fmt(need)} out of {fmt(extra)} in the remaining assessments.")


def safe_to_miss_report(records):
    thr = records["threshold"]
    if not records["subjects"]:
        print("No subjects recorded.")
        return
    for name, s in records["subjects"].items():
        need = classes_needed(s, thr)
        if need == 0:
            print(f"{name}: you can miss {safe_to_miss(s, thr)} more class(es).")
        elif need is None:
            print(f"{name}: threshold can no longer be reached.")
        else:
            print(f"{name}: below threshold - attend the next {need} class(es).")


def risk_report(records):
    ranked = rank_by_risk(records)
    if not ranked:
        print("No subjects at risk.")
        return
    for i, (name, score) in enumerate(ranked, 1):
        print(f"{i}. {name} (risk score {score:.1f})")


MENU = """
===== Grade & Attendance Tracker =====
 1) Add subject          7) Marks needed calculator
 2) Update subject       8) Safe-to-miss report
 3) Delete subject       9) Risk ranking
 4) View all subjects   10) Generate report file
 5) Dashboard           11) Save and exit
 6) Set threshold"""


def main(data_dir="."):
    records = load_records(data_dir)
    actions = {1: add_subject, 2: update_subject, 3: delete_subject,
               4: view_subjects, 5: dashboard, 6: set_threshold,
               7: marks_calculator, 8: safe_to_miss_report, 9: risk_report}
    changes_data = {1, 2, 3, 6}
    try:
        while True:
            print(MENU)
            choice = read_int("Choose an option (1-11)", 1, 11)
            if choice == 11:
                break
            if choice == 10:
                path = os.path.join(data_dir, REPORT_FILE)
                if generate_report(records, path):
                    print(f"Report written to {path}")
                continue
            actions[choice](records)
            if choice in changes_data:
                save_records(records, data_dir)
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
    if save_records(records, data_dir):
        print("Data saved. Goodbye!")


if __name__ == "__main__":
    main()
