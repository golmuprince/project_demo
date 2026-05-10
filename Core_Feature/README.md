기능
- 플래너 : 시험날짜를 입력하면 주별 학습 계획을 짜줍니다.
- 클래스 : 오늘 학습할 내용을 설명해줌
- 퀴즈 : 기출문제로 오늘 배운 내용 테스트

실행방법
cursor - uv sync 후 재시작
.env 에 OPENAI_API_KEY="키값"
python main.py

파일 구조
linux_master/
├── main.py
├── agents/
│   ├── router.py
│   ├── planner_agent.py
│   ├── class_agent.py
│   └── quiz_agent.py
├── tools/
│   ├── shared_tools.py
│   └── db_tools.py
└── data/
    └── real_quiz.json  ← 기출문제