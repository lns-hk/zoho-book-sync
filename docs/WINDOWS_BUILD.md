# ZohoSync — Windows build report

Date: 2026-11-07 · Machine: Windows 11 Pro 10.0.26200 (x64, 3440×1440)
Build dir (outside Synology Drive): `C:\AI\Project\zoho-sync-build` (robocopy of source, excluding dist/build/__pycache__/.venv)

## Toolchain
| | Version |
|---|---|
| Python | 3.12.10 (64-bit, python.org, via `py -3.12`) |
| PySide6 | 6.12.0 |
| PyInstaller | 6.22.3 |
| keyring | 25.7.0 (backend `WinVaultKeyring` = Windows Credential Manager) |
| platformdirs / Pillow / pytest | 4.14.5 / 13.0.0 / 9.2.0 |

## Tests
`python -m pytest tests` → **9 passed** (0.09 s)

## What I verified
**From source (`python app.py`)**
- The main window opens with the title `Zoho 同步 0.1.0`, and the tray icon (green "Z") appears in the notification area's overflow (^) list.
- Closing the window hides it to the tray, and the process keeps running.
- A second `python app.py` exits straight away (exit 0), and the first instance's window becomes visible again (see Known issues about foreground focus).
- keyring: set, get and delete with throwaway service `ZohoSync-test` all worked. After the delete, `get` returns `None`, so nothing is left behind.
- autostart: `set_enabled(True)` writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ZohoSync`. From source the value is `"…\.venv\Scripts\python.exe" "…\app.py" "--background"`. `set_enabled(False)` removes it, and calling it again when it's already gone is a no-op. I confirmed the value is not present afterwards.

**Packaged (`python build.py`)**
- `dist\ZohoSync-windows.zip` built with no errors.
- `ZohoSync.exe` has PE subsystem 2 (GUI), and no console window or conhost child process appeared.
- The window opens, and Traditional Chinese renders correctly in the tabs, labels, radio buttons and tray menu (screenshot checked).
- The tray icon is present. Its right-click menu shows 開啟 Zoho 同步 / 立即同步新單 / 開啟資料夾 / 暫停自動同步 / 結束.
- A second `ZohoSync.exe` exits with code 0, only one ZohoSync process stays running, and the hidden window is shown again.
- **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left).
- No Run key and no `settings.json` were written. I didn't change any settings, and the only thing created was `%LOCALAPPDATA%\ZohoSync\Logs`.
- I did not connect to Zoho and did not enter any credentials.

## Source changes
- `app.py`: on win32 only, the second instance now calls `user32.AllowSetForegroundWindow(ASFW_ANY)` before it sends "show" to the running copy. Windows' focus-stealing lock otherwise stops the running copy's `activateWindow()` from coming to the front: the window was shown, but behind other windows, with only a flashing taskbar button. The call is guarded by `sys.platform == "win32"` and uses only `ctypes`, so it doesn't affect macOS.

`build.py` regenerates `ZohoSync.spec` and `assets/icon.png` in the build copy. I did not copy those generated files back, so the synced folder keeps the Mac versions.

## Output
- `dist-windows\ZohoSync-windows.zip`: **52,229,066 bytes (≈ 49.8 MB)**. Unzipped `ZohoSync\` folder ≈ 124 MB.
- SHA-256: `ddee34e622639ad17dc339e4497b3e372b66a405f89ec99f1fadaf3bdaef5ec9`
- Not code-signed. SmartScreen will warn on first run (其他資訊 → 仍要執行).

## Known issues / notes
1. **Foreground on second launch is not fully verified.** My tests launched the second instance from a background shell, which doesn't own the foreground. Windows therefore still refused the focus change: the window became visible but stayed behind the active app. When a user double-clicks the exe or Start-menu shortcut, the new process does own the foreground, and that's the case the `AllowSetForegroundWindow` fix targets. Please confirm by hand: open the app, put another window in front, then double-click `ZohoSync.exe` again.
2. The tray icon starts in the Windows 11 overflow (^) list, as all new tray icons do. Users can drag it onto the taskbar.
3. The bundle still contains Qt6Qml / Qt6Quick DLLs (~12 MB) and `opengl32sw.dll` (20 MB). The `--exclude-module` flags only drop Python modules, not DLLs that PySide6 hooks pull in. This only affects size, not function.
4. Running from source with autostart on registers `python.exe`, which opens a console at login. The packaged exe registers `ZohoSync.exe --background`, which is correct. This is a dev-mode detail only.
5. 暫停自動同步 shows as ticked on a fresh install because `auto_sync` defaults to off. This is by design.

## Rebuild 2 — 2026-11-07 (Connect tab GUI change from Mac)
Change picked up: `zoho_sync/gui.py`. The 連接 Zoho help text is now selectable, and a read-only field with a 複製 button shows the Scope (手動輸入) or the Redirect URI (一撳登入).
Same procedure and toolchain as above: robocopy into `C:\AI\Project\zoho-sync-build` (same exclusions), reused the existing venv.

- `python -m pytest tests` → **9 passed** (0.13 s).
- `python build.py` → built with no errors.
- I drove packaged `ZohoSync.exe` with Windows UI Automation and screenshots:
  - **Window width does not change when switching modes.** The window stays at 860×620 in 一撳登入, in 手動輸入, and after switching back. The long Scope string is cut off inside its field, and the field does not widen the window.
  - **複製 works.** In 手動輸入 the clipboard got the full Scope string (`ZohoBooks.estimates.READ,…,ZohoBooks.settings.READ`). In 一撳登入 it got `http://127.0.0.1:53682/callback`.
  - The Code row shows only in 手動輸入, and the help text with the API Console link renders correctly in both modes.
  - **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left).
