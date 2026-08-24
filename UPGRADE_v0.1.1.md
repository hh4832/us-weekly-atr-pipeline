# Upgrade from v0.1.0 to v0.1.1

## 核心改動

- Day1：固定 LIMIT
- Day2：固定 LIMIT，`k = Day1 k × 0.6`
- Day3：固定 MARKET

程式不再依據產生訂單時的 reference price，提前把 Day1/Day2 改成 MARKET。

## 你目前正在進行的 TEST plan

舊版已經產生的 Day1/Day2 列不會被自動回改。建議：

1. 測試計畫可直接刪除後，用新 Plan ID 重建。
2. 真實計畫不要刪除；保留原始記錄，並從下一個新 plan 開始使用 v0.1.1。

## 更新 Git

將 v0.1.1 檔案覆蓋到原 repo，但不要覆蓋或刪除：

- `.env`
- `service_account.json`
- `.venv/`

然後執行：

```powershell
git status
git add .
git commit -m "fix: use limit orders on Day1 and Day2"
git tag -a v0.1.1 -m "Use LIMIT on Day1 and Day2"
```

如果 `v0.1.0` 已存在，不需要刪除；它是舊版歷史標記。
