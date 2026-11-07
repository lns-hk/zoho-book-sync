# Zoho Book Sync

[English](README.md) | [简体中文](README.zh-Hans.md) | **正體中文** | [日本語](README.ja.md)

Zoho Book Sync 是一款適用於 macOS 及 Windows 的桌面應用程式，可將 Zoho Books 的報價單、發票等文件匯出為 PDF，並依客戶分類存放於 OneDrive 或任何本機資料夾。

版本：0.2.0

> Zoho Book Sync 為獨立項目，並非由 Zoho Corporation 開發、認可或提供支援。Zoho 及 Zoho Books 為 Zoho Corporation 的商標。

## 背景

我們與多間合作公司共同執行項目。過往每開立一張報價單或發票，都須在 Zoho Books 手動下載 PDF，再逐份寄送予合作公司，既費時亦容易出錯。

Zoho Books 免費方案不提供 Workflow 及 Custom Function，無法在 Zoho 內自動化此流程。因此我們開發了這款桌面應用程式，流程如下：

1. 透過 Zoho Books API 讀取新開立或已修改的文件。
2. 將文件下載為 PDF。
3. 存放至 OneDrive 等雲端同步資料夾內對應的客戶資料夾。
4. 由雲端用戶端自動上傳。

只需將各客戶資料夾分享予合作公司一次，此後新文件便會自動送達。

## 功能

- **介面語言：** 英文、簡體中文、正體中文、日文。預設跟隨系統語言，亦可隨時在「狀態」分頁的「語言」選單切換。
- **文件類型：** 報價單、發票、退款單、銷售訂單、收款收據，可於設定中自行選擇。
- **三種同步方式：**
  - 同步新文件：只同步新開立及已修改的文件，供日常使用。
  - 全部同步：同步全部歷史文件。
  - 自選同步：從經篩選的清單中勾選文件。
- **客戶資料夾：**
  - 可將多間 Zoho 公司歸入同一資料夾。
  - 可設定只同步已列出的客戶。
  - 公司名單取自 Zoho 客戶名冊，並暫存 24 小時。
- **文件修改後：** 預設另存新版本（`_v2.pdf`），不會覆蓋經人手修改的檔案；亦可改為覆蓋或略過。
- **自動同步：**
  - 可設定檢查頻率。
  - 可於開機時自動啟動，並在選單列或系統匣執行。
  - 有新檔案或發生錯誤時發出通知。
- **API 用量：**
  - 自動偵測 Zoho 方案。
  - 視窗底部顯示今日 API 剩餘次數及本機用量。
  - 「自動同步」分頁顯示各項上限，以及自動同步預計每日使用的次數。
- **保安：**
  - 權杖只儲存於應用程式自身的資料夾，不使用系統鑰匙圈。
  - 只要求 Zoho 的唯讀權限。

## 安裝

請從 [Releases](../../releases) 下載：

| 系統 | 檔案 | 首次開啟 |
|---|---|---|
| macOS（Apple Silicon） | `ZohoBookSync-mac.zip` | 解壓縮後將 `ZohoBookSync.app` 移至「應用程式」。由於未經 Apple 簽署，首次開啟須按**右鍵 → 打開**。 |
| Windows 10/11 | `ZohoBookSync-windows.zip` | 解壓縮後執行 `ZohoBookSync\ZohoBookSync.exe`。如出現 SmartScreen 警告，請按**其他資訊 → 仍要執行**。 |

## 使用方法

### 1. 連接 Zoho（「連接 Zoho」分頁）

以下兩種方式擇一使用。

**一鍵登入（建議）**

