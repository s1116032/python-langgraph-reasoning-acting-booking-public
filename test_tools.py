from booking.db import init_db
from tools import get_my_bookings

init_db()
print("=== 直接呼叫工具測試 ===")
print(get_my_bookings.invoke({}))