- No Run key and no `settings.json` were written. I did not connect to Zoho or enter any credentials. No source changes were needed.

Output: `dist-windows\ZohoSync-windows.zip` is **49,731,176 bytes (≈ 47.4 MB)** and the unzipped folder is ≈ 117 MB. This replaces the earlier zip (SHA-256 `ddee34e6…`).
SHA-256: `a746d634e2ac716e5092f85614979df2b6308861d5b48689e327a73a699fc68f`

## Rebuild 3 — 2026-11-07 (自選同步 checkboxes + 客戶資料夾 rename from Mac)
Changes picked up from `zoho_sync/gui.py`:
- The 自選同步 `SelectDialog` now puts a real `QCheckBox` cell widget in column 0 of each row, instead of using checkable `QTableWidgetItem`s.
- The "Partner" tab is renamed 客戶資料夾, and its labels now say 客戶.

Same procedure and toolchain as above: robocopy into `C:\AI\Project\zoho-sync-build` (same exclusions), reused the existing venv.

- `python -m pytest tests` → **9 passed** (0.14 s).
- `python build.py` → built with no errors.
- **Packaged `ZohoSync.exe`**, checked with Windows UI Automation and a screenshot:
  - The tabs read 狀態 | 連接 Zoho | 同步設定 | **客戶資料夾** | 自動同步.
  - The 客戶資料夾 tab renders the help text (每個客戶一個資料夾…), the placeholder 客戶資料夾名, and the buttons **新增客戶** / 刪除 / 由 Zoho 揀公司…. Traditional Chinese renders correctly. I did not click 新增客戶, so no settings were changed.
  - **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left).
