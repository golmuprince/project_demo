import streamlit as st
import os
import sqlite3
import json
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
load_dotenv(override=True)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.router import router
from agents.planner_agent import planner_agent
from agents.class_agent import class_agent
from agents.quiz_agent import quiz_agent
from tools.db_tools import load_plan, get_attendance_data

DB_PATH = "linux_master.db"

st.set_page_config(
    page_title="Linux PassBuddy",
    page_icon="🐧",
    layout="centered"
)

class AgentState(MessagesState):
    current_agent: str

def router_check(state: AgentState):
    return state.get("current_agent", "router")

@st.cache_resource
def build_graph():
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("router", router, destinations=("planner_agent", "class_agent", "quiz_agent"))
    graph_builder.add_node("planner_agent", planner_agent)
    graph_builder.add_node("class_agent", class_agent)
    graph_builder.add_node("quiz_agent", quiz_agent)
    graph_builder.add_conditional_edges(START, router_check, ["router", "planner_agent", "class_agent", "quiz_agent"])
    graph_builder.add_edge("router", END)
    graph_builder.add_edge("planner_agent", END)
    graph_builder.add_edge("class_agent", END)
    graph_builder.add_edge("quiz_agent", END)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    memory = SqliteSaver(conn)
    return graph_builder.compile(checkpointer=memory)

graph = build_graph()
config = {"configurable": {"thread_id": "user_1"}}

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = "router"

def plan_to_daily(weekly_plan: dict, start_date: str) -> list:
    """주차별 계획을 일차별 리스트로 변환"""
    daily = []
    try:
        base = datetime.strptime(start_date, "%Y-%m-%d").date()
    except Exception:
        base = date.today()

    day_num = 0
    for week, topics in weekly_plan.items():
        if week == "총_학습일":
            continue
        if isinstance(topics, list):
            for topic in topics:
                daily.append({
                    "day": day_num + 1,
                    "week": week,
                    "topic": topic,
                    "date": str(base + timedelta(days=day_num))
                })
                day_num += 1
        else:
            for topic in str(topics).split(","):
                topic = topic.strip()
                if topic:
                    daily.append({
                        "day": day_num + 1,
                        "week": week,
                        "topic": topic,
                        "date": str(base + timedelta(days=day_num))
                    })
                    day_num += 1
    return daily

