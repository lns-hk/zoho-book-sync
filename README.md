# ZohoSync

**English** | [正體中文](README.zh-Hant.md)

ZohoSync is a desktop app for macOS and Windows that exports Zoho Books documents (quotes, invoices and others) as PDF files. It files them into per-customer folders inside OneDrive or any other local folder.

Version: 0.1.0

## Background

We work on projects with several partner companies. Every time we issued a quote or an invoice in Zoho Books, someone had to download the PDF by hand and send it to the partner, which took time and was easy to get wrong.

The Zoho Books free plan has no workflow rules or custom functions, so this cannot be automated inside Zoho itself. ZohoSync does the job from the desktop instead:

1. It reads new and changed documents through the Zoho Books API.
2. It downloads each document as a PDF.
3. It saves the PDF into the right customer folder inside a cloud-synced folder such as OneDrive.
4. The cloud client uploads the file.

Share each customer folder with the partner once, and new documents reach them automatically from then on.

## Features

- **Document types:** quotes, invoices, credit notes, sales orders and payment receipts. Choose which ones to sync in the settings.
- **Three sync modes:**
  - Sync new: new and changed documents only. Use this day to day.
  - Sync all: the full history.
  - Select: pick documents from a filtered list.
- **Customer folders:**
  - Group several Zoho companies into one folder.
  - Optionally sync only the listed customers.
  - The company list comes from the Zoho contact list and is cached for 24 hours.
- **Changed documents:** by default a changed document is saved as a new version (`_v2.pdf`), so files edited by hand are never overwritten. You can choose to overwrite or skip instead.
- **Auto-sync:**
  - Set how often it checks.
  - Start at login and run from the menu bar or system tray.
  - Get notified about new files or errors.
- **API usage:**
  - Detects your Zoho plan automatically.
  - The bottom of the window shows the API calls remaining today and how many this computer has used.
  - The Auto Sync tab shows every limit and how many calls auto-sync is expected to use per day.
- **Security:**
  - Tokens are stored only in the app's own folder, not in the system keychain.
  - The app requests read-only access to Zoho.

## Installation

Download from [Releases](../../releases):

| System | File | First launch |
|---|---|---|
| macOS (Apple Silicon) | `ZohoSync-mac.zip` | Unzip and move `ZohoSync.app` to Applications. The app is not signed by Apple, so the first time you must **right-click → Open**. |
| Windows 10/11 | `ZohoSync-windows.zip` | Unzip and run `ZohoSync\ZohoSync.exe`. When SmartScreen warns you, click **More info → Run anyway**. |

The interface is in Traditional Chinese (Cantonese). The tab and button names below are given in Chinese as they appear in the app.

## Usage

### 1. Connect to Zoho (連接 Zoho tab)

Choose one of two methods.

**One-click sign-in (recommended)**

An administrator sets this up once:
1. In the [Zoho API Console](https://api-console.zoho.com), click **Add Client** and choose **Server-based Applications**.
2. Fill in:
   - Homepage URL: any URL, for example `http://127.0.0.1:53682`.
   - Authorized Redirect URIs: `http://127.0.0.1:53682/callback`.
3. Give the Client ID and Client Secret to your colleagues.

Each user enters the Client ID and Secret in the app and clicks **連接 Zoho**. The browser opens Zoho's sign-in page; click **Accept** to finish.

**Manual entry**

1. In the API Console, create a **Self Client**.
2. On the **Generate Code** tab, paste the scope shown in the app (use the **複製** button) and set Time Duration to 10 minutes.
3. Enter the Client ID, Client Secret and Code in the app, then click **連接 Zoho**.

After connecting:
- Choose your Zoho Books organization.
- Choose to sync only documents from today onwards, or decide later.

### 2. Settings (同步設定 tab)

- **Document types:** tick the types to sync.
- **Skipped statuses:** for example drafts or void documents.
- **Storage location:** by default a `Zoho Books` folder inside OneDrive. Click **選擇…** to change it.
- **Folder and file name:** a template such as `{partner}/{type}/{number}.pdf`. Available fields: `{partner}` `{company}` `{customer}` `{type}` `{number}` `{year}` `{month}` `{date}` `{status}`.

### 3. Customer folders (客戶資料夾 tab)

1. Click **新增客戶** (add customer) and rename the folder.
2. Click **由 Zoho 揀公司…** (pick companies from Zoho) and tick the companies that belong to this customer.

Companies that are not listed get a folder named after the company. To sync only the listed companies, tick **只同步下面列出嘅公司**.

### 4. Sync (狀態 tab)

- **同步新單:** sync new and changed documents. Use this day to day.
- **全部同步…:** sync the full history.
- **自選同步…:** pick a date range, then tick the documents to sync.
- **Recent activity:** double-click a row to open the file.

### 5. Auto-sync (自動同步 tab)

Turn on auto-sync, choose how often it checks and, if you like, turn on start at login. When you close the window the app keeps running from the menu bar or system tray.

### API limits

The Zoho Books daily API limit is **shared by the whole Zoho organization**, including colleagues' computers and other integrations:

| Plan | Calls per day |
|---|---|
| Free | 1,000 |
| Standard | 2,000 |
| Professional | 5,000 |
| Premium / Elite / Ultimate | 10,000 |

The app reads the `X-Rate-Limit-*` headers on every Zoho response to show the live remaining count. Each auto-sync check uses about one API call per document type.

## File locations

| Purpose | macOS | Windows |
|---|---|---|
| Settings | `~/Library/Application Support/ZohoSync/settings.json` | `%LOCALAPPDATA%\ZohoSync\settings.json` |
| Tokens | `~/Library/Application Support/ZohoSync/secrets.json` | `%LOCALAPPDATA%\ZohoSync\secrets.json` |
| Sync history, API usage, company cache | `~/Library/Application Support/ZohoSync/` | `%LOCALAPPDATA%\ZohoSync\` |
| Log | `~/Library/Logs/ZohoSync/zoho_sync.log` | `%LOCALAPPDATA%\ZohoSync\Logs\zoho_sync.log` |

To remove your sign-in details, click **中斷連接** (disconnect) on the 連接 Zoho tab, or delete `secrets.json`.

## Development

Requires Python 3.11 or later.

```bash
python -m venv ~/.venvs/zoho-sync        # keep the venv outside cloud-synced folders
~/.venvs/zoho-sync/bin/pip install -r requirements-dev.txt
~/.venvs/zoho-sync/bin/python -m pytest tests
~/.venvs/zoho-sync/bin/python app.py
```

### Packaging

Run `python build.py` on the target system:

- macOS → `dist-mac/ZohoSync-mac.zip` (ad-hoc signed)
- Windows → `dist-windows/ZohoSync-windows.zip`

The Windows build and verification log is in [`docs/WINDOWS_BUILD.md`](docs/WINDOWS_BUILD.md).

### Project layout

```
app.py                  Entry point: single instance, logging
zoho_sync/zoho.py       Zoho OAuth and Books API client (retries, rate limits, usage headers)
zoho_sync/engine.py     Sync engine: list documents, decide what to export, write PDFs safely
zoho_sync/config.py     Settings, tokens, sync history, API usage, company cache
zoho_sync/gui.py        PySide6 interface (five tabs, tray icon, selection and company pickers)
zoho_sync/autostart.py  Start at login (macOS LaunchAgent / Windows Run key)
tests/                  pytest
```