- **Selection dialog, run from source in the venv with fake docs** (Zoho can't be reached here). I built `SelectDialog(config.Settings(), {"docs": {...}})`, called `.fill()` with 5 `engine.Doc`s (estimate, 2 invoices, sales order, credit note; one marked as already synced), then called `.check_visible(True)`:
  - **Alignment:** there is exactly one checkbox per row. Each checkbox's centre falls inside its own row (row pitch 30 px, checkbox centre 13 px down from the row top in every row).
  - **全選顯示中 ticks every row:** `.selection()` returned all 5 keys.
  - **With a filter:** I typed `INV` in the search box, which hides 3 rows. 全選顯示中 then ticked only the 2 visible rows, and `.selection()` returned only `invoices:2` and `invoices:3`.
  - Screenshot check: the native windows11-style checkbox shows a tick in every row, the ✓ in the 已同步 column renders, and the columns line up.
  - Note for anyone repeating this test: Qt's windows11 style animates the tick in. A `grab()` taken right after `setChecked()` shows filled boxes without the tick, so wait about 1 s before grabbing. This is a test-timing detail, not a bug.
- No Run key and no `settings.json` were written. I did not connect to Zoho or enter any credentials. No source changes were needed.

Output: `dist-windows\ZohoSync-windows.zip` is **49,729,951 bytes (≈ 47.4 MB)** and the unzipped folder is ≈ 117 MB. This replaces the Rebuild 2 zip (SHA-256 `a746d634…`).
SHA-256: `aec95393c5c2d8b79f3bc3d505056f9123b47038cc6445451e5ff29f143fc3d7`

## Rebuild 4 — 2026-11-07 (secrets moved from keyring to secrets.json, from Mac)
Changes picked up:
- `zoho_sync/config.py` stores `client_secret` and `refresh_token` only in `%LOCALAPPDATA%\ZohoSync\secrets.json` (the config dir). It no longer uses keyring or Windows Credential Manager.
- `keyring` is removed from `requirements.txt`.
- New `tests/test_config.py`. Its POSIX permission test is skipped on Windows.

Same procedure and toolchain as above (minus keyring): robocopy into `C:\AI\Project\zoho-sync-build` (same exclusions), reused the existing venv.

- **Venv cleanup:** `pip uninstall -y keyring` removed keyring 25.7.0. I also removed its now-orphaned dependencies `jaraco.classes`, `jaraco.context`, `jaraco.functools` and `more-itertools` (`pip show` listed nothing that required them). I kept `pywin32-ctypes` because PyInstaller requires it. `pip install -r requirements-dev.txt` did not pull keyring back in, and `pip check` is clean.
- `python -m pytest tests` → **11 passed, 1 skipped** (0.04 s). The skipped test is `test_secrets_file_is_user_only` (POSIX mode bits).
- `python build.py` → built with no errors.
- **No keyring in the bundle.** Searching `dist\ZohoSync` for `*keyring*` / `*jaraco*` finds 0 files, and the zip has 0 matching entries. The PyInstaller PYZ TOC and `warn-ZohoSync.txt` (in `%TEMP%\zohosync-build`) have 0 `keyring`/`jaraco` hits. Pure-Python modules live inside the PYZ archive, so the file search alone wouldn't prove this.
- **Packaged `ZohoSync.exe`** opens the `Zoho 同步 0.1.0` window. Its tray icon appears in the overflow as `Zoho 同步 — 上次同步 未有`. **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left). I drove this with Windows UI Automation.
- **Secrets, run from source** with `config.CONFIG_DIR` / `config.SECRETS_FILE` pointed at a temp dir, so real app data was not touched:
  - `set_secret("x", "y")` created `secrets.json` in the config dir, containing `{"x": "y"}`. `get_secret("x")` returned `"y"`, and no `secrets.tmp` was left over.
  - `set_secret("x", "")` deleted `secrets.json` again and left the dir empty.
  - On Windows `os.chmod(0o600)` only controls the read-only attribute. The file is not marked read-only, so later writes via `os.replace` still work, and the Windows run of the roundtrip test also covers this.
- **Who can read the file:** Windows ignores the `0o600` mode, so the file gets the ACL it inherits from its folder. I checked with `icacls`:
  - The real target folder `%LOCALAPPDATA%\ZohoSync` (and `%LOCALAPPDATA%` itself) grants only `NT AUTHORITY\SYSTEM:(F)`, `BUILTIN\Administrators:(F)` and `<PC>\<user>:(F)`, all inherited. The temp-dir test file showed SYSTEM / Administrators / OWNER RIGHTS, all inherited.
  - **Result: other standard users cannot read secrets.json, but local administrators and SYSTEM can.** It is stored as plain JSON, so unlike Credential Manager (DPAPI) the tokens are also readable from a backup or disk image of the profile. This is the intended design ("no OS keychain"), noted here only so the trade-off is on record. If stricter protection is ever wanted on Windows, the options are an explicit user-only DACL (removing Administrators) or DPAPI `CryptProtectData`.
- No Run key and no `settings.json` / `secrets.json` were written under the real `%LOCALAPPDATA%\ZohoSync`; it still only has `Logs`. I did not connect to Zoho or enter any credentials. No source changes were needed.

