# Git / GitHub 建立步驟

這個目錄就是新 repo 的根目錄。不要再外包一層舊版 app 目錄。

## 1. 解壓後確認敏感檔案

下列檔案不得出現在 `git status`：

- `.env`
- `service_account.json`
- `*.pfx`
- `.venv/`

`.gitignore` 已排除這些檔案。

## 2. 本機初始化

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Initial Google Sheets ATR pipeline"
git tag -a v0.1.0 -m "First testable Google Sheets pipeline"
```

`git add .` 後必須先看 `git status`，確認憑證沒有被加入。

## 3. 建立 GitHub repository

建議 repo 名稱：

```text
us-weekly-atr-pipeline
```

在 GitHub 建立空 repo 後，不要再勾選產生 README 或 `.gitignore`，然後執行：

```powershell
git remote add origin https://github.com/<YOUR_ACCOUNT>/us-weekly-atr-pipeline.git
git push -u origin main
git push origin v0.1.0
```

## 4. Branch 規則

- `main`：只保留可執行版。
- 新功能：從 `main` 建立 `feature/<name>`。
- 修正：使用 `fix/<name>`。
- 舊版 `app_v2.02.py` 不放進 `main`；保留在原來的備份位置即可。

## 5. Commit 範例

```text
feat: support partial fills
fix: prevent same-day stage advancement
fix: preserve manually entered filled prices
docs: clarify Google service account setup
test: add Day3 reconciliation cases
```

## 6. GitHub Actions

`.github/workflows/tests.yml` 會在 push 與 pull request 時：

1. 安裝 Python 3.12。
2. 安裝 `requirements.txt`。
3. 檢查 Python 語法。
4. 執行狀態機測試。

這個 workflow 不會連 Google Sheet、不會抓行情，也不會產生或送出真實訂單。

## 7. 何時升級 v1.0.0

必須先實際完成至少一週：

- Day1 產生與核對
- Day2 只出現未成交標的
- Day3 MARKET 完成
- 真實成交價沒有被程式覆寫
- 同日重跑不會重複產生訂單

全部通過後再建立 `v1.0.0`。