def get_db_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    stats = {}
    for table in ["study_plan", "study_log", "quiz_log", "attendance"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except Exception:
            stats[table] = 0

    try:
        cursor.execute("SELECT date, topic, is_correct FROM quiz_log ORDER BY id DESC LIMIT 5")
        stats["recent_quiz"] = cursor.fetchall()
    except Exception:
        stats["recent_quiz"] = []

    try:
        cursor.execute("SELECT date, topic FROM study_log ORDER BY id DESC LIMIT 5")
        stats["recent_study"] = cursor.fetchall()
    except Exception:
        stats["recent_study"] = []

    conn.close()
    return stats

with st.sidebar:
    st.title("🐧 Linux PassBuddy")

    if True:
        try:
            plan = load_plan.invoke({})
        except Exception:
            plan = None

        if isinstance(plan, dict):
            target_date = plan.get("exam_date", plan.get("target_date", ""))
            if target_date:
                try:
                    d_day = (datetime.strptime(target_date, "%Y-%m-%d").date() - date.today()).days
                    d_label = f"D-{d_day}" if d_day > 0 else ("D-Day!" if d_day == 0 else f"D+{abs(d_day)}")
                    st.metric("🎯 목표까지", d_label, delta=target_date, delta_color="off")
                except Exception:
                    st.metric("🎯 목표 날짜", target_date)
            else:
                st.metric("🎯 목표 날짜", "미설정")

            attendance = get_attendance_data()
            att_map = {a["date"]: a for a in attendance}
            studied_days = sum(1 for a in attendance if a["studied"])
            quizzed_days = sum(1 for a in attendance if a["quizzed"])

            col1, col2 = st.columns(2)
            col1.metric("✅ 학습일", f"{studied_days}일")
            col2.metric("🧩 퀴즈일", f"{quizzed_days}일")

            st.divider()

            weekly_plan = plan.get("weekly_plan", {})
            created_at = plan.get("created_at", str(date.today()))
            daily_list = plan_to_daily(weekly_plan, created_at)

            if daily_list:
                weeks = {}
                for d in daily_list:
                    w = d["week"]
                    if w not in weeks:
                        weeks[w] = []
                    weeks[w].append(d)

                for week, days in weeks.items():
                    done = sum(1 for d in days if att_map.get(d["date"], {}).get("studied", 0))
                    total = len(days)
                    pct = int(done / total * 100) if total > 0 else 0

                    with st.expander(f"**{week}** ({done}/{total} · {pct}%)"):
                        for d in days:
                            att = att_map.get(d["date"], {})
                            s_icon = "✅" if att.get("studied") else "⬜"
                            q_icon = "🧩" if att.get("quizzed") else "  "
                            score = f" `{att['quiz_score']}`" if att.get("quiz_score") else ""
                            is_today = d["date"] == str(date.today())
                            today_mark = " 👈" if is_today else ""
                            st.write(f"{s_icon}{q_icon} **Day {d['day']}** {d['topic'][:18]}{'...' if len(d['topic']) > 18 else ''}{score}{today_mark}")
            else:
                st.info("계획이 없어요.")
        else:
            st.info("학습 계획이 없어요.\n플래너에게 계획을 요청해보세요!")

    st.divider()
        agent_labels = {
            "router":        "🔀 라우터",
            "planner_agent": "📅 플래너",
            "class_agent":   "📚 클래스",
            "quiz_agent":    "🧩 퀴즈",
        }
        st.caption("현재 에이전트")
        st.write(agent_labels.get(st.session_state.current_agent, "🔀 라우터"))

        st.divider()

        if st.button("🗑️ 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_agent = "router"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for table in ["checkpoints", "checkpoint_writes", "checkpoint_blobs"]:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
            st.rerun()

        if st.button("📋 계획 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_agent = "router"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for table in ["study_plan", "study_log", "quiz_log", "attendance"]:
                cursor.execute(f"DELETE FROM {table}")
            for table in ["checkpoints", "checkpoint_writes", "checkpoint_blobs"]:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
            st.rerun()

st.title("🐧 Linux PassBuddy")
st.caption("리눅스마스터 2급 취득을 도와드려요!")
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("무엇이든 물어보세요 (예: 학습 계획 짜줘, 오늘 공부할래, 퀴즈 풀고 싶어)")

if user_input:
    with st.chat_message("human"):
        st.write(user_input)
    st.session_state.messages.append({"role": "human", "content": user_input})

    with st.chat_message("ai"):
        with st.spinner("생각 중..."):
            try:
                result = graph.invoke(
                    {
                        "messages": [{"role": "user", "content": user_input}],
                        "current_agent": st.session_state.current_agent,
                    },
                    config=config
                )
                response = result["messages"][-1].content
                new_agent = result.get("current_agent", "router")
                st.session_state.current_agent = new_agent
                st.write(response)
                st.session_state.messages.append({"role": "ai", "content": response})
            except Exception as e:
                st.error(f"오류가 발생했어요: {str(e)}")

    st.rerun()        "router",
        "planner_agent",
        "class_agent",
        "quiz_agent",
    ],
)
graph_builder.add_edge("router", END)
graph_builder.add_edge("planner_agent", END)
graph_builder.add_edge("class_agent", END)
graph_builder.add_edge("quiz_agent", END)

with SqliteSaver.from_conn_string("linux_master.db") as memory:
    graph = graph_builder.compile(checkpointer=memory)
 
    config = {"configurable": {"thread_id": "user_1"}}
 
    print("\n 리눅스마스터 2급 학습 도우미")
    print("─" * 40)
    print("종료하려면 'exit' 입력 또는 Cmd+C\n")
 
    try:
        while True:
            print()
            user_input = input("나: ")
 
            if user_input.strip() == "":
                continue
 
            if user_input.lower() == "exit":
                print("\n학습 종료! 오늘도 수고했습니다\n")
                break
 
            result = graph.invoke({
                "messages": [{"role": "user", "content": user_input}],
            }, config=config)
 
            print()
            print("─" * 40)
            print("에이전트:", result["messages"][-1].content)
            print("─" * 40)
 
    except KeyboardInterrupt:
        print("\n\n학습 종료! 오늘도 수고했습니다 \n")
