# Upgrade to v0.1.2

此版將「Day1/Day2 成交價高於程式參考限價」改為二次確認警告，不再完全阻擋。

## 更新 GitHub

將壓縮檔內的檔案覆蓋到原本的 Git 專案後，在 PowerShell 執行：

```powershell
git status
git add app.py trading_engine.py tests/test_trading_engine.py README.md CHANGELOG.md VERSION UPGRADE_v0.1.2.md
git commit -m "fix: require second confirmation for fills above reference limit"
git push origin main
git tag -a v0.1.2 -m "Warn instead of blocking fills above reference limit"
git push origin v0.1.2
```

Streamlit Community Cloud 會在 `main` 更新後自動重新部署。原本的 Google Sheet 與 Secrets 不需重建。

## 新流程

1. 在 Google Sheet 填入真實成交價。
2. 勾選 FT 核對方塊並按「完成今日核對」。
3. 若成交價高於程式參考限價，畫面顯示警告，當日尚未確認。
4. 再次核對後勾選第二個方塊，按「仍要完成今日核對」即可繼續。

成交價非數字、成交價小於等於零，以及 Day3 仍有空白成交價，依然會強制阻擋。
