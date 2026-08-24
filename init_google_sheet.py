from __future__ import annotations

import os

from dotenv import load_dotenv

from google_sheets_store import GoogleSheetsStore


def main() -> None:
    load_dotenv()
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    store = GoogleSheetsStore(sheet_id)
    store.ensure_schema()
    print("初始化完成：已保留原工作表，並建立程式專用工作表。")


if __name__ == "__main__":
    main()

