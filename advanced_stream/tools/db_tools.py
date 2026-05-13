import sqlite3
import json
from datetime import date
from langchain_core.tools import tool

DB_PATH = "linux_master.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_date TEXT,
            created_at TEXT,
            weekly_plan TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            topic TEXT,
            summary TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            topic TEXT,
            question TEXT,
            is_correct INTEGER
        )
    """)

    # 출석 체크 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            studied INTEGER DEFAULT 0,
            quizzed INTEGER DEFAULT 0,
            quiz_score TEXT
        )
    """)

    conn.commit()
    conn.close()

# 앱 시작할 때 테이블 생성
init_db()


@tool
def save_plan(exam_date: str, weekly_plan: dict):
    """
    학습 플랜을 DB에 저장합니다.
    Args:
        exam_date: 시험 날짜 (예: '2025-11-08')
        weekly_plan: 주차별 학습 계획 딕셔너리
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_plan (exam_date, created_at, weekly_plan)
        VALUES (?, ?, ?)
    """, (
        exam_date,
        str(date.today()),
        json.dumps(weekly_plan, ensure_ascii=False)
    ))

    conn.commit()
    conn.close()
    return "플랜이 저장됐어요!"


@tool
def load_plan():
    """
    가장 최근 학습 플랜을 DB에서 불러옵니다.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT exam_date, weekly_plan
        FROM study_plan
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return "저장된 플랜이 없어요."

    exam_date, weekly_plan = row
    return {
        "exam_date": exam_date,
        "weekly_plan": json.loads(weekly_plan)
    }


@tool
def save_study_log(topic: str, summary: str):
    """
    오늘 학습한 내용을 DB에 저장합니다.
    Args:
        topic: 학습한 주제
        summary: 학습 내용 요약
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_log (date, topic, summary)
        VALUES (?, ?, ?)
    """, (
        str(date.today()),
        topic,
        summary
    ))

    conn.commit()
    conn.close()
    return "학습 일지가 저장됐어요!"


@tool
def load_quiz_bank(topic: str = None):
    """
    real_quiz.json에서 기출문제를 불러옵니다.
    Args:
        topic: 주제 필터 (없으면 전체 반환)
               예: '1주차', '파일 권한', '프로세스'
    """
    with open("data/real_quiz.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    if topic:
        questions = [q for q in questions if topic in q["topic"]]

    return questions


@tool
def save_quiz_log(topic: str, question: str, is_correct: bool):
    """
    퀴즈 결과를 DB에 저장합니다.
    Args:
        topic: 퀴즈 주제
        question: 퀴즈 문제
        is_correct: 정답 여부
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO quiz_log (date, topic, question, is_correct)
        VALUES (?, ?, ?, ?)
    """, (
        str(date.today()),
        topic,
        question,
        1 if is_correct else 0
    ))

    conn.commit()
    conn.close()
    return "퀴즈 결과가 저장됐어요!"


@tool
def load_wrong_questions(limit: int = 10):
    """
    이전에 틀린 문제를 불러옵니다.
    Args:
        limit: 불러올 문제 수 (기본 10개)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT topic, question, is_correct
        FROM quiz_log
        WHERE is_correct = 0
        ORDER BY date DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "이전에 틀린 문제가 없어요."

    wrong = []
    for topic, question, _ in rows:
        # quiz_bank에서 해당 문제 전체 정보 불러오기
        try:
            with open("data/real_quiz.json", "r", encoding="utf-8") as f:
                all_questions = json.load(f)
            matched = [q for q in all_questions if q["question"].strip()[:30] == question.strip()[:30]]
            if matched:
                wrong.append(matched[0])
            else:
                wrong.append({"topic": topic, "question": question})
        except Exception:
            wrong.append({"topic": topic, "question": question})

    return wrong


@tool
def mark_attendance(studied: bool = False, quizzed: bool = False, quiz_score: str = ""):
    """
    오늘의 출석 및 학습/퀴즈 완료를 기록합니다.
    Args:
        studied: 오늘 학습 완료 여부
        quizzed: 오늘 퀴즈 완료 여부
        quiz_score: 퀴즈 점수 (예: "8/10")
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = str(date.today())
    cursor.execute("""
        INSERT INTO attendance (date, studied, quizzed, quiz_score)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            studied = MAX(studied, ?),
            quizzed = MAX(quizzed, ?),
            quiz_score = CASE WHEN ? != '' THEN ? ELSE quiz_score END
    """, (
        today,
        1 if studied else 0,
        1 if quizzed else 0,
        quiz_score,
        1 if studied else 0,
        1 if quizzed else 0,
        quiz_score, quiz_score
    ))

    conn.commit()
    conn.close()
    return "출석 기록 완료!"


def get_attendance_data():
    """출석 데이터를 불러옵니다. (툴 아님, 앱에서 직접 호출)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT date, studied, quizzed, quiz_score FROM attendance ORDER BY date")
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "studied": r[1], "quizzed": r[2], "quiz_score": r[3]} for r in rows]