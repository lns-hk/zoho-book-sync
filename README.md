# Zoho Book Sync

**English** | [简体中文](README.zh-Hans.md) | [正體中文](README.zh-Hant.md) | [日本語](README.ja.md)

Zoho Book Sync is a desktop app for macOS and Windows that exports Zoho Books documents (quotes, invoices and others) as PDF files. It saves them into per-customer folders in a folder of your choice on your computer.

Version: 0.2.0

> Zoho Book Sync is an independent project. It is not made, endorsed or supported by Zoho Corporation. Zoho and Zoho Books are trademarks of Zoho Corporation.

## Background

We work on projects with several partner companies. Every time we issued a quote or an invoice in Zoho Books, someone had to download the PDF by hand and send it to the partner, which took time and was easy to get wrong.

The Zoho Books free plan has no workflow rules or custom functions, so this cannot be automated inside Zoho itself. Zoho Book Sync does the job from the desktop instead:

1. It reads new and changed documents through the Zoho Books API.
2. It downloads each document as a PDF.
3. It saves the PDF into the right customer folder in a local folder of your choice.

Any folder works. If you want partners to receive the files automatically, pick a folder that a sync service such as OneDrive, Google Drive, Dropbox or a NAS already syncs, and share each customer folder with the partner once.

## Features

- **Interface languages:** English, Simplified Chinese, Traditional Chinese and Japanese. It follows your system language by default, and you can switch at any time from the **Language** menu on the Status tab.
- **Document types:** quotes, invoices, credit notes, sales orders and payment receipts. Choose which ones to sync in the settings.
- **Three sync modes:**
  - Sync New: new and changed documents only. Use this day to day.
  - Sync All: the full history.
  - Select: pick documents from a filtered list.
- **Customer folders:**
  - Group several Zoho companies into one folder.
  - Optionally sync only the listed customers.
  - The company list comes from the Zoho contact list and is cached for 24 hours.
- **Changed documents:** by default a changed document is saved as a new version (`_v2.pdf`), so files edited by hand are never overwritten. You can choose to overwrite or skip instead.
- **Auto sync:**
  - Set how often it checks.
  - Start at login and run from the menu bar or system tray.
  - Get notified about new files or errors.
- **API usage:**
  - Detects your Zoho plan automatically.
  - The bottom of the window shows the API calls remaining today and how many this computer has used.
  - The Auto Sync tab shows every limit and how many calls auto sync is expected to use per day.
- **Security:**
  - Tokens are stored only in the app's own folder, not in the system keychain.
  - The app requests read-only access to Zoho.

## Installation

Download from [Releases](../../releases):

| System | File | First launch |
|---|---|---|
| macOS (Apple Silicon) | `ZohoBookSync-mac.zip` | Unzip and move `ZohoBookSync.app` to Applications. The app is not signed by Apple, so the first time you must **right-click → Open**. |
| Windows 10/11 | `ZohoBookSync-windows.zip` | Unzip and run `ZohoBookSync\ZohoBookSync.exe`. When SmartScreen warns you, click **More info → Run anyway**. |

## Usage

### 1. Connect to Zoho (Connect Zoho tab)

Choose one of two methods.

**One-click sign-in (recommended)**

