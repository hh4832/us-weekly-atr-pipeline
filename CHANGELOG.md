# Changelog

所有重要修改都記錄在這裡。版本原則使用 Semantic Versioning。

## [Unreleased]

- 待實際走完一週 Day1–Day3 後補上修正。
- 部分成交 `filled_shares` 邏輯尚未實作。

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

