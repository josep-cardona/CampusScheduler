from datetime import date, datetime
from typing import List

from campsched.models.schedule import LectureType, ScheduledLecture

# Map lecture type string to enum
lecture_type_map = {
    "Teoria": LectureType.THEORY,
    "Pràctiques": LectureType.LAB,
    "Seminari": LectureType.SEMINAR,
}


def parse_schedule_rows(
    rows: list, start_date: date, end_date: date
) -> List[ScheduledLecture]:
    """Parses raw row elements from the scraper into a list of ScheduledLecture objects."""
    classes: List[ScheduledLecture] = []
    current_day_element = None

    skipped = 0
    for row in rows:
        row_classes = row["class"]
        if not row_classes or (
            "fc-event" not in row_classes and "fc-list-day" not in row_classes
        ):
            continue

        if "fc-list-day" in row_classes:
            current_day_element = row["data_date"]
            continue

        if "festiu" in row_classes or "assig" not in row_classes:
            continue

        class_time = row["event_time"]
        details = row["details"].split("\n")
        if len(details) < 3:
            skipped += 1
            continue

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
        if current_day_element:
            date_str = current_day_element

            current_day = datetime.strptime(date_str, "%Y-%m-%d").date()
            if end_date < current_day:
                break
            elif start_date > current_day:
                continue

            start_time = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")

            scheduled_lecture = ScheduledLecture(
                course_id=int(course_id_str),
                course_name=course_name,
                classroom=classroom,
                group_num=group_num,
                lecture_type=lecture_type,
                start_time=start_time,
                end_time=end_time,
            )
            classes.append(scheduled_lecture)
        else:
            raise ValueError(
                "Lecture row encountered without a preceding day header (fc-list-day). Input data may be malformed."
            )

    if skipped:
        print(
            f"⚠️ Could not parse {skipped} classes due to unexpected format. They have been skipped."
        )
    return classes
