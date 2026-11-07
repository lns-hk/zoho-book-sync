"""UI translations: English, Simplified Chinese, Traditional Chinese, Japanese.

tr("key", name=value) looks up the current language and formats {placeholders}.
Every key has all four languages; tests/test_i18n.py enforces this and that every
tr() call in the code uses a known key.
"""
from __future__ import annotations

LANGUAGES = {  # code -> name shown in the language menu (always in its own language)
    "en": "English",
    "zh-Hans": "简体中文",
    "zh-Hant": "正體中文",
    "ja": "日本語",
}
QT_LOCALES = {"en": "en", "zh-Hans": "zh_CN", "zh-Hant": "zh_TW", "ja": "ja"}

_current = "en"


def detect(ui_languages: list[str]) -> str:
    """Pick a supported language from the OS preference list (e.g. QLocale.system().uiLanguages())."""
    for tag in ui_languages:
        t = tag.replace("_", "-").lower()
        if t.startswith("zh"):
            return "zh-Hant" if any(x in t for x in ("hant", "-tw", "-hk", "-mo")) else "zh-Hans"
        if t.startswith("ja"):
            return "ja"
        if t.startswith("en"):
            return "en"
    return "en"


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else "en"


def current() -> str:
    return _current


def tr(key: str, default: str | None = None, **kw) -> str:
    row = CATALOG.get(key)
    if row is None:
        text = key if default is None else default
    else:
        text = row[_INDEX[_current]] or row[0]
    return text.format(**kw) if kw else text


_INDEX = {"en": 0, "zh-Hans": 1, "zh-Hant": 2, "ja": 3}

