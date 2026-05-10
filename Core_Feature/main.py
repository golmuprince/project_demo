from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.router import router
from agents.planner_agent import planner_agent
from agents.class_agent import class_agent
from agents.quiz_agent import quiz_agent
import readline
class AgentState(MessagesState):
    current_agent: str

def router_check(state: AgentState):
    current_agent = state.get("current_agent", "router")
    return current_agent

graph_builder = StateGraph(AgentState)

graph_builder.add_node(
    "router",
    router,
    destinations=(
        "planner_agent",
        "class_agent",
        "quiz_agent",
    ),
)
graph_builder.add_node("planner_agent", planner_agent)
graph_builder.add_node("class_agent", class_agent)
graph_builder.add_node("quiz_agent", quiz_agent)

graph_builder.add_conditional_edges(
    START,
    router_check,
    [
        "router",
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