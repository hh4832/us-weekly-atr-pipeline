# Changelog

所有重要修改都記錄在這裡。版本原則使用 Semantic Versioning。

## [Unreleased]

- 待實際走完一週 Day1–Day3 後補上修正。
- 部分成交 `filled_shares` 邏輯尚未實作。

## [0.1.4] - 2026-08-25

### Fixed

- 快取 Google Sheet worksheet 物件，避免每次操作都重讀 spreadsheet metadata。
- 使用 gspread 指數退避 HTTP client，自動重試暫時性的 API 429/5xx。
- 每次 Streamlit rerun 少做一次重複的「執行紀錄」讀取。

## [0.1.3] - 2026-08-25

### Fixed

- 移除 `app.py` 對新版 `trading_engine.filled_price_warnings` 的啟動時匯入依賴。
- 即使 Streamlit Cloud 更新時暫時混用舊版 `trading_engine.py`，應用程式仍可啟動並執行二次確認。

## [0.1.2] - 2026-08-25

### Changed

- Day1/Day2 成交價高於程式參考限價時，不再直接阻擋每日核對。
- 第一次提交會顯示標的警告；使用者必須再次勾選並確認，才會完成當日核對。
- 非數字、非正數與 Day3 成交價空白仍維持強制阻擋。

## [0.1.1] - 2026-08-25

### Changed

- Day1 與 Day2 一律產生 LIMIT order，不再用程式抓價時的 reference price 預先改成 MARKET。
- Day3 維持 MARKET，以完成本週剩餘訂單。
- 新增限價成交價高於限價時的輸入阻擋。

### Rationale

- 程式抓取 10:00 reference price 與使用者實際下單時點可能不同。
- LIMIT 在當下市價低於限價時仍通常可立即成交，同時保留最高價格保護。

## [0.1.0] - 2026-08-25

### Added

- 直接讀取原 Google Sheet `計算` 工作表 A/P 欄。
- 每週凍結 target-dollar plan。
- Day1 ATR matrix。
- Day2 `k1 × 0.6`。
- Day3 MARKET 執行。
- 累積式執行紀錄與每日核對閘門。
- 同日重跑與重複下單防護。
- Google Sheet 初始化程式。
- GitHub Actions 語法與單元測試流程。
