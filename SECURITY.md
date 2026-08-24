# Security

## 不得提交的資料

- Google service-account JSON
- `.env`
- 富邦憑證或 PFX
- 券商帳號、密碼、OTP
- 含完整財務資料的除錯 log

## 洩漏處理

如果憑證曾被 commit，只從最新 commit 刪除並不足夠。應立即在 Google Cloud 停用原 key、產生新 key，再清理 Git 歷史。

