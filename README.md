\# 星光大學校園助手（LangGraph ReAct PoC）



本專案是一個使用 \*\*LangGraph ReAct Agent\*\* 搭建的校園討論室預約助手 PoC。



使用者可透過自然語言查詢討論室、建立預約、查詢預約或取消預約。  

Agent 會自行判斷是否需要呼叫工具、是否需要追問使用者，以及如何以自然語言回覆。



\---



\## 核心功能



\- 查詢開放中的討論室與容量

\- 查詢目前使用者的有效預約紀錄

\- 建立討論室預約

\- 取消討論室預約

\- 輸入白名單檢查與 Unicode 正規化

\- 預約欄位驗證

\- 時段衝突檢查

\- 工具失敗時顯示友善訊息

\- 繁體中文校園情境對話



\---



\## 技術架構



\- Python

\- Streamlit

\- LangChain

\- LangGraph

\- Ollama

\- SQLite



使用模型：



```text

qwen2.5:7b

```



\---



\## 目錄結構



```text

.

├── app.py                  # Streamlit 入口與聊天介面

├── graph.py                # LangGraph ReAct Agent 組裝層

├── tools.py                # LangGraph 工具層

├── input\_guard.py          # 輸入白名單與正規化

├── test\_tools.py           # 工具簡單測試

├── data/

│   └── campus.db           # SQLite 資料庫，首次執行時自動建立

└── booking/

&#x20;   ├── \_\_init\_\_.py

&#x20;   ├── db.py               # 資料庫存取層

&#x20;   └── service.py          # 預約業務邏輯層

```



\---



\## 快速開始



先下載並啟動 Ollama 模型：



```bash

ollama pull qwen2.5:7b

ollama serve

```



安裝 Python 套件：



```bash

pip install streamlit python-dotenv langchain-core langchain-ollama langgraph

```



執行專案：



```bash

streamlit run app.py

```



首次執行時，專案會自動建立 SQLite 資料庫與預設討論室資料。



\---



\## 使用範例



\### 查詢討論室



```text

有哪些討論室可以預約？

```



\### 查詢預約



```text

我目前有哪些預約？

```



\### 建立預約



```text

我想預約明天下午兩點的 B01 討論室，大概 5 個人，事由是專題開會。

```



若資訊不完整，Agent 會主動追問缺少的欄位。



\### 取消預約



```text

我要取消預約 #3

```



Agent 會先展示預約內容，並在使用者確認後才執行取消。



\---



\## ReAct 流程詳解



ReAct 是 \*\*Reasoning + Acting\*\* 的結合。  

Agent 會依照下列循環運作：



1\. 理解使用者需求

2\. 推理接下來該做什麼

3\. 決定是否呼叫工具

4\. 執行工具取得觀察結果

5\. 根據觀察結果繼續推理

6\. 產生最終自然語言回覆



\---



\## 整體流程圖



```mermaid

graph TD

&#x20;   User\[使用者輸入] --> Streamlit\[Streamlit app.py]

&#x20;   Streamlit --> InputGuard\[輸入檢查與正規化]

&#x20;   InputGuard --> MessageBuilder\[組裝訊息歷史]

&#x20;   MessageBuilder --> Agent\[LangGraph ReAct Agent]



&#x20;   Agent --> LLM\[LLM 推理]



&#x20;   LLM -->|需要工具| ToolCall\[產生 tool\_calls]

&#x20;   ToolCall --> ToolNode\[ToolNode 執行工具]

&#x20;   ToolNode --> ToolResult\[回傳 ToolMessage]

&#x20;   ToolResult --> LLM



&#x20;   LLM -->|可直接回覆| FinalAnswer\[產生最終 AIMessage]

&#x20;   FinalAnswer --> Sanitize\[前端安全過濾]

&#x20;   Sanitize --> User

```



\---



\## 一次完整請求流程



\### 1. 使用者輸入



使用者輸入自然語言需求，例如：



```text

我想預約明天下午兩點的 B01 討論室，大概 5 個人。

```



\---



\### 2. 輸入前處理



系統先透過 `input\_guard.py` 檢查輸入：



\- 檢查長度

\- 檢查白名單字元

\- Unicode 正規化

\- 正規化後再次檢查



若輸入不合法，系統會直接提示錯誤，不會呼叫 Agent。



\---



\### 3. 組裝訊息歷史



`app.py` 會將聊天紀錄轉換為 LangChain 訊息格式：



\- `SystemMessage`

\- `HumanMessage`

\- `AIMessage`



其中 System Prompt 會由 `app.py` 在每次請求時動態產生，確保日期資訊是最新的。



\---



\### 4. 呼叫 LangGraph Agent



程式執行：



```python

result = agent.invoke({"messages": lc\_messages})

```



LangGraph 會將整段對話交給 Agent 處理。



\---



\### 5. LLM 推理



LLM 會根據系統提示、歷史對話與可用工具，判斷下一步。



例如使用者說：



```text

我想預約明天下午兩點的 B01 討論室，大概 5 個人。

```



LLM 可能發現缺少：



\- 結束時間

\- 事由



