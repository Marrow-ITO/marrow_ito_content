from enum import Enum

from app.models.base import BaseDoc, PyObjectId


class MCQAnswer(str, Enum):
    OPTION_1 = "option_1"
    OPTION_2 = "option_2"
    OPTION_3 = "option_3"
    OPTION_4 = "option_4"


class MCQ(BaseDoc):
    title: str
    option_1: str
    option_2: str
    option_3: str
    option_4: str
    answer: MCQAnswer
    answer_desc: str

    subject_id: PyObjectId
    topic_id: PyObjectId
    lesson_id: PyObjectId
    qbank_id: PyObjectId
