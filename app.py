"""
Campus Agent Entrypoint (LangGraph ReAct 極簡版)。

提供本地聊天介面，整合輸入前處理與 LangGraph ReAct Agent。
"""

import json
import logging
import re

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from input_guard import check_allowed_chars, unicode_normalize
from booking.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(
    page_title="星光大學校園助手 (ReAct)",
    page_icon="✨",
    layout="wide",
)

INPUT_MAX_LENGTH = 1024


# =========================================================
# Guard：防止 Agent 誤問使用者身份
# =========================================================

OWN_BOOKING_KEYWORDS = [
    "我的預約",
    "目前預約",
    "現有預約",
    "預約紀錄",
    "我有預約",
    "我有哪些預約",
    "查詢預約",
    "查預約",
    "查詢我的預約",
    "看我的預約",
    "看一下我的預約",
    "有效預約",
]

IDENTITY_ASK_PATTERNS = [
    re.compile(r"請(提供|告訴|輸入).{0,20}(姓名|學號|帳號)"),
    re.compile(r"(姓名|學號|帳號).{0,20}(是|為|呢|嗎|？|\?)"),
    re.compile(r"哪位(使用者|同學|學生)"),
    re.compile(r"請問您是"),
    re.compile(r"您是誰"),
    re.compile(r"請告訴我您"),
]


def is_own_booking_query(text: str) -> bool:
    """
    判斷使用者是否明顯在查詢自己的預約。
    """
    if not isinstance(text, str):
        return False

    text = text.strip()

    if not text:
        return False

    if any(keyword in text for keyword in OWN_BOOKING_KEYWORDS):
        return True

    if re.search(r"(我的|目前|現有|有效).{0,12}預約", text):
        return True

    if re.fullmatch(
        r"(請問|幫我|麻煩)?\s*(查|查詢|看一下|列出)?\s*(我的|目前|現有|有效)?\s*預約(紀錄)?[?？]?(\s*)",
        text,
    ):
        return True

    return False


def asks_for_identity(text: str) -> bool:
    """
    判斷 Assistant 回覆是否不應該地詢問使用者身份。
    """
    if not isinstance(text, str):
        return False

    text = text.strip()

    if not text:
        return False

    return any(pattern.search(text) for pattern in IDENTITY_ASK_PATTERNS)


def looks_like_raw_tool_call(text: str) -> bool:
    """
    判斷文字是否像模型原始工具呼叫輸出。
    """
    if not isinstance(text, str):
        return False

    text = text.strip()

    if not text:
        return False

    raw_markers = [
        "<tool_call>",
        "</tool_call>",
        "tool_call",
        '"name":',
        '"arguments":',
    ]

    tool_names = [
        "get_my_bookings",
        "list_rooms",
        "create_booking",
        "cancel_booking_tool",
    ]

    return any(marker in text for marker in raw_markers) or any(
        tool_name in text for tool_name in tool_names
    )


def get_direct_my_bookings_reply() -> str:
    """
    當 Guard 判斷模型不應該詢問身份或輸出原始工具呼叫時，
    直接呼叫 get_my_bookings，回傳友善訊息。
    """
    try:
        from tools import get_my_bookings

        direct_result = get_my_bookings.invoke({})

    except Exception as guard_error:
        logger.exception("[Guard] 直接查詢預約失敗")
        return "抱歉，系統查詢預約時發生問題，請稍後再試。"

    if not isinstance(direct_result, str) or not direct_result.strip():
        return "目前沒有任何有效的預約紀錄。"

    if any(
        error_keyword in direct_result for error_keyword in ["發生問題", "失敗", "錯誤"]
    ):
        return direct_result

    if "沒有任何有效的預約紀錄" in direct_result:
        return direct_result

    return f"已為您查詢到目前的有效預約：\n{direct_result}"


# =========================================================
# 資源初始化 (快取)
# =========================================================


