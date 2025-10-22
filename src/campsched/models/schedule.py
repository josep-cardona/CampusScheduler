from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LectureType(Enum):
    THEORY="Teoria"
    LAB="Pràctiques"
    SEMINAR="Seminari"


@dataclass
class ScheduledLecture:

    course_id: int
    course_name: str
    classroom: str
    group_num: int
    lecture_type: LectureType
    start_time: datetime
    end_time: datetime

    def __str__(self):
        return (
            "--------------------------------------------------\n"
            f"{self.course_id} - {self.course_name}\n"
            f"Group: {self.group_num} | Type: {self.lecture_type.value}\n"
            f"Classroom: {self.classroom}\n"
            f"Time: {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%H:%M')}"
        )