Output: `dist-windows\ZohoSync-windows.zip` is **47,859,946 bytes (≈ 45.6 MB)** and the unzipped folder is ≈ 115 MB. It is about 1.9 MB smaller than Rebuild 3 because keyring and its dependencies are gone. This replaces the Rebuild 3 zip (SHA-256 `aec95393…`).
SHA-256: `523e9f4b5f658c82f0a4538482dd0b8b2b39899caa1ef0e6628eacff57b3de60`

## Rebuild 5 — 2026-11-07 (由 Zoho 揀公司… `CompanyPicker` dialog, from Mac)
Changes picked up:
- New `gui.CompanyPicker` dialog, opened from 客戶資料夾 → 由 Zoho 揀公司…. It opens instantly and shows an animated busy bar while it loads company names from Zoho contacts (`engine.list_companies`).
- The names are cached for 24 h in the data dir (`config.load_companies` / `save_companies` → `companies.json`).
- Each row has a real `QCheckBox` (`setItemWidget`), and there is a search box.
- Companies that belong to another 客戶 are labelled （已屬：X）, and the dialog asks for confirmation before moving them.

Same procedure and toolchain as above: robocopy into `C:\AI\Project\zoho-sync-build` (same exclusions), reused the existing venv.

- `python -m pytest tests` → **13 passed, 1 skipped** (0.05 s). The skipped test is the POSIX permission test, as before.
- `python build.py` → built with no errors.
- **CompanyPicker, run from source in the venv without Zoho.** I pointed `config.CONFIG_DIR` / `DATA_DIR` / `COMPANIES_FILE` (plus `SETTINGS_FILE` / `STATE_FILE` / `SECRETS_FILE`) at a temp dir and called `config.save_companies("o", [6 names])`. The names included two CJK ones. I then built `Settings(org_id="o", partners=[Partner("客戶 A", ["Acme Ltd"]), Partner("客戶 B", ["Beta Trading", "Echo Holdings"])])` and opened `gui.CompanyPicker(settings, 1)`. Results, checked about 1.2 s after opening (windows11 tick animation) with `grab()` screenshots:
  - **Loaded from the cache, so no network call was made.** The status line reads `共 6 間公司 （已暫存，撳「重新載入」可以即時更新）` and the busy bar is hidden.
  - **Alignment:** there are 6 rows with exactly one checkbox each. Each checkbox's geometry matches its row rect exactly (rows are 24 px tall at y = 0, 24, 48 …), and every checkbox has the same left edge (x = 6). The screenshot shows the native ticks lined up.
  - **Ticks:** Beta Trading and Echo Holdings (owned by 客戶 B) are ticked, and nothing else is. `chosen()` returned `['Beta Trading', 'Echo Holdings']`.
  - **The A-owned company is labelled:** `Acme Ltd　（已屬：客戶 A）` (unticked). Traditional Chinese renders correctly.
  - **Search:** typing `trad` leaves only `Beta Trading` visible.
  - **Busy state:** after `dlg.set_busy(True, "讀取緊 Zoho 客戶名冊…")`, the indeterminate bar (range 0–0) is visible. The text shows, and OK, 重新載入 and the list are disabled, while 取消 stays enabled. Two screenshots taken 400 ms apart show the bar segment in different positions, so it is animating.
  - **Confirmation before moving:** I ticked Acme Ltd and called `accept()` with `QMessageBox.question` stubbed to answer No. The dialog asked `以下公司已經屬於其他客戶，確定搬去「客戶 B」？\n\n客戶 A：Acme Ltd`. After the No it stayed open and was not accepted.
  - The only file written to the temp dir was `companies.json`.
- **Packaged `ZohoSync.exe`**, checked with Windows UI Automation and a screenshot:
  - It starts and shows the `Zoho 同步 0.1.0` window.
  - The 客戶資料夾 tab renders: the 只同步下面列出嘅公司 checkbox, the help text, 資料夾名 / 包括嘅 Zoho 公司（每行一間）, and the buttons 新增客戶 / 刪除 / **由 Zoho 揀公司…**. I did not open the picker in the exe, because with no cache it would try to reach Zoho.
  - The tray icon is `Zoho 同步 — 上次同步 未有`. Its menu shows 開啟 Zoho 同步 / 立即同步新單 / 開啟資料夾 / 暫停自動同步 / 結束.
  - **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left).
  - Testing tip: the tray button's UIA name has a leading space (` Zoho 同步 — …`), so match it with a wildcard.