因此先向使用者追問，而不是直接建立預約。



\---



\### 6. 工具呼叫



若 LLM 需要查詢資料，會產生工具呼叫。



例如：



```text

查詢討論室

```



會呼叫：



```python

list\_rooms

```



或：



```text

查詢我的預約

```



會呼叫：



```python

get\_my\_bookings

```



\---



\### 7. ToolNode 執行工具



LangGraph 的 `ToolNode` 會根據 `tool\_calls` 執行工具。



工具結果會以 `ToolMessage` 回傳給 Agent。



\---



\### 8. LLM 根據工具結果繼續推理



LLM 拿到工具結果後，會再次判斷：



\- 是否還需要呼叫其他工具？

\- 是否資料已足夠？

\- 是否需要追問使用者？

\- 是否可以產生最終回覆？



若還缺資料，就繼續循環；若資料完整，就產生最終回覆。



\---



\## ReAct 循環示意



```mermaid

graph TD

&#x20;   A\[LLM 推理] --> B{是否需要工具？}



&#x20;   B -->|是| C\[產生 tool\_calls]

&#x20;   C --> D\[ToolNode 執行工具]

&#x20;   D --> E\[回傳 ToolMessage]

&#x20;   E --> A



&#x20;   B -->|否| F\[產生最終回覆]

&#x20;   F --> G\[顯示給使用者]

```



\---



\## 預約建立流程範例



\### 使用者輸入



```text

我想預約明天下午兩點的 B01 討論室，大概 5 個人。

```



\### Agent 回覆



```text

好的，我已收到部分資訊。請問預計使用到幾點？另外請提供預約事由。

```



\### 使用者補充



```text

到下午四點，事由是專題開會。

```



\### Agent 確認



```text

請確認以下預約資訊：



討論室：B01

人數：5 人

開始時間：2026-10-27 14:00

結束時間：2026-10-27 16:00

事由：專題開會



請問以上資訊正確嗎？確認後我將為您送出預約。

```



\### 使用者確認



```text

確認。

```



\### Agent 呼叫工具



```python

create\_booking(

&#x20;   room\_id="B01",

&#x20;   people\_count=5,

&#x20;   start\_time="2026-10-27 14:00",

&#x20;   end\_time="2026-10-27 16:00",

&#x20;   reason="專題開會"

)

```



\### 最終回覆



```text

預約成功！預約編號：#12。

```



\---



\## 工具清單



\### `list\_rooms`



查詢目前開放的討論室清單。



```text

編號: A01, 容量: 4人

編號: B01, 容量: 6人

```



\---



\### `get\_my\_bookings`



查詢目前使用者的有效預約紀錄。



```text

預約編號: #3, 討論室: B01, 時間: 2026-10-27 14:00 \~ 2026-10-27 16:00

```



\---



\### `create\_booking`



建立新的討論室預約。



參數：



| 參數 | 說明 |

|---|---|

| room\_id | 討論室編號 |

| people\_count | 人數 |

| start\_time | 開始時間，格式為 `YYYY-MM-DD HH:MM` |

| end\_time | 結束時間，格式為 `YYYY-MM-DD HH:MM` |

| reason | 預約事由 |



\---



\### `cancel\_booking\_tool`



取消指定預約。



參數：



| 參數 | 說明 |

|---|---|

| reservation\_id | 預約編號，純數字 |



\---



\## 錯誤處理



為避免工具失敗時使用者看到原始 JSON 或技術錯誤，本專案採取以下處理：



1\. `tools.py` 中所有工具皆回傳自然語言字串。

2\. `booking/service.py` 負責業務規則驗證，回傳使用者可理解的錯誤訊息。

3\. `ToolNode` 使用 `handle\_tool\_errors=True`，避免工具例外直接中斷流程。

4\. `app.py` 只取最後一條有效的 `AIMessage` 作為回覆。

5\. 若回覆內容疑似 JSON 或技術錯誤，會轉為友善訊息。



例如使用者會看到：



```text

抱歉，系統處理時發生問題，請稍後再試。

```



而不是原始錯誤堆疊或 JSON。



\---



\## 預約業務規則



\### 人數限制



\- 人數需大於等於 2

\- 人數不可超過討論室容量



\### 時間規則



\- 時間格式：`YYYY-MM-DD HH:MM`

\- 結束時間需晚於開始時間

\- 不可跨天

\- 不可預約過去時間



\### 開放時段



週一至週五：



```text

08:00–21:30

```



週末：



```text

09:00–17:30

```



\### 事由規則



事由不可為空白、過短、無意義或測試用途。



\---



\## 目前限制



本專案為 PoC，不包含正式產品級功能。



\- 使用者身分固定為 `S123456789`

\- 尚未整合真實登入系統

\- 尚未提供修改預約功能

\- 使用本地 SQLite，不適合多使用者正式環境

\- 未加入正式日誌與錯誤監控



\---



\## 後續可擴展方向



\- 串接真實帳號系統

\- 加入修改預約功能

\- 加入預約審核流程

\- 加入串流式輸出

\- 導入正式資料庫

\- 加入權限控制與稽核機制