An administrator sets this up once:
1. In the [Zoho API Console](https://api-console.zoho.com), click **Add Client** and choose **Server-based Applications**.
2. Fill in:
   - Homepage URL: any URL, for example `http://127.0.0.1:53682`.
   - Authorized Redirect URIs: `http://127.0.0.1:53682/callback`.
3. Give the Client ID and Client Secret to your colleagues.

Each user enters the Client ID and Secret in the app and clicks **Connect Zoho**. The browser opens Zoho's sign-in page; click **Accept** to finish.

**Manual entry**

1. In the API Console, create a **Self Client**.
2. On the **Generate Code** tab, paste the scope shown in the app (use the **Copy** button) and set Time Duration to 10 minutes.
3. Enter the Client ID, Client Secret and Code in the app, then click **Connect Zoho**.

After connecting:
- Choose your Zoho Books organization.
- Choose to sync only documents from today onwards, or decide later.

### 2. Sync Settings tab

- **Documents to sync:** tick the types to sync.
- **Don't sync these statuses:** for example drafts or void documents.
- **Storage location:** any folder on your computer. By default the app uses a `Zoho Books` folder in OneDrive if OneDrive is installed, otherwise `Documents/Zoho Books`. Click **Choose…** to change it.
- **Folder and file name:** a template such as `{partner}/{type}/{number}.pdf`. Available fields: `{partner}` `{company}` `{customer}` `{type}` `{number}` `{year}` `{month}` `{date}` `{status}`.

Folder names for document types (`Quotes`, `Invoices`, …) stay in English whatever the interface language, so changing the language never moves your files.

### 3. Customer Folders tab

1. Click **Add Customer** and rename the folder.
2. Click **Pick Companies from Zoho…** and tick the companies that belong to this customer.

Companies that are not listed get a folder named after the company. To sync only the listed companies, tick **Only sync the companies listed below**.

### 4. Status tab

- **Sync New:** sync new and changed documents. Use this day to day.
- **Sync All…:** sync the full history.
- **Select…:** pick a date range, then tick the documents to sync.
- **Recent activity:** double-click a row to open the file.
- **Language:** switch the interface language.

### 5. Auto Sync tab

Turn on auto sync, choose how often it checks and, if you like, turn on start at login. When you close the window the app keeps running from the menu bar or system tray.

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
| Settings | `~/Library/Application Support/ZohoBookSync/settings.json` | `%LOCALAPPDATA%\ZohoBookSync\settings.json` |
| Tokens | `~/Library/Application Support/ZohoBookSync/secrets.json` | `%LOCALAPPDATA%\ZohoBookSync\secrets.json` |
| Sync history, API usage, company cache | `~/Library/Application Support/ZohoBookSync/` | `%LOCALAPPDATA%\ZohoBookSync\` |
| Log | `~/Library/Logs/ZohoBookSync/zoho_book_sync.log` | `%LOCALAPPDATA%\ZohoBookSync\Logs\zoho_book_sync.log` |

To remove your sign-in details, click **Disconnect** on the Connect Zoho tab, or delete `secrets.json`.

### Upgrading from 0.1.0 (ZohoSync)

Version 0.2.0 was renamed from ZohoSync and keeps its data in a new `ZohoBookSync` folder, so it starts fresh: connect to Zoho again and set up your folders. Old settings are not migrated. If you had turned on start at login in 0.1.0, turn it off there first (or delete the old app); the old `ZohoSync` folders can then be removed.

## Development

Requires Python 3.11 or later.

```bash
python -m venv ~/.venvs/zoho-book-sync        # keep the venv outside cloud-synced folders
~/.venvs/zoho-book-sync/bin/pip install -r requirements-dev.txt
~/.venvs/zoho-book-sync/bin/python -m pytest tests
~/.venvs/zoho-book-sync/bin/python app.py
```

### Translations

All interface text is in `zoho_sync/i18n.py`: one key per string, with English, Simplified Chinese, Traditional Chinese and Japanese. `tests/test_i18n.py` checks that every key used in the code exists, that all four languages are filled in with matching `{placeholders}`, and that no text is hard-coded outside the catalog.

### Packaging

Run `python build.py` on the target system:

- macOS → `dist-mac/ZohoBookSync-mac.zip` (ad-hoc signed)
- Windows → `dist-windows/ZohoBookSync-windows.zip`

The Windows build and verification log is in [`docs/WINDOWS_BUILD.md`](docs/WINDOWS_BUILD.md).

### Project layout

```
app.py                  Entry point: single instance, logging, language
zoho_sync/i18n.py       Interface text in four languages, language detection
zoho_sync/zoho.py       Zoho OAuth and Books API client (retries, rate limits, usage headers)
zoho_sync/engine.py     Sync engine: list documents, decide what to export, write PDFs safely
zoho_sync/config.py     Settings, tokens, sync history, API usage, company cache
zoho_sync/gui.py        PySide6 interface (five tabs, tray icon, selection and company pickers)
zoho_sync/autostart.py  Start at login (macOS LaunchAgent / Windows Run key)
tests/                  pytest
```