- No Run key and no `settings.json` / `secrets.json` / `companies.json` were written under the real `%LOCALAPPDATA%\ZohoSync`; it still only has `Logs`. I did not connect to Zoho or enter any credentials. No source changes were needed.

Output: `dist-windows\ZohoSync-windows.zip` is **47,863,262 bytes (≈ 45.6 MB)** and the unzipped folder is ≈ 115 MB. This replaces the Rebuild 4 zip (SHA-256 `523e9f4b…`).
SHA-256: `c6fff4fa5deaba0e6efcad271bc9af01fc7d4181ab2c940ce80b3263b40cdca7`

## Rebuild 6 — 2026-11-07 (Zoho API usage counter, from Mac)
Changes picked up:
- `zoho_sync/zoho.py` parses Zoho's `X-Rate-Limit-*` response headers (`parse_rate_headers`, `plan_daily_limit`), and `BooksClient` takes an `observer` that is told about every call. A new `quota_probe` makes one cheap call to read the headers.
- `zoho_sync/config.py` adds the `plan_name` setting and `quota.json` in the data dir (`load_quota` / `save_quota` / `apply_api_call`). `local_used` resets at local midnight; `limit` / `remaining` come from Zoho and are shared by the whole org.
- `zoho_sync/gui.py`:
  - a permanent bottom status-bar counter: `Zoho <plan> 方案 ｜ 今日 API 剩餘 x / y（HH:MM 重設）｜ 本機今日已用 n 次`
  - a "Zoho API 使用上限" group on the 自動同步 tab, with a 立即更新（用 1 次 API） button
  - the plan is read on connect
  - the first column of the 狀態 table is renamed 同步時間

Same procedure and toolchain as above: robocopy into `C:\AI\Project\zoho-sync-build` (same exclusions), reused the existing venv.

- `python -m pytest tests` → **16 passed, 1 skipped** (0.07 s). The skipped test is the POSIX permission test, as before.
- `python build.py` → built with no errors.
- **Run from source in the venv, without Zoho.** I pointed `config.CONFIG_DIR` / `DATA_DIR` and every `*_FILE` (settings, state, companies, quota, secrets) at a temp dir. I then wrote `config.save_quota({"date": today, "local_used": 5, "limit": 1000, "remaining": 786, "reset_at": <tonight 00:00>, "per_minute": 150, "updated_at": now})` and `Settings(plan_name="FREE", auto_sync=True, interval_min=10).save()`, and opened `gui.MainWindow()` on the 自動同步 tab. Results from `grab()` screenshots and widget values:
  - The window is the default **860×620**.
  - **Status bar:** it reads `Zoho FREE 方案　｜　今日 API 剩餘 786 / 1,000（00:00 重設）　｜　本機今日已用 5 次`. The label is 477 px wide and its sizeHint is also 477 px, inside an 860 px status bar, so **nothing is cut off on Windows and no fix was needed**. Traditional Chinese renders correctly.
  - **Zoho API 使用上限 group:**

    | Field | Shows |
    |---|---|
    | Zoho 方案 | FREE |
    | 每日上限 | 1,000 次（成個 Zoho 機構共用） |
    | 每分鐘上限 | 150 次 |
    | 今日剩餘 | 786 / 1,000（23:29 更新） |
    | 重設時間 | 00:00 |
    | 本機今日已用 | 5 次 |
    | 自動同步預計 | 每 10 分鐘 × 2 種文件 ≈ 每日 288 次（約佔每日上限 28%） |

    The 立即更新（用 1 次 API） button and the grey hint text render, and no row is cut off. Settings are not "connected", so no automatic quota refresh fired and no network call was made.
  - The 狀態 table's first header is `同步時間`.
  - The only files written to the temp dir were `quota.json` and `settings.json`.
  - My test script ended with `os._exit(0)`, and Qt logged an access violation during that forced teardown, after all checks and screenshots were done. This is a harness artefact; the app's own exit was checked in the packaged exe.