@st.cache_resource
def load_agent():
    """初始化資料庫並載入 LangGraph Agent。"""
    init_db()

    from graph import campus_agent, get_system_prompt

    return campus_agent, get_system_prompt


# =========================================================
# 主介面
# =========================================================

st.title("✨ 星光大學校園助手 (ReAct)")
st.caption(
    "這是一個使用 LangGraph ReAct 架構的預約討論室助手。"
    "您可以直接告訴我您的需求，例如：「我想預約明天下午兩點的 B01 討論室，大概 5 個人。」"
)

if st.sidebar.button("🗑️ 清空對話"):
    st.session_state.messages = []
    st.rerun()

# 初始化對話歷史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染歷史對話
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 處理使用者輸入
if prompt := st.chat_input("請輸入您的需求..."):
    # ---------------------------------------------------------
    # 1. 輸入前處理 (Input Guard)
    # ---------------------------------------------------------
    if (
        check_allowed_chars(
            prompt,
            allow_empty=False,
            max_length=INPUT_MAX_LENGTH,
        )
        == "refuse"
    ):
        st.warning(
            f"輸入格式不符合限制：長度不可超過 {INPUT_MAX_LENGTH} 字，或包含不允許的字元。"
        )
        st.stop()

    normalized_prompt = unicode_normalize(prompt)

    if (
        check_allowed_chars(
            normalized_prompt,
            allow_empty=False,
            max_length=INPUT_MAX_LENGTH,
        )
        == "refuse"
    ):
        st.warning("輸入經正規化後仍不符合格式限制，請重新輸入。")
        st.stop()

    # ---------------------------------------------------------
    # 2. 顯示使用者輸入並加入歷史
    # ---------------------------------------------------------
    st.session_state.messages.append(
        {
            "role": "user",
            "content": normalized_prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(normalized_prompt)

    # ---------------------------------------------------------
    # 3. 呼叫 LangGraph Agent
    # ---------------------------------------------------------
    with st.chat_message("assistant"):
        with st.spinner("AI 正在思考與執行工具..."):
            try:
                agent, get_system_prompt = load_agent()

                lc_messages = [SystemMessage(content=get_system_prompt())]

                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))

                result = agent.invoke({"messages": lc_messages})

                final_message = "抱歉，系統處理時發生問題，請稍後再試。"

                for msg in reversed(result["messages"]):
                    if isinstance(msg, AIMessage) and msg.content:
                        if isinstance(msg.content, str):
                            final_message = msg.content
                        else:
                            final_message = str(msg.content)
                        break

                # 防止內容仍是 JSON / dict / error 訊息被直接顯示
                try:
                    parsed = json.loads(final_message)

                    if isinstance(parsed, dict):
                        final_message = (
                            "抱歉，系統執行時發生問題，請稍後再試或重新描述需求。"
                        )

                except Exception:
                    pass

                # ---------------------------------------------------------
                # Guard：如果使用者只是在查自己的預約，但 Agent 誤問姓名或學號，
                # 則不顯示錯誤回覆，直接以工具查詢目前使用者的預約。
                # ---------------------------------------------------------
                if is_own_booking_query(normalized_prompt) and asks_for_identity(
                    final_message
                ):
                    final_message = get_direct_my_bookings_reply()

                # ---------------------------------------------------------
                # Guard：如果 final_message 是原始工具呼叫文字，
                # 不要直接顯示給使用者。
                # ---------------------------------------------------------
                if looks_like_raw_tool_call(final_message):
                    if (
                        is_own_booking_query(normalized_prompt)
                        and "get_my_bookings" in final_message
                    ):
                        final_message = get_direct_my_bookings_reply()
                    else:
                        final_message = (
                            "抱歉，系統處理時發生問題，請稍後再試或重新描述需求。"
                        )

                st.markdown(final_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": final_message,
                    }
                )

            except Exception as e:
                logger.exception("Agent 執行錯誤")

                error_msg = "抱歉，系統處理時發生問題，請稍後再試。"

                st.error(error_msg)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_msg,
                    }
                )
