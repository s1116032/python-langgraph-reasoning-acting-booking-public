"""
LangGraph ReAct 工具層。
將現有的預約業務邏輯 (service/db) 包裝成 LLM 可呼叫的工具。
"""

from langchain_core.tools import tool
from booking.service import (
    submit_booking,
    get_current_user_id,
    cancel_booking,
)
from booking.db import list_available_rooms, list_user_reservations


@tool
def list_rooms() -> str:
    """查詢目前校園內開放預約的討論室清單及其容量上限；此工具不需要任何參數。"""
    try:
        rooms = list_available_rooms()
        if not rooms:
            return "目前沒有開放的討論室。"

        return "\n".join(
            [f"編號: {r['room_id']}, 容量: {r['capacity']}人" for r in rooms]
        )
    except Exception:
        return "查詢討論室時發生問題，請稍後再試。"


@tool
def get_my_bookings() -> str:
    """查詢目前登入使用者自己的有效預約紀錄；此工具不需要任何參數，請勿詢問姓名或學號。

    使用時機：
    - 使用者詢問「我的預約」、「現有預約」、「我有哪些預約」、「查詢預約」時。
    - 系統已知道目前使用者身分，不需要使用者提供姓名或學號。
    - 此工具只能查詢目前登入者自己的預約，不能查詢其他使用者。
    """
    try:
        student_id = get_current_user_id()
        reservations = list_user_reservations(student_id, status="confirmed")

        if not reservations:
            return "目前沒有任何有效的預約紀錄。"

        lines = []
        for r in reservations:
            lines.append(
                f"預約編號: #{r['id']}, 討論室: {r['room_id']}, "
                f"時間: {r['start_time']} ~ {r['end_time']}, "
                f"人數: {r['people_count']}人, 事由: {r['reason']}"
            )
        return "\n".join(lines)

    except Exception:
        return "查詢預約紀錄時發生問題，請稍後再試。"


@tool
def create_booking(
    room_id: str,
    people_count: int,
    start_time: str,
    end_time: str,
    reason: str,
) -> str:
    """建立新的討論室預約；必須在五個欄位都齊全，且使用者已明確確認後才可呼叫。

    使用限制：
    - 若缺少任何欄位，請勿呼叫此工具，應先向使用者追問。
    - 若使用者尚未明確確認，請勿呼叫此工具。
    - 參數：
      - room_id: 討論室編號，例如 A01, B02
      - people_count: 預約人數，整數，必須大於等於 2
      - start_time: 開始時間，格式必須是 YYYY-MM-DD HH:MM
      - end_time: 結束時間，格式必須是 YYYY-MM-DD HH:MM
      - reason: 預約事由，必須是實際原因
    """
    try:
        fields = {
            "room_id": room_id,
            "people_count": people_count,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
        }

        result = submit_booking(fields)

        if result["success"]:
            return f"預約成功！預約編號：{result['reservation_id']}。"

        return f"預約失敗：{result['message']}。請根據錯誤訊息調整參數後再試一次。"

    except Exception:
        return "預約時發生系統錯誤，請稍後再試。"


@tool
def cancel_booking_tool(reservation_id: int) -> str:
    """取消指定的討論室預約；必須先查詢預約紀錄並向使用者明確確認後才可呼叫。

    使用限制：
    - 如果使用者要求取消預約，應先呼叫 get_my_bookings 確認預約存在。
    - 必須向使用者展示該預約編號、討論室與時間，並取得明確確認。
    - 參數：
      - reservation_id: 預約編號，純數字，不包含 # 號
    """
    try:
        result = cancel_booking(reservation_id)

        if result["success"]:
            return f"已成功取消預約 #{reservation_id}。"

        return f"取消失敗：{result['message']}"

    except Exception:
        return "取消預約時發生系統錯誤，請稍後再試。"


tools = [list_rooms, get_my_bookings, create_booking, cancel_booking_tool]