須由管理員先完成一次設定：
1. 在 [Zoho API Console](https://api-console.zoho.com) 按 **Add Client**，選擇 **Server-based Applications**。
2. 填寫以下資料：
   - Homepage URL：任何網址均可，例如 `http://127.0.0.1:53682`。
   - Authorized Redirect URIs：`http://127.0.0.1:53682/callback`。
3. 將 Client ID 及 Client Secret 提供予同事。

使用者在應用程式輸入 Client ID 及 Secret 後按「連接 Zoho」，瀏覽器會開啟 Zoho 登入頁面，按 **Accept** 即完成。

**手動輸入**

1. 在 API Console 建立 **Self Client**。
2. 於 **Generate Code** 分頁貼上應用程式顯示的 Scope（可按「複製」），Time Duration 選擇 10 minutes。
3. 在應用程式輸入 Client ID、Client Secret 及 Code，然後按「連接 Zoho」。

連接成功後：
- 選擇 Zoho Books 機構。
- 選擇只同步今日起的新文件，或稍後再決定。

### 2.「同步設定」分頁

- **同步的文件類型：** 勾選要同步的類型。
- **不同步以下狀態：** 例如草稿、作廢。
- **儲存位置：** 預設為 OneDrive 內的 `Zoho Books` 資料夾，可按「選擇…」更改。
- **資料夾及檔名：** 以範本設定，例如 `{partner}/{type}/{number}.pdf`。可用欄位：`{partner}` `{company}` `{customer}` `{type}` `{number}` `{year}` `{month}` `{date}` `{status}`。

文件類型資料夾名稱（`Quotes`、`Invoices` 等）不論介面語言均維持英文，因此切換語言不會移動任何檔案。

### 3.「客戶資料夾」分頁

1. 按「新增客戶」，並修改資料夾名稱。
2. 按「從 Zoho 選擇公司…」，勾選屬於此客戶的公司。

未列出的公司會以其公司名稱建立資料夾。如只需同步已列出的公司，請勾選「只同步下方列出的公司」。

### 4.「狀態」分頁

- **同步新文件：** 同步新開立及已修改的文件，供日常使用。
- **全部同步…：** 同步全部歷史文件。
- **自選同步…：** 選擇日期範圍後勾選文件。
- **最近紀錄：** 按兩下可開啟檔案。
- **語言：** 切換介面語言。

### 5.「自動同步」分頁

開啟自動同步並設定檢查頻率，如有需要可開啟「開機時自動啟動」。關閉視窗後，程式會繼續於選單列或系統匣執行。

### API 使用上限

Zoho Books 的每日 API 上限由**整個 Zoho 機構共用**，包括同事的電腦及其他整合服務：

| 方案 | 每日上限 |
|---|---|
| Free | 1,000 |
| Standard | 2,000 |
| Professional | 5,000 |
| Premium / Elite / Ultimate | 10,000 |

應用程式會讀取 Zoho 每次回應中的 `X-Rate-Limit-*` 資料，以顯示即時剩餘次數。每次自動檢查，每種文件類型約使用一次 API。

## 檔案位置

| 用途 | macOS | Windows |
|---|---|---|
| 設定 | `~/Library/Application Support/ZohoBookSync/settings.json` | `%LOCALAPPDATA%\ZohoBookSync\settings.json` |
| 權杖 | `~/Library/Application Support/ZohoBookSync/secrets.json` | `%LOCALAPPDATA%\ZohoBookSync\secrets.json` |
| 同步紀錄、API 用量、公司暫存 | `~/Library/Application Support/ZohoBookSync/` | `%LOCALAPPDATA%\ZohoBookSync\` |
| 記錄檔 | `~/Library/Logs/ZohoBookSync/zoho_book_sync.log` | `%LOCALAPPDATA%\ZohoBookSync\Logs\zoho_book_sync.log` |

如需清除登入資料，可在「連接 Zoho」分頁按「中斷連接」，或直接刪除 `secrets.json`。

### 由 0.1.0（ZohoSync）升級

0.2.0 由 ZohoSync 更名而來，資料改存於新的 `ZohoBookSync` 資料夾，因此會以全新狀態啟動：請重新連接 Zoho 並設定客戶資料夾，舊設定不會轉移。如曾於 0.1.0 開啟開機自動啟動，請先在舊版關閉（或刪除舊版應用程式），之後即可刪除舊的 `ZohoSync` 資料夾。

## 開發

須使用 Python 3.11 或以上版本。

```bash
python -m venv ~/.venvs/zoho-book-sync        # 虛擬環境請勿放在雲端同步資料夾內
~/.venvs/zoho-book-sync/bin/pip install -r requirements-dev.txt
~/.venvs/zoho-book-sync/bin/python -m pytest tests
~/.venvs/zoho-book-sync/bin/python app.py
```

### 翻譯

所有介面文字均存放於 `zoho_sync/i18n.py`：每段文字一個鍵，附英文、簡體中文、正體中文及日文。`tests/test_i18n.py` 會檢查程式中使用的每個鍵均存在、四種語言均已填寫且 `{placeholders}` 一致，以及目錄以外沒有寫死的文字。

### 打包

在目標系統執行 `python build.py`：

- macOS → `dist-mac/ZohoBookSync-mac.zip`（ad-hoc 簽署）
- Windows → `dist-windows/ZohoBookSync-windows.zip`

Windows 打包及驗證紀錄見 [`docs/WINDOWS_BUILD.md`](docs/WINDOWS_BUILD.md)。

### 項目結構

```
app.py                  進入點：單一實例、記錄、語言
zoho_sync/i18n.py       四種語言的介面文字、語言偵測
zoho_sync/zoho.py       Zoho OAuth 及 Books API 用戶端（重試、限速、讀取 API 用量）
zoho_sync/engine.py     同步引擎：列出文件、決定匯出項目、安全寫入 PDF
zoho_sync/config.py     設定、權杖、同步紀錄、API 用量、公司暫存
zoho_sync/gui.py        PySide6 介面（五個分頁、系統匣、自選同步及選擇公司視窗）
zoho_sync/autostart.py  開機啟動（macOS LaunchAgent / Windows Run key）
tests/                  pytest
```