- **Packaged `ZohoSync.exe`**, checked with Windows UI Automation and a screenshot:
  - It starts and shows the `Zoho 同步 0.1.0` window at 860×620.
  - **The 狀態 tab headers are 同步時間 | 類型 | 單號 | 公司 | 結果 | 檔案.**
  - **The bottom counter is visible.** On a fresh profile it reads `Zoho 未知 方案　｜　今日 API 剩餘 —　｜　本機今日已用 0 次` and fits at the right of the status bar.
  - The tray icon is ` Zoho 同步 — 上次同步 未有`. **Clicking 結束 in the tray menu quits the app** (no ZohoSync process left).
  - Testing tip: the taskbar button's name also contains `Zoho 同步`, so match the tray icon with `*Zoho 同步 —*`. If a UIA script has Chinese literals, save it as UTF-8 **with BOM**; otherwise Windows PowerShell 5.1 reads it as ANSI.
- No Run key was written. Under the real `%LOCALAPPDATA%\ZohoSync` there is no `settings.json` / `secrets.json` / `quota.json`. It has only `Logs`, which now holds an empty `zoho_sync.log` created by the existing log handler in `app.py`. I did not connect to Zoho or enter any credentials. No source changes were needed.

Output: `dist-windows\ZohoSync-windows.zip` is **47,870,228 bytes (≈ 45.7 MB)** and the unzipped folder is ≈ 115 MB. This replaces the Rebuild 5 zip (SHA-256 `c6fff4fa…`).
SHA-256: `fab82e9c0e7a52d79de86fa233fc0fd57c83753f79645861019df5cf67f56941`

## 0.2.0 build — 2026-11-08 (renamed to Zoho Book Sync, 4-language UI, from Mac)
Changes picked up:
- The app/exe name is now **ZohoBookSync**. `build.py` outputs `dist-windows\ZohoBookSync\ZohoBookSync.exe` and `dist-windows\ZohoBookSync-windows.zip`. The config dir is `%LOCALAPPDATA%\ZohoBookSync`, and the autostart Run value is `ZohoBookSync`.
- New `zoho_sync/i18n.py` covers English / 简体中文 / 正體中文 / 日本語. By default the UI follows the OS language (`QLocale.system().uiLanguages()`). A 語言/Language combo on the Status tab switches language live by rebuilding the UI. `gui.apply_language` also loads Qt's `qtbase_*.qm` so standard dialog buttons are translated.
- Engine outcomes are now codes, which the GUI translates.

