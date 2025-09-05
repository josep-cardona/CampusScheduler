from datetime import datetime
from typing import List
from src.models.schedule import ScheduledLecture, LectureType

# Map lecture type string to enum
lecture_type_map = {
    "Teoria": LectureType.THEORY,
    "Pràctiques": LectureType.LAB,
    "Seminari": LectureType.SEMINAR
}

def parse_schedule_rows(rows: list) -> List[ScheduledLecture]:
    """Parses raw row elements from the scraper into a list of ScheduledLecture objects."""
    classes: List[ScheduledLecture] = []
    current_day_element = None

    for row in rows:
        row_classes = row.get_attribute("class")
        if not row_classes or ("fc-event" not in row_classes and "fc-list-day" not in row_classes):
            continue

        if "fc-list-day" in row_classes:
            current_day_element = row
            continue

        if "festiu" in row_classes or "assig" not in row_classes:
            continue

        class_time = row.query_selector(".fc-list-event-time").inner_text()
        details = row.query_selector(".fc-event-title").inner_text().split("\n")

        # Parse course id and name
        course_id_str, course_name = details[0].split(" - ", 1)
        
        # Parse group number and lecture type
        group_part, lecture_type_str = details[1].split(" - ", 1)
        group_num = int(group_part.replace("Grup ", ""))
        lecture_type = lecture_type_map.get(lecture_type_str, LectureType.THEORY)

        # Parse classroom
        classroom = details[2].replace("Aula ", "")

        # Parse start and end time
        start_str, end_str = class_time.split(" - ")
        else:
            raise ValueError("Lecture row encountered without a preceding day header (fc-list-day). Input data may be malformed.")
    return classes