# Grade and Attendance Tracker
Course: 2026CSAE100 - Computational Thinking and Programming, Bennett University
Team: Aditya Punia (Leader), Ved Prabhakar, Hardik Upadhyay, Tarun Nanak Shai

A menu-driven Python program that records subject-wise marks and attendance, analyses them,
and ranks subjects by how urgently they need attention.

## Run
    python tracker.py

## Test
    python -m unittest test_tracker -v

## Features
- Add / view / update / delete subjects with several assessments each
- Marks %, overall average, attendance %, configurable attendance threshold (default 75%)
- Priority ranking (risk score = attendance shortfall + marks shortfall below 40%)
- Attendance planner: classes you can miss, or must attend to recover
- Marks target calculator: marks needed in the next assessment for a target %
- Text bar chart and automatic report.txt
- Input validation and safe loading of CSV/TXT files

## Files
- tracker.py - main program
- test_tracker.py - 41 automated tests
- ../2_Data_Files/ - example marks.csv, attendance.csv, settings.txt, report.txt
- ../3_Project_Report/ - project report
- ../5_Screenshots/ - program output images

Requires Python 3.8+ (standard library only). Data files are created in the folder you run it from.
