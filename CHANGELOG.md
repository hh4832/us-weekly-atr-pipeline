# Changelog

所有重要修改都記錄在這裡。版本原則使用 Semantic Versioning。

## [Unreleased]

- 待實際走完一週 Day1–Day3 後補上修正。
- 部分成交 `filled_shares` 邏輯尚未實作。

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
