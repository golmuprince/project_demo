from langchain_core.tools import tool
from typing import Literal, List
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

class Question(BaseModel):
    question: str = Field(description="퀴즈 문제")
    options: List[str] = Field(description="4개의 보기 A, B, C, D")
    correct_answer: str = Field(description="정답 (보기 중 하나와 일치해야 함)")
    explanation: str = Field(description="정답 및 오답 이유 설명")

class Quiz(BaseModel):
    topic: str = Field(description="퀴즈 주제")
    questions: List[Question] = Field(description="퀴즈 문제 목록")

@tool
def generate_quiz(
    topic: str,
    difficulty: Literal["easy", "medium", "hard"],
    num_questions: int,
):
    """
    리눅스마스터 2급 퀴즈를 생성합니다.
    Args:
        topic: 퀴즈 주제 (예: '파일 권한 관리', '프로세스 관리')
        difficulty: 난이도 'easy', 'medium', 'hard' 중 하나
        num_questions: 문제 수 (1~15)
    """
    model = init_chat_model("openai:gpt-4o")
    structured_model = model.with_structured_output(Quiz)

    prompt = f"""
    리눅스마스터 2급 시험 기준으로
    {topic} 주제의 {difficulty} 난이도 퀴즈를 {num_questions}문제 만들어주세요.

    조건:
    - 실제 시험에 나올 법한 문제로 만들어주세요
    - 보기는 4개로 만들어주세요
    - 한국어로 만들어주세요
    - 명령어 문제는 실제 리눅스 명령어를 사용하세요
    """

    quiz = structured_model.invoke(prompt)
    return quiz