# key: (English, 简体中文, 正體中文, 日本語)
CATALOG: dict[str, tuple[str, str, str, str]] = {
    # ---- app / window
    "app.name": ("Zoho Book Sync", "Zoho Book Sync", "Zoho Book Sync", "Zoho Book Sync"),
    "tab.status": ("Status", "状态", "狀態", "ステータス"),
    "tab.connect": ("Connect Zoho", "连接 Zoho", "連接 Zoho", "Zoho 接続"),
    "tab.sync": ("Sync Settings", "同步设置", "同步設定", "同期設定"),
    "tab.customers": ("Customer Folders", "客户文件夹", "客戶資料夾", "顧客フォルダ"),
    "tab.auto": ("Auto Sync", "自动同步", "自動同步", "自動同期"),
    "language": ("Language", "语言", "語言", "言語"),
    "language.system": ("System ({name})", "跟随系统（{name}）", "跟隨系統（{name}）", "システム（{name}）"),
    "common.cancel": ("Cancel", "取消", "取消", "キャンセル"),
    "common.unknown": ("Unknown", "未知", "未知", "不明"),
    "common.calls": ("{n} calls", "{n} 次", "{n} 次", "{n} 回"),

    # ---- document types / statuses / outcomes
    "doctype.estimates": ("Quote", "报价单", "報價單", "見積書"),
    "doctype.invoices": ("Invoice", "发票", "發票", "請求書"),
    "doctype.creditnotes": ("Credit Note", "退款单", "退款單", "クレジットノート"),
    "doctype.salesorders": ("Sales Order", "销售订单", "銷售訂單", "受注書"),
    "doctype.customerpayments": ("Payment Receipt", "收款收据", "收款收據", "入金領収書"),
    "status.draft": ("Draft", "草稿", "草稿", "下書き"),
    "status.sent": ("Sent", "已发送", "已發送", "送信済み"),
    "status.accepted": ("Accepted", "已接受", "已接受", "承認済み"),
    "status.declined": ("Declined", "已拒绝", "已拒絕", "辞退"),
    "status.expired": ("Expired", "已过期", "已過期", "期限切れ"),
    "status.invoiced": ("Invoiced", "已开发票", "已開立發票", "請求済み"),
    "status.paid": ("Paid", "已付款", "已付款", "支払済み"),
    "status.partially_paid": ("Partially paid", "部分付款", "部分付款", "一部支払済み"),
    "status.overdue": ("Overdue", "逾期", "逾期", "期限超過"),
    "status.void": ("Void", "作废", "作廢", "無効"),
    "status.open": ("Open", "未结", "未結", "未完了"),
    "status.closed": ("Closed", "已结", "已結", "完了"),
    "status.unpaid": ("Unpaid", "未付款", "未付款", "未払い"),
    "status.approved": ("Approved", "已批准", "已核准", "承認済み"),
    "status.pending_approval": ("Pending approval", "待批准", "待核准", "承認待ち"),
    "status.confirmed": ("Confirmed", "已确认", "已確認", "確定済み"),
    "status.fulfilled": ("Fulfilled", "已完成", "已完成", "履行済み"),
    "outcome.created": ("Created", "已创建", "已建立", "作成"),
    "outcome.overwritten": ("Overwritten", "已覆盖", "已覆蓋", "上書き"),
    "outcome.new_version": ("New version", "新版本", "新版本", "新しい版"),
    "outcome.skipped": ("Skipped", "已跳过", "已略過", "スキップ"),
    "outcome.unchanged": ("Unchanged", "无变化", "無變更", "変更なし"),
    "outcome.failed": ("Failed: {error}", "失败：{error}", "失敗：{error}", "失敗：{error}"),

    # ---- data centres
    "dc.com": ("United States / Hong Kong (zoho.com)", "美国 / 香港 (zoho.com)", "美國／香港 (zoho.com)", "米国／香港 (zoho.com)"),
    "dc.eu": ("Europe (zoho.eu)", "欧洲 (zoho.eu)", "歐洲 (zoho.eu)", "欧州 (zoho.eu)"),
    "dc.in": ("India (zoho.in)", "印度 (zoho.in)", "印度 (zoho.in)", "インド (zoho.in)"),
    "dc.com.au": ("Australia (zoho.com.au)", "澳大利亚 (zoho.com.au)", "澳洲 (zoho.com.au)", "オーストラリア (zoho.com.au)"),
    "dc.jp": ("Japan (zoho.jp)", "日本 (zoho.jp)", "日本 (zoho.jp)", "日本 (zoho.jp)"),
    "dc.ca": ("Canada (zohocloud.ca)", "加拿大 (zohocloud.ca)", "加拿大 (zohocloud.ca)", "カナダ (zohocloud.ca)"),
    "dc.sa": ("Saudi Arabia (zoho.sa)", "沙特阿拉伯 (zoho.sa)", "沙烏地阿拉伯 (zoho.sa)", "サウジアラビア (zoho.sa)"),
    "dc.com.cn": ("China (zoho.com.cn)", "中国 (zoho.com.cn)", "中國 (zoho.com.cn)", "中国 (zoho.com.cn)"),

    # ---- status tab
    "status.connected": ("✅ Connected: <b>{org}</b>", "✅ 已连接：<b>{org}</b>", "✅ 已連接：<b>{org}</b>", "✅ 接続済み：<b>{org}</b>"),
    "status.not_connected": ("⚠️ <b>Not connected to Zoho</b>", "⚠️ <b>未连接 Zoho</b>", "⚠️ <b>尚未連接 Zoho</b>", "⚠️ <b>Zoho に未接続</b>"),
    "status.every_min": ("every {n} min", "每 {n} 分钟", "每 {n} 分鐘", "{n} 分ごと"),
    "status.off": ("Off", "关闭", "關閉", "オフ"),
    "status.never": ("Never", "尚未同步", "尚未同步", "未実行"),
    "status.none_selected": ("(none selected)", "（未选择）", "（未選擇）", "（未選択）"),
    "status.list_sep": (", ", "、", "、", "、"),
    "status.summary": (
        "{conn}<br>Storage location: {root}<br>Document types: {types}<br>Auto sync: {auto}　|　Last sync: {last}",
        "{conn}<br>保存位置：{root}<br>同步类型：{types}<br>自动同步：{auto}　｜　上次同步：{last}",
        "{conn}<br>儲存位置：{root}<br>同步類型：{types}<br>自動同步：{auto}　｜　上次同步：{last}",
        "{conn}<br>保存先：{root}<br>同期する書類：{types}<br>自動同期：{auto}　｜　前回の同期：{last}"),
    "status.tray_tip": ("{app} — last sync {last}", "{app} — 上次同步 {last}", "{app} — 上次同步 {last}", "{app} — 前回の同期 {last}"),
    "btn.sync_new": ("Sync New", "同步新单", "同步新文件", "新規を同期"),
    "btn.sync_new.tip": ("Sync new and changed documents (use this day to day)", "同步新开或已修改的单据（日常使用）",
                         "同步新開立或已修改的文件（日常使用）", "新規・変更された書類を同期します（通常はこちら）"),
    "btn.sync_all": ("Sync All…", "全部同步…", "全部同步…", "すべて同期…"),
    "btn.sync_all.tip": ("Sync the full history as well", "连同历史单据一起同步", "連同歷史文件一併同步", "過去の書類もすべて同期します"),
    "btn.sync_select": ("Select…", "自选同步…", "自選同步…", "選んで同期…"),
    "btn.stop": ("Stop", "停止", "停止", "停止"),
    "btn.open_folder": ("Open Folder", "打开文件夹", "開啟資料夾", "フォルダを開く"),
    "status.recent": ("Recent activity (double-click to open the file)", "最近记录（双击打开文件）",
                      "最近紀錄（按兩下開啟檔案）", "最近の履歴（ダブルクリックでファイルを開く）"),
    "col.sync_time": ("Synced at", "同步时间", "同步時間", "同期日時"),
    "col.type": ("Type", "类型", "類型", "種類"),
    "col.number": ("Number", "单号", "單號", "番号"),
    "col.date": ("Date", "日期", "日期", "日付"),
    "col.company": ("Company", "公司", "公司", "会社"),
    "col.status": ("Status", "状态", "狀態", "ステータス"),
    "col.synced": ("Synced", "已同步", "已同步", "同期済み"),
    "col.result": ("Result", "结果", "結果", "結果"),
    "col.file": ("File", "文件", "檔案", "ファイル"),

    # ---- connect tab
    "conn.method": ("Connection method", "连接方式", "連接方式", "接続方法"),
    "conn.browser": ("One-click sign-in (sign in to Zoho in your browser; recommended)",
                     "一键登录（在浏览器登录 Zoho，推荐）", "一鍵登入（於瀏覽器登入 Zoho，建議）",
                     "ワンクリックサインイン（ブラウザで Zoho にサインイン・推奨）"),
    "conn.manual": ("Manual entry (Self Client: Client ID / Secret / Code)", "手动输入（Self Client：Client ID / Secret / Code）",
                    "手動輸入（Self Client：Client ID / Secret / Code）", "手動入力（Self Client：Client ID / Secret / Code）"),
    "conn.region": ("Zoho region", "Zoho 区域", "Zoho 地區", "Zoho リージョン"),
    "conn.code_hint": ("1000.xxxx (valid for 10 minutes)", "1000.xxxx（10 分钟内有效）", "1000.xxxx（10 分鐘內有效）",
                       "1000.xxxx（有効期限 10 分）"),
    "conn.copy": ("Copy", "复制", "複製", "コピー"),
    "conn.copied": ("Copied {what}", "已复制 {what}", "已複製 {what}", "{what} をコピーしました"),
    "conn.connect": ("Connect Zoho", "连接 Zoho", "連接 Zoho", "Zoho に接続"),
    "conn.disconnect": ("Disconnect", "断开连接", "中斷連接", "接続を解除"),
    "conn.org": ("Zoho Books organization", "Zoho Books 组织", "Zoho Books 機構", "Zoho Books 組織"),
    "conn.help.manual": (
        "1. Go to <a href='{console}'>Zoho API Console</a> → Self Client and note the Client ID and Secret.<br>"
        "2. On the Generate Code tab, paste the scope below (click “Copy”).<br>"
        "3. Set Time Duration to 10 minutes, click Create, paste the Code above, then click “Connect Zoho”.",
        "1. 前往 <a href='{console}'>Zoho API Console</a> → Self Client，记下 Client ID 和 Secret。<br>"
        "2. 在 Generate Code 页签，将下方的 Scope 贴上（点击“复制”）。<br>"
        "3. Time Duration 选择 10 minutes，点击 Create，将 Code 贴到上方，再点击“连接 Zoho”。",
        "1. 前往 <a href='{console}'>Zoho API Console</a> → Self Client，記下 Client ID 及 Secret。<br>"
        "2. 於 Generate Code 分頁貼上下方的 Scope（按「複製」）。<br>"
        "3. Time Duration 選擇 10 minutes，按 Create，將 Code 貼於上方，再按「連接 Zoho」。",
        "1. <a href='{console}'>Zoho API Console</a> → Self Client を開き、Client ID と Secret を控えます。<br>"
        "2. Generate Code タブに下の Scope を貼り付けます（「コピー」をクリック）。<br>"
        "3. Time Duration を 10 minutes にして Create をクリックし、Code を上に貼り付けて「Zoho に接続」をクリックします。"),
    "conn.help.browser": (
        "Enter the Client ID and Secret from your IT team and click “Connect Zoho”. Your browser opens the Zoho sign-in page; click “Accept” to finish.<br>"
        "IT setup (once): in <a href='{console}'>API Console</a> → Add Client → <b>Server-based Applications</b>; "
        "Homepage URL can be anything (e.g. http://127.0.0.1:53682); set Authorized Redirect URIs to the value below (click “Copy”).",
        "填入公司 IT 提供的 Client ID 和 Secret，点击“连接 Zoho”，浏览器会打开 Zoho 登录页，点击“Accept”即完成。<br>"
        "IT 设置（只需一次）：在 <a href='{console}'>API Console</a> → Add Client → <b>Server-based Applications</b>；"
        "Homepage URL 可随意填写（例如 http://127.0.0.1:53682）；Authorized Redirect URIs 填写下方的值（点击“复制”）。",
        "填入公司 IT 提供的 Client ID 及 Secret，按「連接 Zoho」，瀏覽器會開啟 Zoho 登入頁面，按「Accept」即完成。<br>"
        "IT 設定（只需一次）：於 <a href='{console}'>API Console</a> → Add Client → <b>Server-based Applications</b>；"
        "Homepage URL 可任意填寫（例如 http://127.0.0.1:53682）；Authorized Redirect URIs 填寫下方的值（按「複製」）。",
        "IT 担当から受け取った Client ID と Secret を入力し、「Zoho に接続」をクリックします。ブラウザで Zoho のサインインページが開くので、「Accept」をクリックすれば完了です。<br>"
        "IT 側の設定（初回のみ）：<a href='{console}'>API Console</a> → Add Client → <b>Server-based Applications</b>。"
        "Homepage URL は任意（例：http://127.0.0.1:53682）、Authorized Redirect URIs には下の値を入力します（「コピー」をクリック）。"),
    "conn.missing.title": ("Missing details", "资料未填齐", "資料未填妥", "未入力の項目があります"),
    "conn.missing.body": ("Please fill in the Client ID and Client Secret.", "请填写 Client ID 和 Client Secret。",
                          "請填寫 Client ID 及 Client Secret。", "Client ID と Client Secret を入力してください。"),
    "conn.missing.body_code": ("Please fill in the Client ID, Client Secret and Code.", "请填写 Client ID、Client Secret 和 Code。",
                               "請填寫 Client ID、Client Secret 及 Code。", "Client ID、Client Secret、Code を入力してください。"),
    "conn.connecting": ("Connecting…", "连接中…", "連接中…", "接続しています…"),
    "conn.connecting_browser": ("Connecting… Sign in to Zoho in your browser and click Accept.",
                                "连接中…请在浏览器登录 Zoho 并点击 Accept。", "連接中…請於瀏覽器登入 Zoho 並按 Accept。",
                                "接続しています…ブラウザで Zoho にサインインし、Accept をクリックしてください。"),
    "conn.no_org": ("Signed in, but this account has no Zoho Books organization.", "已登录，但此账户没有 Zoho Books 组织。",
                    "已登入，但此帳戶沒有 Zoho Books 機構。", "サインインしましたが、このアカウントには Zoho Books の組織がありません。"),
    "conn.ok": ("✅ Connected: {org}", "✅ 连接成功：{org}", "✅ 連接成功：{org}", "✅ 接続しました：{org}"),
    "conn.ok_many": (" (several organizations — choose one above)", "（有多个组织，请在上方选择）",
                     "（有多個機構，請於上方選擇）", "（複数の組織があります。上で選択してください）"),
    "conn.first.title": ("Where should syncing start?", "从什么时候开始同步？", "從何時開始同步？", "どこから同期しますか？"),
    "conn.first.body": ("First use: what should happen to documents already in Zoho?", "首次使用：如何处理 Zoho 中已有的旧单据？",
                        "首次使用：如何處理 Zoho 中已有的舊文件？", "初回利用：Zoho にある既存の書類をどうしますか？"),
    "conn.first.today": ("Only sync new documents from today", "只同步今天之后的新单据", "只同步今日起的新文件", "今日以降の新しい書類のみ同期"),
    "conn.first.later": ("Decide later (Sync All / Select)", "稍后自行选择（全部同步 / 自选同步）",
                         "稍後自行選擇（全部同步／自選同步）", "後で決める（すべて同期／選んで同期）"),
    "conn.disc.title": ("Disconnect", "断开连接", "中斷連接", "接続を解除"),
    "conn.disc.body": ("Disconnect? Files already synced will not be deleted.", "确定断开连接？已同步的文件不会被删除。",
                       "確定中斷連接？已同步的檔案不會被刪除。", "接続を解除しますか？同期済みのファイルは削除されません。"),
    "conn.disc.done": ("Disconnected.", "已断开连接。", "已中斷連接。", "接続を解除しました。"),
    "err.not_connected": ("Not connected to Zoho. Set it up on the “Connect Zoho” tab first.",
                          "未连接 Zoho，请先在“连接 Zoho”页设置。", "尚未連接 Zoho，請先於「連接 Zoho」分頁設定。",
                          "Zoho に接続されていません。先に「Zoho 接続」タブで設定してください。"),

    # ---- sync settings tab
    "sync.types": ("Documents to sync", "同步哪些单据", "同步的文件類型", "同期する書類"),
    "sync.skip": ("Don't sync these statuses", "不同步以下状态", "不同步以下狀態", "次のステータスは同期しない"),
    "sync.since": ("Only sync new documents dated on or after", "只同步此日期或之后的新单据", "只同步此日期或之後的新文件",
                   "この日付以降の新しい書類のみ同期"),
    "sync.start_date": ("Start date", "开始日期", "開始日期", "開始日"),
    "sync.browse": ("Choose…", "选择…", "選擇…", "選択…"),
    "sync.storage": ("Storage location", "保存位置", "儲存位置", "保存先"),
    "sync.storage.pick": ("Choose storage location", "选择保存位置", "選擇儲存位置", "保存先を選択"),
    "sync.template": ("Folder and file name", "文件夹和文件名", "資料夾及檔名", "フォルダとファイル名"),
    "sync.template.help": (
        "Fields: {partner} customer folder  {company} company  {customer} contact  {type} document type  "
        "{number} number  {year} year  {month} month  {date} date  {status} status",
        "可用字段：{partner} 客户文件夹  {company} 公司  {customer} 联系人  {type} 单据类型  "
        "{number} 单号  {year} 年  {month} 月  {date} 日期  {status} 状态",
        "可用欄位：{partner} 客戶資料夾  {company} 公司  {customer} 聯絡人  {type} 文件類型  "
        "{number} 單號  {year} 年  {month} 月  {date} 日期  {status} 狀態",
        "使用できる項目：{partner} 顧客フォルダ  {company} 会社  {customer} 担当者  {type} 書類の種類  "
        "{number} 番号  {year} 年  {month} 月  {date} 日付  {status} ステータス"),
    "sync.example": ("Example", "示例", "範例", "例"),
    "sync.template.error": ("Invalid template: {error}", "格式有误：{error}", "格式錯誤：{error}", "形式が正しくありません：{error}"),
    "sync.conflict": ("When a document changes in Zoho", "Zoho 修改了单据时", "Zoho 文件經修改時", "Zoho で書類が変更されたとき"),
    "sync.conflict.version": ("Save a new version (e.g. INV001_v2.pdf, keep the old file; recommended)",
                              "另存新版本（例如 INV001_v2.pdf，保留旧文件，推荐）",
                              "另存新版本（例如 INV001_v2.pdf，保留舊檔，建議）",
                              "新しい版として保存（例：INV001_v2.pdf、古いファイルは残す・推奨）"),
    "sync.conflict.overwrite": ("Overwrite the old file", "直接覆盖旧文件", "直接覆蓋舊檔", "古いファイルを上書き"),
    "sync.conflict.skip": ("Don't update existing files", "已有文件则不更新", "已有檔案則不更新", "既存のファイルは更新しない"),

    # ---- customer folders tab
    "cust.only": ("Only sync the companies listed below (skip all other customers)", "只同步下面列出的公司（其他客户不同步）",
                  "只同步下方列出的公司（其他客戶不同步）", "下に登録した会社のみ同期（その他の顧客は同期しない）"),
    "cust.help": ("One folder per customer; several Zoho companies can share a folder. Companies not listed get a folder named after the company.",
                  "每个客户一个文件夹，可将多间 Zoho 公司放入同一个客户文件夹。未列出的公司会以公司名建立文件夹。",
                  "每個客戶一個資料夾，可將多間 Zoho 公司歸入同一客戶資料夾。未列出的公司會以其公司名稱建立資料夾。",
                  "顧客ごとに 1 つのフォルダを作ります。複数の Zoho の会社を同じフォルダにまとめられます。登録されていない会社は会社名のフォルダになります。"),
    "cust.add": ("Add Customer", "新增客户", "新增客戶", "顧客を追加"),
    "cust.delete": ("Delete", "删除", "刪除", "削除"),
    "cust.name_hint": ("Customer folder name", "客户文件夹名称", "客戶資料夾名稱", "顧客フォルダ名"),
    "cust.folder_name": ("Folder name", "文件夹名称", "資料夾名稱", "フォルダ名"),
    "cust.companies": ("Zoho companies included (one per line)", "包含的 Zoho 公司（每行一间）",
                       "包含的 Zoho 公司（每行一間）", "含める Zoho の会社（1 行に 1 社）"),
    "cust.pick": ("Pick Companies from Zoho…", "从 Zoho 选择公司…", "從 Zoho 選擇公司…", "Zoho から会社を選択…"),
    "cust.item": ("{name} ({n})", "{name}（{n} 间）", "{name}（{n} 間）", "{name}（{n} 社）"),
    "cust.default_name": ("Customer {n}", "客户 {n}", "客戶 {n}", "顧客 {n}"),
    "cust.not_connected.title": ("Not connected", "未连接", "尚未連接", "未接続"),
    "cust.not_connected.body": ("Please connect on the “Connect Zoho” tab first.", "请先在“连接 Zoho”页连接。",
                                "請先於「連接 Zoho」分頁連接。", "先に「Zoho 接続」タブで接続してください。"),

    # ---- company picker
    "pick.title": ("Pick Companies", "选择公司", "選擇公司", "会社を選択"),
    "pick.search": ("Search companies…", "搜索公司…", "搜尋公司…", "会社を検索…"),
    "pick.reload": ("Reload", "重新载入", "重新載入", "再読み込み"),
    "pick.cached": ("(cached; click “Reload” to refresh now)", "（已缓存，点击“重新载入”可立即更新）",
                    "（已暫存，按「重新載入」可立即更新）", "（キャッシュ済み。「再読み込み」ですぐ更新できます）"),
    "pick.fresh": ("(just loaded from Zoho)", "（刚从 Zoho 读取）", "（剛從 Zoho 讀取）", "（Zoho から読み込みました）"),
    "pick.loading": ("Loading the Zoho customer list…", "正在读取 Zoho 客户名册…", "正在讀取 Zoho 客戶名冊…", "Zoho の顧客一覧を読み込んでいます…"),
    "pick.failed": ("❌ Failed to load: {error}", "❌ 载入失败：{error}", "❌ 載入失敗：{error}", "❌ 読み込みに失敗しました：{error}"),
    "pick.owned": ("　(belongs to: {owner})", "　（已属于：{owner}）", "　（已屬於：{owner}）", "　（所属：{owner}）"),
    "pick.count": ("{n} companies {note}", "共 {n} 间公司 {note}", "共 {n} 間公司 {note}", "{n} 社 {note}"),
    "pick.move.title": ("Move companies", "移动公司", "移動公司", "会社の移動"),
    "pick.move.body": ("These companies already belong to another customer. Move them to “{target}”?\n\n{moves}",
                       "以下公司已属于其他客户，确定移到“{target}”？\n\n{moves}",
                       "以下公司已屬於其他客戶，確定移至「{target}」？\n\n{moves}",
                       "次の会社はすでに別の顧客に属しています。「{target}」に移動しますか？\n\n{moves}"),

    # ---- selection dialog
    "sel.title": ("Select Documents to Sync", "自选同步", "自選同步", "選んで同期"),
    "sel.all_types": ("All enabled types", "所有已启用类型", "所有已啟用類型", "有効なすべての種類"),
    "sel.load": ("Load", "载入", "載入", "読み込む"),
    "sel.type": ("Type", "类型", "類型", "種類"),
    "sel.from": ("From", "日期从", "日期由", "期間"),
    "sel.to": ("to", "至", "至", "〜"),
    "sel.search": ("Search number / company…", "搜索单号 / 公司…", "搜尋單號／公司…", "番号／会社を検索…"),
    "sel.only_new": ("Only show unsynced", "只显示未同步", "只顯示未同步", "未同期のみ表示"),
    "sel.check_visible": ("Select Visible", "全选显示中", "全選顯示項目", "表示中をすべて選択"),
    "sel.uncheck_all": ("Clear All", "全部取消", "全部取消", "すべて解除"),
    "sel.hint": ("Choose a date range and click “Load”.", "选好日期范围，点击“载入”。", "選擇日期範圍後按「載入」。",
                 "期間を選んで「読み込む」をクリックしてください。"),
    "sel.ok": ("Sync Selected", "同步已选", "同步已選項目", "選択項目を同期"),
    "sel.loading": ("Loading…", "载入中…", "載入中…", "読み込んでいます…"),
    "sel.failed": ("Failed to load: {error}", "载入失败：{error}", "載入失敗：{error}", "読み込みに失敗しました：{error}"),
    "sel.count": ("{n} documents. Tick the ones to sync, or double-click a row.", "共 {n} 张。勾选要同步的单据，或双击一行。",
                  "共 {n} 張。勾選要同步的文件，或按兩下一列。", "{n} 件。同期する書類にチェックを入れるか、行をダブルクリックしてください。"),

    # ---- auto sync tab / quota
    "auto.enable": ("Turn on auto sync (new and changed documents only)", "开启自动同步（只同步新单和已修改的单据）",
                    "開啟自動同步（只同步新文件及已修改的文件）", "自動同期をオンにする（新規・変更された書類のみ）"),
    "auto.interval": ("Check every", "检查频率", "檢查頻率", "確認間隔"),
    "auto.minutes": (" min", " 分钟", " 分鐘", " 分"),
    "auto.login": ("Start at login (run in the background)", "开机自动启动（在后台运行）", "開機時自動啟動（於背景執行）",
                   "ログイン時に起動（バックグラウンドで実行）"),
    "auto.notify": ("Notify me about new files or errors", "有新文件或出错时通知我", "有新檔案或發生錯誤時通知我",
                    "新しいファイルやエラーを通知する"),
    "auto.note": ("Closing the window keeps the app running in the menu bar / system tray.", "关闭窗口后程序会继续在菜单栏 / 系统托盘运行。",
                  "關閉視窗後，程式會繼續於選單列／系統匣執行。", "ウインドウを閉じても、アプリはメニューバー／システムトレイで動作し続けます。"),
    "auto.login_failed.title": ("Setting failed", "设置失败", "設定失敗", "設定に失敗しました"),
    "auto.login_failed.body": ("Could not set start at login: {error}", "开机启动设置失败：{error}", "開機啟動設定失敗：{error}",
                               "ログイン時の起動を設定できませんでした：{error}"),
    "quota.box": ("Zoho API limits", "Zoho API 使用上限", "Zoho API 使用上限", "Zoho API の上限"),
    "quota.plan": ("Zoho plan", "Zoho 方案", "Zoho 方案", "Zoho プラン"),
    "quota.daily": ("Daily limit", "每日上限", "每日上限", "1 日の上限"),
    "quota.minute": ("Per-minute limit", "每分钟上限", "每分鐘上限", "1 分あたりの上限"),
    "quota.remaining": ("Remaining today", "今日剩余", "今日剩餘", "本日の残り"),
    "quota.reset": ("Resets at", "重置时间", "重設時間", "リセット時刻"),
    "quota.local": ("Used by this computer today", "本机今日已用", "本機今日已用", "このコンピュータの本日の使用数"),
    "quota.estimate": ("Auto-sync estimate", "自动同步预计", "自動同步預計", "自動同期の見込み"),
    "quota.refresh": ("Refresh now (uses 1 API call)", "立即更新（使用 1 次 API）", "立即更新（使用 1 次 API）", "今すぐ更新（API を 1 回使用）"),
    "quota.hint": ("The daily limit is shared by the whole Zoho organization (including colleagues' computers and other integrations); the numbers come live from each Zoho response.",
                   "每日上限由整个 Zoho 组织共用（包括同事的电脑及其他集成），数字由 Zoho 每次响应实时提供。",
                   "每日上限由整個 Zoho 機構共用（包括同事的電腦及其他整合服務），數字由 Zoho 每次回應即時提供。",
                   "1 日の上限は Zoho の組織全体で共有されます（同僚のコンピュータや他の連携を含む）。数値は Zoho の各応答から取得しています。"),
    "quota.no_data": ("No data yet (sync once or click “Refresh now”)", "暂无数据（同步一次或点击“立即更新”）",
                      "尚無資料（同步一次或按「立即更新」）", "データがまだありません（一度同期するか「今すぐ更新」をクリック）"),
    "quota.updated": (" (updated {time})", "（{time} 更新）", "（{time} 更新）", "（{time} 更新）"),
    "quota.daily_value": ("{limit} calls (shared by the whole Zoho organization)", "{limit} 次（整个 Zoho 组织共用）",
                          "{limit} 次（整個 Zoho 機構共用）", "{limit} 回（Zoho の組織全体で共有）"),
    "quota.est": ("Every {interval} min × {types} document types ≈ {per_day} calls a day",
                  "每 {interval} 分钟 × {types} 种单据 ≈ 每日 {per_day} 次",
                  "每 {interval} 分鐘 × {types} 種文件 ≈ 每日 {per_day} 次",
                  "{interval} 分ごと × {types} 種類 ≈ 1 日 {per_day} 回"),
    "quota.est_pct": (" (about {pct}% of the daily limit)", "（约占每日上限 {pct}%）", "（約佔每日上限 {pct}%）", "（1 日の上限の約 {pct}%）"),
    "quota.est_warn": ("; consider a longer interval or fewer document types", "，建议延长检查间隔或减少单据类型",
                       "，建議延長檢查間隔或減少文件類型", "。確認間隔を長くするか、書類の種類を減らすことをおすすめします"),
    "quota.est_off": (" (auto sync is off)", "（自动同步未开启）", "（自動同步未開啟）", "（自動同期はオフ）"),
    "quota.bar": ("Zoho {plan} plan　|　API remaining today {remaining}", "Zoho {plan} 方案　｜　今日 API 剩余 {remaining}",
                  "Zoho {plan} 方案　｜　今日 API 剩餘 {remaining}", "Zoho {plan} プラン　｜　本日の API 残り {remaining}"),
    "quota.bar_reset": (" (resets {time})", "（{time} 重置）", "（{time} 重設）", "（{time} リセット）"),
    "quota.bar_local": ("　|　This computer today: {n}", "　｜　本机今日已用 {n} 次", "　｜　本機今日已用 {n} 次", "　｜　このコンピュータ本日 {n} 回"),
    "quota.failed": ("Could not read API usage: {error}", "读取 API 用量失败：{error}", "讀取 API 用量失敗：{error}", "API 使用量を取得できませんでした：{error}"),

    # ---- tray / sync
    "tray.open": ("Open Zoho Book Sync", "打开 Zoho Book Sync", "開啟 Zoho Book Sync", "Zoho Book Sync を開く"),
    "tray.sync_now": ("Sync New Now", "立即同步新单", "立即同步新文件", "今すぐ新規を同期"),
    "tray.pause": ("Pause Auto Sync", "暂停自动同步", "暫停自動同步", "自動同期を一時停止"),
    "tray.quit": ("Quit", "退出", "結束", "終了"),
    "tray.still_running": ("The app is still running in the background; reopen it from the menu bar / system tray.",
                           "程序仍在后台运行，可从菜单栏 / 系统托盘重新打开。",
                           "程式仍於背景執行，可從選單列／系統匣重新開啟。",
                           "アプリはバックグラウンドで動作中です。メニューバー／システムトレイから再度開けます。"),
    "sync.all.title": ("Sync All", "全部同步", "全部同步", "すべて同期"),
    "sync.all.body": ("This reads every document in Zoho and syncs any that are new or changed, ignoring the start date.\n"
                      "With many documents this uses more API calls. Continue?",
                      "将读取 Zoho 所有历史单据，同步未同步过或已修改的单据（不受开始日期限制）。\n单据较多时会使用较多 API 次数。继续？",
                      "將讀取 Zoho 所有歷史文件，同步未同步或已修改的文件（不受開始日期限制）。\n文件較多時會使用較多 API 次數。是否繼續？",
                      "Zoho のすべての書類を読み込み、未同期または変更された書類を同期します（開始日は無視）。\n書類が多いと API の使用回数が増えます。続けますか？"),
    "sync.reading": ("Reading Zoho…", "正在读取 Zoho…", "正在讀取 Zoho…", "Zoho を読み込んでいます…"),
    "sync.done": ("Synced {n} files", "已同步 {n} 个文件", "已同步 {n} 個檔案", "{n} 件のファイルを同期しました"),
    "sync.done_failed": (", {n} failed", "，{n} 个失败", "，{n} 個失敗", "、{n} 件失敗"),
    "sync.nothing": ("No new documents to sync", "没有需要同步的新单据", "沒有需要同步的新文件", "同期する新しい書類はありません"),
    "sync.failed": ("Sync failed", "同步失败", "同步失敗", "同期に失敗しました"),
    "sync.failed_title": ("{app} sync failed", "{app} 同步失败", "{app} 同步失敗", "{app} の同期に失敗しました"),

    # ---- Zoho client errors (zoho.py)
    "zerr.invalid_code": ("The Code is invalid or has expired (a Code is valid for 10 minutes and can be used only once)",
                          "Code 无效或已过期（Code 只有 10 分钟有效，且只能使用一次）",
                          "Code 無效或已過期（Code 只有 10 分鐘有效，且只能使用一次）",
                          "Code が無効か期限切れです（Code の有効期限は 10 分で、1 回のみ使用できます）"),
    "zerr.auth_failed": ("Authorization failed: {error}", "授权失败：{error}", "授權失敗：{error}", "認可に失敗しました：{error}"),
    "zerr.login_timeout": ("Timed out waiting for sign-in. Please try again.", "等待登录超时，请重试。", "等待登入逾時，請再試一次。",
                           "サインインの待機がタイムアウトしました。もう一度お試しください。"),
    "zerr.session_expired": ("Your sign-in has expired. Please reconnect Zoho ({error})", "登录已失效，请重新连接 Zoho（{error}）",
                             "登入已失效，請重新連接 Zoho（{error}）", "サインインの有効期限が切れました。Zoho に再接続してください（{error}）"),
    "zerr.rate_limited": ("The Zoho API limit has been exceeded. Please try again later.", "已超过 Zoho API 使用上限，请稍后再试。",
                          "已超過 Zoho API 使用上限，請稍後再試。", "Zoho API の上限を超えました。しばらくしてから再度お試しください。"),
    "zerr.forbidden": ("Not permitted: reconnect on the “Connect Zoho” tab to allow reading this document type.",
                       "权限不足：请在“连接 Zoho”页重新连接，授权读取此类单据。",
                       "權限不足：請於「連接 Zoho」分頁重新連接，授權讀取此類文件。",
                       "権限がありません：「Zoho 接続」タブで再接続し、この種類の書類の読み取りを許可してください。"),
    "zerr.api": ("Zoho API error {code}: {message}", "Zoho API 错误 {code}：{message}", "Zoho API 錯誤 {code}：{message}",
                 "Zoho API エラー {code}：{message}"),
    "zerr.unreachable": ("Cannot reach Zoho: {error}", "无法连接 Zoho：{error}", "無法連線至 Zoho：{error}", "Zoho に接続できません：{error}"),
    "zerr.retry_failed": ("Zoho API retries failed", "Zoho API 重试失败", "Zoho API 重試失敗", "Zoho API の再試行に失敗しました"),
    "zerr.no_pdf": ("Zoho did not return a PDF", "Zoho 没有返回 PDF", "Zoho 未有傳回 PDF", "Zoho から PDF が返されませんでした"),
    "zerr.callback_ok": ("Done. You can close this window and return to {app}.", "已完成，可以关闭此窗口，返回 {app}。",
                         "已完成，可以關閉此視窗，返回 {app}。", "完了しました。このウインドウを閉じて {app} に戻ってください。"),
}
