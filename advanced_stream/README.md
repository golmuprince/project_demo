랭그래프로 만든 리눅스마스터 2급 취득 도우미입니다
목표날짜 넣으면 알아서 계획 짜주고, 오늘 뭐 공부할지 알려주고, 기출문제로 퀴즈도 내줍니다.

플래너 - 목표날짜 알려주면 남은 기간에 맞게 주차별 학습 계획 짜줌
클래스 - 오늘 공부할 내용 개념 설명
퀴즈 - 기출문제로 퀴즈 내줌, 틀리면 피드백 가능

bashpip install langgraph langchain-core langchain-openai python-dotenv streamlit pdf2image pillow

# .env 파일에 추가
OPENAI_API_KEY=your_key

# 웹으로 실행
streamlit run main.py

linux_master/
├── main.py                      ← streamlit 웹 버전
├── agents/
│   ├── router.py               ← 사용자 의도 파악해서 에이전트로 넘김
│   ├── planner_agent.py        ← 학습 계획 짜주는 에이전트
│   ├── class_agent.py          ← 오늘 공부 내용 설명해주는 에이전트
│   └── quiz_agent.py           ← 퀴즈 내주는 에이전트
├── tools/
│   ├── shared_tools.py         ← 에이전트 전환 툴
│   ├── db_tools.py             ← sqlite 저장/불러오기
├── data/
│   └── real_quiz.json          ← 기출문제 모음 (직접 추가 가능)
└── linux_master.db             ← 학습 기록 저장되는 db (자동 생성)
