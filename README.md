# 美股三日 ATR Google Sheet Pipeline

Version: `0.1.1`  
Git/GitHub 初始化請見 [`GIT_SETUP.md`](GIT_SETUP.md)。

這個版本保留原本 Google Sheet 的「計算」工作表，不改寫原有市值、ETF 穿透曝險與配置公式。程式只讀取 A 欄 ticker 與 P 欄 target dollar，再建立累積性的每週計畫與 Day1–Day3 執行紀錄。

## 工作表

- `設定`：原始工作表名稱、欄位與 Day2 參數。
- `程式輸入`：透過公式連到 `計算!A:P`，只暴露 `ticker / target_dollar`。
- `每週計畫`：Day1 開始時將當週 target dollar 凍結為 `plan_id`。
- `執行紀錄`：累積保存每天訂單。使用者只編輯 `filled_price`，`filled_date` 可留空由程式補入。
- `每日確認`：核對閘門；沒有確認就不會進入隔日。

## 執行環境

Python 3.11 或更新版本。

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Google 憑證

1. 沿用原本 pipeline 的 Google service account JSON。
2. 將目標 Google Sheet 共用給 service account 的 email，權限設為編輯者。
3. 複製 `.env.example` 為 `.env`。
4. 確認 `GOOGLE_SHEET_ID` 與憑證檔路徑。

`service_account.json` 必須放進 `.gitignore`，不得提交到 GitHub。

## 第一次初始化

```powershell
python init_google_sheet.py
```

這個指令只新增程式專用工作表，不刪除、改名或清空原有工作表。

## 啟動

```powershell
streamlit run app.py
```

## 每週流程

1. 週日照常在原本 Google Sheet 更新市值與 P 欄。
2. Day1 按「從 Google Sheet 建立／讀取本週計畫」，再產生 Day1 訂單。
3. 在 FT 下單。成交後到 `執行紀錄` 填 `filled_price`。
4. 回到 App，勾選已核對並按「完成今日核對」。
5. 下一個美東交易日，程式只對空白列產生 Day2，使用 `Day1 k × 0.6`。
6. Day3 剩餘列使用 MARKET，但仍需填真實成交價才能關閉本週計畫。

## 重要安全規則

- 同一個美東交易日重跑不會進入下一階段。
- 前一日未完成核對，不會產生下一日訂單。
- Day1/Day2 空白列只有在使用者確認後才會進入下一階段。
- Day3 仍有空白成交價時，系統拒絕完成核對。
- Day1/Day2 固定使用 LIMIT；即使當下市價低於限價，仍送出該 LIMIT 以保留最高成交價保護。
- Day3 才使用 MARKET，真實成交價仍由使用者填寫。
- 若 Day1/Day2 真實成交價高於程式產生時的參考限價，系統會要求第二次確認，但不會完全阻擋。
- Day1/Day2 的 `filled_price` 若高於 `limit_price` 超過 0.01，核對會被阻擋，需先檢查委託類型或輸入。
- 第一版不處理部分成交。若實際發生，請先不要按每日核對，再增加 `filled_shares` 邏輯。

## 測試

```powershell
pytest -q
```
