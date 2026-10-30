"""
LangGraph ReAct Agent 組裝層。
"""

from datetime import datetime
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from tools import tools


llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0,
    num_ctx=8192,
)


def get_system_prompt() -> str:
    """生成帶有當前日期的 System Prompt"""
    today = datetime.now().strftime("%Y-%m-%d %A")

    return f"""你是星光大學校園預約助手。
今天是 {today}。

系統已綁定目前登入使用者。
禁止詢問使用者姓名、學號或帳號。
查詢我的預約時，直接呼叫 get_my_bookings；此工具不需要參數。

建立預約需要五個欄位：
- room_id
- people_count
- start_time，格式 YYYY-MM-DD HH:MM
- end_time，格式 YYYY-MM-DD HH:MM
- reason

如果缺少欄位，請追問使用者，不要猜測。
收集齊全後，先列出資訊請使用者確認；使用者明確確認後才呼叫 create_booking。

取消預約前，先呼叫 get_my_bookings 確認預約存在，並請使用者確認。

工具失敗時，請用自然語言說明，不要輸出 JSON 或錯誤堆疊。
請使用繁體中文回答。
"""


def build_graph():
    """
    使用 canonical 寫法建立 ReAct Agent。
    由 create_react_agent 內部處理工具綁定。
    """
    agent = create_react_agent(
        model=llm,
        tools=tools,
    )
    return agent


campus_agent = build_graph()