Procedure: I deleted everything in `C:\AI\Project\zoho-sync-build` except `.venv`, so old files such as `ZohoSync.spec`, `dist\` and the root-level `WINDOWS_BUILD.md` can't linger. I then robocopied the source in (excluding `dist`, `dist-mac`, `dist-windows`, `build`, `__pycache__`, `.venv`, `.git`) and reused the venv. Toolchain is unchanged: Python 3.12.10, PySide6 6.12.0, PyInstaller 6.22.3, platformdirs 4.14.5. `pip install -r requirements-dev.txt` installed nothing new, and `pip check` is clean.

- `python -m pytest tests` → **235 passed, 1 skipped** (0.22 s). The skipped test is the POSIX permission test, as before.
- `python build.py` → built with no errors into `dist-windows\`. **The Qt translations are bundled:** `_internal\PySide6\translations\` holds 99 `.qm` files, including `qtbase_en`, `qtbase_zh_CN`, `qtbase_zh_TW` and `qtbase_ja`. PyInstaller's PySide6 hook collects them, so `build.py` needed no change.
- **Packaged `ZohoBookSync.exe`**, driven with Windows UI Automation and `PrintWindow` screenshots (OS UI language is 繁體中文 (香港)):
  1. **It starts.** The window title is **`Zoho Book Sync 0.2.0`** and the size is 860×620. On first run it follows the system language, so it opens in 正體中文, and the combo's first entry reads 跟隨系統（正體中文）.
  2. **Language switching:** I selected English → 简体中文 → 正體中文 → 日本語 in the Status-tab combo and screenshotted all 5 tabs in each language (20 screenshots). Every switch rebuilt the UI live: tab names went Status/Connect Zoho/Sync Settings/Customer Folders/Auto Sync → 状态/连接 Zoho/同步设置/客户文件夹/自动同步 → 狀態/連接 Zoho/同步設定/客戶資料夾/自動同步 → ステータス/Zoho 接続/同期設定/顧客フォルダ/自動同期. The window title stayed `Zoho Book Sync 0.2.0`. Simplified, Traditional and Japanese text (including kana) render with Windows' CJK fonts, and nothing is clipped at the default 860 px width. That covers the tabs, group boxes, radio/check boxes, form labels, the wrapped help texts, the buttons, the Zoho API group, and the bottom status-bar counter (e.g. `Zoho 不明 プラン ｜ 本日の API 残り — ｜ このコンピュータ本日 0 回`, whose last character sits just left of the size grip but is fully visible). In English the counter ends with the bare number (`This computer today: 0`); that is the English wording, not clipping.
  3. **Qt's own strings are translated.** In 日本語 I clicked Zoho 接続 → 接続を解除. The standard `QMessageBox.question` titled 接続を解除 asked 接続を解除しますか？同期済みのファイルは削除されません。 with buttons **はい(Y) / いいえ(N)**, which shows `qtbase_ja.qm` is bundled and found via `QLibraryInfo` in the frozen app. I answered いいえ, so nothing was disconnected or written.
  4. **The tray menu is translated.** In 日本語 the menu shows Zoho Book Sync を開く / 今すぐ新規を同期 / フォルダを開く / 自動同期を一時停止 / 終了, and the tooltip is `Zoho Book Sync — 前回の同期 未実行`. **Clicking 終了 quits the app** (no ZohoBookSync process left).
  5. **`%LOCALAPPDATA%\ZohoBookSync` is used.** It created `Logs\zoho_book_sync.log`, and the language choice was saved to `%LOCALAPPDATA%\ZohoBookSync\settings.json`. I deleted that test `settings.json` afterwards, so the next first run follows the OS language again. Nothing new was written to the old `%LOCALAPPDATA%\ZohoSync`. No `ZohoBookSync` (or `ZohoSync`) Run value exists.
- I did not connect to Zoho or enter any credentials. **No source changes were needed.**

Testing tips:
- Qt's `QComboBox` popup ignores UIA `SelectionItemPattern.Select()`. The item looks selected, but `currentIndexChanged` never fires. To switch language, focus the combo, `Expand()` it, then send `{HOME}`, `{DOWN}`×n and `{ENTER}`.
- Win11's overflow tray button name is `<InitialTooltip> <current tooltip>`. Windows caches the tooltip from the first launch, so after a language switch it reads `Zoho Book Sync — 上次同步 尚未同步 Zoho Book Sync — 前回の同期 未実行`. The tray `QMenu` is a top-level window of class `QMenu`; poll for it right after the right-click.
- At 9 pt, 纟 and 糸 look the same in screenshots (结果 vs 結果), so a zh-Hans label like `组织` can look Traditional. The strings are correct Simplified codepoints (U+7EC4 U+7EC7).

Notes:
- **No migration from the old name.** 0.2.0 does not read `%LOCALAPPDATA%\ZohoSync`. A user upgrading from 0.1.0 starts unconfigured and has to reconnect to Zoho and redo their settings, or copy `settings.json` / `secrets.json` / `state.json` / `quota.json` across by hand. An old `ZohoSync` Run value (if autostart was on) is not removed and would still launch the old exe. The old and new apps use different single-instance keys, so both can run side by side (seen during this test: a 0.1.0 `ZohoSync.exe` from Downloads kept running alongside). This isn't Windows-specific, so I left the code as is.
- Unsigned as before (SmartScreen: 其他資訊 → 仍要執行).

Output: `dist-windows\ZohoBookSync-windows.zip` is **50,390,922 bytes (≈ 48.1 MB)**, 230 entries, and the unzipped `ZohoBookSync\` folder is ≈ 121 MB. It replaces `ZohoSync-windows.zip` (Rebuild 6, SHA-256 `fab82e9c…`). I deleted that zip and the old `dist-windows\ZohoSync\` folder.
SHA-256: `98696b1367786a272c8a24a33d3e21cc602f32067595f47d897c564ad27505df`
