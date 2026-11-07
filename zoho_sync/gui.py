"""PySide6 GUI: main window (狀態 / 連接 / 同步設定 / 客戶資料夾 / 自動同步), tray icon, selection dialog."""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime

from PySide6.QtCore import QDate, QObject, QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from . import __version__, autostart, engine
from .config import (Partner, Settings, apply_api_call, get_secret, load_companies, load_quota, load_state,
                     save_companies, save_quota, save_state, set_secret)
from .zoho import DATA_CENTERS, BooksClient, ZohoError, browser_login, exchange_code, plan_daily_limit

log = logging.getLogger("zohosync")

DC_LABELS = {"com": "美國 / 香港 (zoho.com)", "eu": "歐洲 (zoho.eu)", "in": "印度 (zoho.in)",
             "com.au": "澳洲 (zoho.com.au)", "jp": "日本 (zoho.jp)", "ca": "加拿大 (zohocloud.ca)",
             "sa": "沙地阿拉伯 (zoho.sa)", "com.cn": "中國 (zoho.com.cn)"}
TEMPLATE_HELP = ("可用欄位：{partner} 客戶資料夾  {company} 公司  {customer} 聯絡人  {type} 文件類型  "
                 "{number} 單號  {year} 年  {month} 月  {date} 日期  {status} 狀態")


def make_icon(color: str = "#1f7a4d") -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color)); p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setPen(QColor("white")); f = QFont(); f.setBold(True); f.setPointSize(30); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "Z")
    p.end()
    return QIcon(pm)


def form_layout(parent=None) -> QFormLayout:
    f = QFormLayout(parent) if parent is not None else QFormLayout()
    f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)  # macOS default keeps fields tiny
    f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return f


class ApiBus(QObject):
    """Worker threads report every Books API call here; the window updates the usage counter."""
    call = Signal(dict)


API_BUS = ApiBus()


def make_client(s: Settings) -> BooksClient:
    if not s.connected:
        raise ZohoError("未連接 Zoho，請先去「連接 Zoho」設定")
    return BooksClient(dc=s.dc, client_id=s.client_id, client_secret=get_secret("client_secret"),
                       refresh_token=get_secret("refresh_token"), api_domain=s.api_domain or None,
                       org_id=s.org_id, observer=API_BUS.call.emit)


class Task(QThread):
    """Run fn(task) off the UI thread. fn may call task.report(i, n, text) and check task.cancelled()."""
    progress = Signal(int, int, str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn, self._cancel = fn, False

    def cancel(self):
        self._cancel = True

    def cancelled(self) -> bool:
        return self._cancel

    def report(self, i: int, n: int, text: str):
        self.progress.emit(i, n, text)

    def run(self):
        try:
            self.done.emit(self.fn(self))
        except Exception as e:  # surfaced in the UI
            log.exception("task failed")
            self.failed.emit(str(e))


# ---------------------------------------------------------------- selection dialog

class SelectDialog(QDialog):
    """自選同步: pick documents from a filtered list."""

    def __init__(self, settings: Settings, state: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自選同步")
        self.resize(900, 560)
        self.settings, self.state, self.docs, self.task = settings, state, [], None
        lay = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.type_box = QComboBox()
        self.type_box.addItem("所有已啟用類型", None)
        for t in engine.DOC_TYPES:
            if t.key in settings.doc_types:
                self.type_box.addItem(t.label, t.key)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-3)); self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        for w in (self.date_from, self.date_to):
            w.setDisplayFormat("yyyy-MM-dd")
        load = QPushButton("載入"); load.clicked.connect(self.load)
        bar.addWidget(QLabel("類型")); bar.addWidget(self.type_box)
        bar.addWidget(QLabel("日期由")); bar.addWidget(self.date_from)
        bar.addWidget(QLabel("至")); bar.addWidget(self.date_to); bar.addWidget(load); bar.addStretch()
        lay.addLayout(bar)

        bar2 = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("搜尋單號 / 公司…")
        self.search.textChanged.connect(self.apply_filter)
        self.only_new = QCheckBox("只顯示未同步過"); self.only_new.toggled.connect(self.apply_filter)
        sel_all = QPushButton("全選顯示中"); sel_all.clicked.connect(lambda: self.check_visible(True))
        sel_none = QPushButton("全部取消"); sel_none.clicked.connect(lambda: self.check_visible(False))
        for w in (self.search, self.only_new, sel_all, sel_none):
            bar2.addWidget(w)
        lay.addLayout(bar2)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", "類型", "單號", "日期", "公司", "狀態", "已同步"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.cellDoubleClicked.connect(self.toggle_row)
        lay.addWidget(self.table)

        self.info = QLabel("揀好日期範圍，撳「載入」。")
        lay.addWidget(self.info)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("同步已選")
        btns.button(QDialogButtonBox.Cancel).setText("取消")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def load(self):
        key = self.type_box.currentData()
        types = [key] if key else [t for t in self.settings.doc_types]
        dfrom, dto = self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")
        s = self.settings
        self.info.setText("載入中…")

        def work(task):
            client = make_client(s)
            return engine.list_documents(client, types, max_pages=None, cancelled=task.cancelled,
                                         date_start=dfrom, date_end=dto)

        self.task = Task(work, self)
        self.task.done.connect(self.fill)
        self.task.failed.connect(lambda m: self.info.setText(f"載入失敗：{m}"))
        self.task.start()

    def fill(self, docs):
        self.docs = sorted(docs, key=lambda d: (d.date, d.number), reverse=True)
        seen = self.state.get("docs", {})
        self.table.setRowCount(len(self.docs))
        for r, d in enumerate(self.docs):
            self.table.setItem(r, 0, QTableWidgetItem())
            self.table.setCellWidget(r, 0, self._check_cell())
            synced = "✓" if (seen.get(d.key) or {}).get("path") else ""
            vals = [d.type.label.split()[0], d.number, d.date, d.company or d.customer,
                    engine.STATUS_LABELS.get(d.status, d.status), synced]
            for c, v in enumerate(vals, 1):
                self.table.setItem(r, c, QTableWidgetItem(v))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 36)
        self.apply_filter()
        self.info.setText(f"共 {len(self.docs)} 張。剔選要同步嘅單，或者雙擊一行。")

    @staticmethod
    def _check_cell() -> QWidget:
        # a real QCheckBox per row: checkable empty QTableWidgetItems mis-render on macOS
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); l.setAlignment(Qt.AlignCenter)
        l.addWidget(QCheckBox())
        return w

    def _check(self, r: int) -> QCheckBox:
        return self.table.cellWidget(r, 0).findChild(QCheckBox)

    def apply_filter(self):
        q = self.search.text().strip().casefold()
        for r, d in enumerate(self.docs):
            hide = bool(q) and q not in f"{d.number} {d.company} {d.customer}".casefold()
            if self.only_new.isChecked() and self.table.item(r, 6).text():
                hide = True
            self.table.setRowHidden(r, hide)

    def check_visible(self, on: bool):
        for r in range(self.table.rowCount()):
            if on and self.table.isRowHidden(r):
                continue
            self._check(r).setChecked(on)

    def toggle_row(self, r, _c):
        cb = self._check(r)
        cb.setChecked(not cb.isChecked())

    def selection(self):
        keys = {self.docs[r].key for r in range(self.table.rowCount())
                if self._check(r).isChecked()}
        return [d for d in self.docs if d.key in keys], keys


# ---------------------------------------------------------------- company picker

class CompanyPicker(QDialog):
    """揀公司: opens instantly, loads the Zoho customer list (cached 24h) with a busy indicator."""

    def __init__(self, settings: Settings, row: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("揀公司")
        self.resize(480, 600)
        self.settings, self.row = settings, row
        self.current = set(settings.partners[row].companies)
        # company (normalized) -> name of the *other* 客戶 that already owns it
        self.owner = {engine.norm_company(c): p.name for i, p in enumerate(settings.partners)
                      if i != row for c in p.companies}
        self.task: Task | None = None
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("搜尋公司…")
        self.search.textChanged.connect(self.apply_filter)
        self.reload_btn = QPushButton("重新載入"); self.reload_btn.clicked.connect(lambda: self.load(force=True))
        top.addWidget(self.search, 1); top.addWidget(self.reload_btn)
        lay.addLayout(top)

        self.busy = QProgressBar(); self.busy.setRange(0, 0); self.busy.setTextVisible(False)  # animated "working"
        self.status = QLabel()
        lay.addWidget(self.busy); lay.addWidget(self.status)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        lay.addWidget(self.list, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        QTimer.singleShot(0, self.load)

    def load(self, force: bool = False):
        s = self.settings
        cached = None if force else load_companies(s.org_id)
        if cached is not None:
            self.fill(cached, "（已暫存，撳「重新載入」可以即時更新）")
            return
        self.set_busy(True, "讀取緊 Zoho 客戶名冊…")

        def work(task):
            names = engine.list_companies(make_client(s), cancelled=task.cancelled)
            save_companies(s.org_id, names)
            return names

        self.task = Task(work, self.parent())  # parent = main window, so closing the dialog can't kill a live thread
        self.task.done.connect(lambda names: self.isVisible() and self.fill(names, "（啱啱由 Zoho 讀取）"))
        self.task.failed.connect(lambda m: self.isVisible() and self.set_busy(False, f"❌ 載入失敗：{m}"))
        self.task.finished.connect(self.task.deleteLater)
        self.task.start()

    def set_busy(self, on: bool, text: str):
        self.busy.setVisible(on); self.status.setText(text)
        self.reload_btn.setEnabled(not on); self.list.setEnabled(not on)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not on)

    def fill(self, names: list[str], note: str):
        # keep companies already in this 客戶 even if Zoho no longer lists them
        known = {engine.norm_company(n) for n in names}
        extra = [c for c in self.current if engine.norm_company(c) not in known]
        current_norm = {engine.norm_company(c) for c in self.current}
        self.list.clear()
        for name in sorted(names + extra, key=str.casefold):
            owner = self.owner.get(engine.norm_company(name))
            cb = QCheckBox(name + (f"　（已屬：{owner}）" if owner else ""))
            cb.setProperty("company", name)
            cb.setChecked(engine.norm_company(name) in current_norm)
            it = QListWidgetItem(); it.setSizeHint(cb.sizeHint())
            self.list.addItem(it); self.list.setItemWidget(it, cb)  # real checkbox per row (macOS item-view bug)
        self.set_busy(False, f"共 {len(names)} 間公司 {note}")
        self.apply_filter()

    def apply_filter(self):
        q = self.search.text().strip().casefold()
        for i in range(self.list.count()):
            cb = self.list.itemWidget(self.list.item(i))
            self.list.item(i).setHidden(bool(q) and q not in cb.text().casefold())

    def chosen(self) -> list[str]:
        out = []
        for i in range(self.list.count()):
            cb = self.list.itemWidget(self.list.item(i))
            if cb.isChecked():
                out.append(cb.property("company"))
        return out

    def accept(self):
        moves = sorted({self.owner[engine.norm_company(c)] + "：" + c for c in self.chosen()
                        if engine.norm_company(c) in self.owner and engine.norm_company(c) not in
                        {engine.norm_company(x) for x in self.current}})
        if moves:
            target = self.settings.partners[self.row].name
            if QMessageBox.question(self, "搬公司", f"以下公司已經屬於其他客戶，確定搬去「{target}」？\n\n"
                                    + "\n".join(moves)) != QMessageBox.Yes:
                return
        super().accept()

    def reject(self):
        if self.task is not None:
            try:
                self.task.cancel()
            except RuntimeError:  # already finished and deleted
                pass
        super().reject()


# ---------------------------------------------------------------- main window

class MainWindow(QMainWindow):
    def __init__(self, start_hidden: bool = False):
        super().__init__()
        self.settings = Settings.load()
        self.task: Task | None = None
        self.last_sync: datetime | None = None
        self.quitting = False
        self.setWindowTitle(f"Zoho 同步 {__version__}")
        self.setWindowIcon(make_icon())
        self.resize(860, 620)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_status_tab(), "狀態")
        self.tabs.addTab(self.build_connect_tab(), "連接 Zoho")
        self.tabs.addTab(self.build_sync_tab(), "同步設定")
        self.tabs.addTab(self.build_partner_tab(), "客戶資料夾")
        self.tabs.addTab(self.build_auto_tab(), "自動同步")
        self.setCentralWidget(self.tabs)

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.start_sync("new", silent=True))
        self.quota = load_quota()
        self.quota_label = QLabel()
        self.statusBar().addPermanentWidget(self.quota_label)
        API_BUS.call.connect(self.on_api_call)
        self.build_tray()
        self.apply_auto()
        self.refresh_status()
        self.refresh_quota_ui()
        if self.settings.connected and self.quota.get("date") != date.today().isoformat():
            QTimer.singleShot(1500, self.refresh_quota)  # first launch today: fetch live remaining
        if not self.settings.connected:
            self.tabs.setCurrentIndex(1)
        if not start_hidden:
            self.show()

    # ---------- tab: 狀態
    def build_status_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.status_label = QLabel(); self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status_label)
        row = QHBoxLayout()
        self.btn_new = QPushButton("同步新單"); self.btn_new.setToolTip("同步新開或者改過嘅單（平時用呢個）")
        self.btn_all = QPushButton("全部同步…"); self.btn_all.setToolTip("連歷史單一齊同步")
        self.btn_sel = QPushButton("自選同步…")
        self.btn_cancel = QPushButton("停止"); self.btn_cancel.setEnabled(False)
        btn_open = QPushButton("開啟資料夾")
        self.btn_new.clicked.connect(lambda: self.start_sync("new"))
        self.btn_all.clicked.connect(self.confirm_all)
        self.btn_sel.clicked.connect(self.open_select)
        self.btn_cancel.clicked.connect(lambda: self.task and self.task.cancel())
        btn_open.clicked.connect(lambda: self.open_path(self.settings.output_root))
        for b in (self.btn_new, self.btn_all, self.btn_sel, self.btn_cancel):
            row.addWidget(b)
        row.addStretch(); row.addWidget(btn_open)
        lay.addLayout(row)
        self.progress = QProgressBar(); self.progress.setVisible(False)
        lay.addWidget(self.progress)

        lay.addWidget(QLabel("最近紀錄（雙擊開啟檔案）"))
        self.activity = QTableWidget(0, 6)
        self.activity.setHorizontalHeaderLabels(["同步時間", "類型", "單號", "公司", "結果", "檔案"])
        self.activity.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.activity.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.activity.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.activity.verticalHeader().hide()
        self.activity.cellDoubleClicked.connect(
            lambda r, c: self.open_path(self.activity.item(r, 5).text()) if self.activity.item(r, 5).text() else None)
        lay.addWidget(self.activity)
        return w

    def refresh_status(self):
        s = self.settings
        conn = f"✅ 已連接：<b>{s.org_name or s.org_id}</b>" if s.connected else "⚠️ <b>未連接 Zoho</b>"
        auto = f"每 {s.interval_min} 分鐘" if s.auto_sync else "關閉"
        last = self.last_sync.strftime("%H:%M:%S") if self.last_sync else "未有"
        types = "、".join(engine.TYPES_BY_KEY[k].label.split()[0] for k in s.doc_types) or "（未揀）"
        self.status_label.setText(
            f"{conn}<br>儲存位置：{s.output_root}<br>同步類型：{types}<br>"
            f"自動同步：{auto}　｜　上次同步：{last}")
        for b in (self.btn_new, self.btn_all, self.btn_sel):
            b.setEnabled(s.connected and self.task is None)
        if hasattr(self, "tray"):
            self.tray.setToolTip(f"Zoho 同步 — 上次同步 {last}")

    def add_activity(self, job, outcome, path):
        self.activity.insertRow(0)
        vals = [datetime.now().strftime("%m-%d %H:%M"), job.doc.type.label.split()[0], job.doc.number,
                job.doc.company or job.doc.customer, outcome, str(path or "")]
        for c, v in enumerate(vals):
            it = QTableWidgetItem(v)
            if outcome.startswith("失敗"):
                it.setForeground(QColor("#c0392b"))
            self.activity.setItem(0, c, it)
        while self.activity.rowCount() > 300:
            self.activity.removeRow(self.activity.rowCount() - 1)

    # ---------- tab: 連接
    def build_connect_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        s = self.settings
        mode_box = QGroupBox("連接方式"); ml = QVBoxLayout(mode_box)
        self.rb_browser = QRadioButton("一撳登入（用瀏覽器登入 Zoho，建議）")
        self.rb_manual = QRadioButton("手動輸入（Self Client：Client ID / Secret / Code）")
        grp = QButtonGroup(w); grp.addButton(self.rb_browser); grp.addButton(self.rb_manual)
        (self.rb_manual if s.auth_mode == "manual" else self.rb_browser).setChecked(True)
        ml.addWidget(self.rb_browser); ml.addWidget(self.rb_manual)
        lay.addWidget(mode_box)

        form = form_layout()
        self.dc_box = QComboBox()
        for k in DATA_CENTERS:
            self.dc_box.addItem(DC_LABELS.get(k, k), k)
        self.dc_box.setCurrentIndex(max(0, self.dc_box.findData(s.dc)))
        self.client_id = QLineEdit(s.client_id)
        self.client_secret = QLineEdit(get_secret("client_secret")); self.client_secret.setEchoMode(QLineEdit.Password)
        self.grant_code = QLineEdit(); self.grant_code.setPlaceholderText("1000.xxxx（10 分鐘內有效）")
        form.addRow("Zoho 地區", self.dc_box)
        form.addRow("Client ID", self.client_id)
        form.addRow("Client Secret", self.client_secret)
        self.code_label = QLabel("Code")
        form.addRow(self.code_label, self.grant_code)
        lay.addLayout(form)

        self.help = QLabel(); self.help.setWordWrap(True); self.help.setOpenExternalLinks(True)
        self.help.setTextInteractionFlags(Qt.TextBrowserInteraction)  # selectable + clickable links
        lay.addWidget(self.help)
        copy_row = QHBoxLayout()
        self.copy_label = QLabel()
        self.copy_value = QLineEdit(); self.copy_value.setReadOnly(True)
        copy_btn = QPushButton("複製")
        copy_btn.clicked.connect(self.copy_help_value)
        copy_row.addWidget(self.copy_label); copy_row.addWidget(self.copy_value, 1); copy_row.addWidget(copy_btn)
        lay.addLayout(copy_row)

        row = QHBoxLayout()
        self.btn_connect = QPushButton("連接 Zoho"); self.btn_connect.clicked.connect(self.connect_zoho)
        btn_disc = QPushButton("中斷連接"); btn_disc.clicked.connect(self.disconnect_zoho)
        row.addWidget(self.btn_connect); row.addWidget(btn_disc); row.addStretch()
        lay.addLayout(row)

        org_row = QHBoxLayout()
        self.org_box = QComboBox()
        if s.org_id:
            self.org_box.addItem(s.org_name or s.org_id, s.org_id)
        self.org_box.currentIndexChanged.connect(self.org_changed)
        org_row.addWidget(QLabel("Zoho Books 公司")); org_row.addWidget(self.org_box, 1)
        lay.addLayout(org_row)
        self.conn_msg = QLabel(); self.conn_msg.setWordWrap(True)
        lay.addWidget(self.conn_msg)
        lay.addStretch()
        for rb in (self.rb_browser, self.rb_manual):
            rb.toggled.connect(self.update_connect_help)
        self.dc_box.currentIndexChanged.connect(self.update_connect_help)
        self.conn_msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.update_connect_help()
        return w

    def update_connect_help(self):
        manual = self.rb_manual.isChecked()
        self.grant_code.setVisible(manual); self.code_label.setVisible(manual)
        dc = self.dc_box.currentData() or "com"
        from .zoho import REDIRECT_URI, SCOPES
        if manual:
            self.help.setText(
                f"1. 去 <a href='https://api-console.zoho.{dc}'>Zoho API Console</a> → Self Client，抄低 Client ID 同 Secret。<br>"
                "2. Generate Code tab，Scope 貼下面嗰串（撳「複製」）。<br>"
                "3. Time Duration 揀 10 minutes，撳 Create，將 Code 貼喺上面，撳「連接 Zoho」。")
            self.copy_label.setText("Scope"); self.copy_value.setText(SCOPES)
        else:
            self.help.setText(
                "填入公司 IT 提供嘅 Client ID 同 Secret，撳「連接 Zoho」，瀏覽器會開 Zoho 登入頁，撳「Accept」就完成。<br>"
                f"IT 設定（只需一次）：喺 <a href='https://api-console.zoho.{dc}'>API Console</a> → Add Client → "
                "<b>Server-based Applications</b>；Homepage URL 隨便填（例如 http://127.0.0.1:53682）；"
                "Authorized Redirect URIs 填下面嗰條（撳「複製」）。")
            self.copy_label.setText("Redirect URI"); self.copy_value.setText(REDIRECT_URI)
        self.copy_value.setCursorPosition(0)

    def copy_help_value(self):
        QApplication.clipboard().setText(self.copy_value.text())
        self.statusBar().showMessage(f"已複製 {self.copy_label.text()}", 3000)

    def connect_zoho(self):
        dc = self.dc_box.currentData()
        cid, secret, code = self.client_id.text().strip(), self.client_secret.text().strip(), self.grant_code.text().strip()
        manual = self.rb_manual.isChecked()
        if not cid or not secret or (manual and not code):
            QMessageBox.warning(self, "資料未填齊", "請填 Client ID、Client Secret" + ("同 Code。" if manual else "。"))
            return
        self.conn_msg.setText("連接中…" + ("" if manual else "請喺瀏覽器登入 Zoho 並撳 Accept。"))
        self.btn_connect.setEnabled(False)

        def work(task):
            tok = exchange_code(dc, cid, secret, code) if manual else browser_login(dc, cid, secret)
            client = BooksClient(dc=tok["dc"], client_id=cid, client_secret=secret,
                                 refresh_token=tok["refresh_token"], api_domain=tok["api_domain"],
                                 observer=API_BUS.call.emit)
            return tok, client.organizations()

        def ok(result):
            tok, orgs = result
            s = self.settings
            s.dc, s.client_id, s.api_domain = tok["dc"], cid, tok["api_domain"]
            s.auth_mode = "manual" if manual else "browser"
            set_secret("client_secret", secret); set_secret("refresh_token", tok["refresh_token"])
            self.grant_code.clear()
            self.org_box.blockSignals(True); self.org_box.clear()
            self._org_plans = {o["organization_id"]: o.get("plan_name") or "" for o in orgs}
            for o in orgs:
                self.org_box.addItem(o["name"], o["organization_id"])
            self.org_box.blockSignals(False)
            if not orgs:
                self.conn_msg.setText("已登入，但呢個帳戶冇 Zoho Books 公司。")
            else:
                idx = max(0, self.org_box.findData(s.org_id))
                self.org_box.setCurrentIndex(idx); self.org_changed(idx)
                self.conn_msg.setText(f"✅ 連接成功：{s.org_name}" + ("（有幾間公司，請喺上面揀）" if len(orgs) > 1 else ""))
                self.first_run_choice()
                QTimer.singleShot(0, self.refresh_quota)  # read live limits for the chosen org
            self.btn_connect.setEnabled(True)
            self.refresh_status()

        def fail(msg):
            self.conn_msg.setText(f"❌ {msg}")
            self.btn_connect.setEnabled(True)

        self.run_task(work, ok, fail, busy=False)

    def org_changed(self, idx):
        if idx < 0 or not self.org_box.itemData(idx) or not hasattr(self, "tray"):
            return
        self.settings.org_id = self.org_box.itemData(idx)
        self.settings.org_name = self.org_box.itemText(idx)
        plans = getattr(self, "_org_plans", {})
        if self.settings.org_id in plans:
            self.settings.plan_name = plans[self.settings.org_id]
        self.settings.save(); self.refresh_status(); self.refresh_quota_ui()

    def first_run_choice(self):
        if self.settings.since_date or load_state().get("docs"):
            return
        box = QMessageBox(self)
        box.setWindowTitle("由幾時開始同步？")
        box.setText("第一次使用：想點樣處理 Zoho 入面已經有嘅舊單？")
        today = box.addButton("只同步今日之後嘅新單", QMessageBox.AcceptRole)
        box.addButton("之後自己揀（全部同步 / 自選同步）", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is today:
            self.settings.since_date = date.today().isoformat()
            self.since_enabled.setChecked(True); self.since_date.setDate(QDate.currentDate())
            self.settings.save()

    def disconnect_zoho(self):
        if QMessageBox.question(self, "中斷連接", "確定中斷連接？已同步嘅檔案唔會刪除。") != QMessageBox.Yes:
            return
        set_secret("refresh_token", "")
        self.settings.org_id = self.settings.org_name = ""
        self.settings.save(); self.org_box.clear()
        self.conn_msg.setText("已中斷連接。"); self.refresh_status()

    # ---------- tab: 同步設定
    def build_sync_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        s = self.settings
        types = QGroupBox("同步邊啲文件"); tl = QHBoxLayout(types)
        self.type_checks = {}
        for t in engine.DOC_TYPES:
            cb = QCheckBox(t.label); cb.setChecked(t.key in s.doc_types)
            cb.toggled.connect(self.save_sync)
            self.type_checks[t.key] = cb; tl.addWidget(cb)
        lay.addWidget(types)

        st = QGroupBox("唔同步以下狀態"); sl = QHBoxLayout(st)
        self.status_checks = {}
        for k in ("draft", "void", "declined", "expired"):
            cb = QCheckBox(engine.STATUS_LABELS[k]); cb.setChecked(k in s.skip_statuses)
            cb.toggled.connect(self.save_sync)
            self.status_checks[k] = cb; sl.addWidget(cb)
        sl.addStretch()
        lay.addWidget(st)

        form = form_layout()
        since_row = QHBoxLayout()
        self.since_enabled = QCheckBox("只同步呢日或之後嘅新單")
        self.since_date = QDateEdit(QDate.fromString(s.since_date, "yyyy-MM-dd") if s.since_date else QDate.currentDate())
        self.since_date.setCalendarPopup(True); self.since_date.setDisplayFormat("yyyy-MM-dd")
        self.since_enabled.setChecked(bool(s.since_date))
        self.since_enabled.toggled.connect(self.save_sync); self.since_date.dateChanged.connect(self.save_sync)
        since_row.addWidget(self.since_enabled); since_row.addWidget(self.since_date); since_row.addStretch()
        form.addRow("開始日期", since_row)

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(s.output_root); self.out_edit.editingFinished.connect(self.save_sync)
        browse = QPushButton("選擇…"); browse.clicked.connect(self.pick_folder)
        out_row.addWidget(self.out_edit, 1); out_row.addWidget(browse)
        form.addRow("儲存位置", out_row)

        self.template = QLineEdit(s.path_template)
        self.template.textChanged.connect(self.update_preview); self.template.editingFinished.connect(self.save_sync)
        form.addRow("資料夾同檔名", self.template)
        tip = QLabel(TEMPLATE_HELP); tip.setWordWrap(True); tip.setTextInteractionFlags(Qt.TextSelectableByMouse); tip.setStyleSheet("color:gray")
        form.addRow("", tip)
        self.preview = QLabel(); self.preview.setStyleSheet("color:#1f7a4d")
        form.addRow("例子", self.preview)

        conflict = QWidget(); cl = QVBoxLayout(conflict); cl.setContentsMargins(0, 0, 0, 0)
        self.conflict_btns = {}
        for k, label in (("version", "另存新版本（例如 INV001_v2.pdf，保留舊檔，建議）"),
                         ("overwrite", "直接覆蓋舊檔"),
                         ("skip", "已有檔案就唔更新")):
            rb = QRadioButton(label); rb.setChecked(s.conflict == k); rb.toggled.connect(self.save_sync)
            self.conflict_btns[k] = rb; cl.addWidget(rb)
        form.addRow("Zoho 改咗張單", conflict)
        lay.addLayout(form)
        lay.addStretch()
        self.update_preview()
        return w

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "選擇儲存位置", self.out_edit.text())
        if d:
            self.out_edit.setText(d); self.save_sync()

    def update_preview(self):
        t = engine.TYPES_BY_KEY["invoices"]
        demo = engine.Doc(t, "1", "INV2020196", date.today().isoformat(), "Ken, ABC Limited",
                          "ABC Limited", "sent", 0, "")
        tmp = Settings(**{**self.settings.__dict__, "path_template": self.template.text(), "output_root": "…"})
        try:
            self.preview.setText(str(engine.dest_path(demo, tmp)))
        except Exception as e:
            self.preview.setText(f"格式有錯：{e}")

    def save_sync(self, *_):
        s = self.settings
        s.doc_types = [k for k, cb in self.type_checks.items() if cb.isChecked()]
        s.skip_statuses = [k for k, cb in self.status_checks.items() if cb.isChecked()]
        s.since_date = self.since_date.date().toString("yyyy-MM-dd") if self.since_enabled.isChecked() else ""
        s.output_root = self.out_edit.text().strip() or s.output_root
        s.path_template = self.template.text().strip() or "{partner}/{type}/{number}.pdf"
        s.conflict = next(k for k, rb in self.conflict_btns.items() if rb.isChecked())
        s.save(); self.refresh_status(); self.refresh_quota_ui()

    # ---------- tab: 客戶資料夾
    def build_partner_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.partner_only = QCheckBox("只同步下面列出嘅公司（其他客唔同步）")
        self.partner_only.setChecked(self.settings.partner_only)
        self.partner_only.toggled.connect(self.save_partners)
        lay.addWidget(self.partner_only)
        lay.addWidget(QLabel("每個客戶一個資料夾，可以將幾間 Zoho 公司放入同一個客戶資料夾。冇列出嘅公司會用自己公司名做資料夾。"))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.partner_list = QListWidget(); self.partner_list.currentRowChanged.connect(self.partner_selected)
        left.addWidget(self.partner_list)
        pr = QHBoxLayout()
        add = QPushButton("新增客戶"); add.clicked.connect(self.add_partner)
        rm = QPushButton("刪除"); rm.clicked.connect(self.remove_partner)
        pr.addWidget(add); pr.addWidget(rm); left.addLayout(pr)
        body.addLayout(left, 1)

        right = QVBoxLayout()
        self.partner_name = QLineEdit(); self.partner_name.setPlaceholderText("客戶資料夾名")
        self.partner_name.editingFinished.connect(self.save_partners)
        right.addWidget(QLabel("資料夾名")); right.addWidget(self.partner_name)
        right.addWidget(QLabel("包括嘅 Zoho 公司（每行一間）"))
        self.partner_companies = QPlainTextEdit()
        self.partner_companies.textChanged.connect(self.save_partners)
        right.addWidget(self.partner_companies)
        pick = QPushButton("由 Zoho 揀公司…"); pick.clicked.connect(self.pick_companies)
        right.addWidget(pick)
        body.addLayout(right, 2)
        lay.addLayout(body)
        self._loading_partner = False
        self.reload_partner_list()
        return w

    def reload_partner_list(self, select: int = 0):
        self.partner_list.blockSignals(True); self.partner_list.clear()
        for p in self.settings.partners:
            self.partner_list.addItem(f"{p.name}（{len(p.companies)} 間）")
        self.partner_list.blockSignals(False)
        if self.settings.partners:
            self.partner_list.setCurrentRow(min(select, len(self.settings.partners) - 1))
        self.partner_selected(self.partner_list.currentRow())

    def partner_selected(self, row):
        self._loading_partner = True
        has = 0 <= row < len(self.settings.partners)
        p = self.settings.partners[row] if has else None
        self.partner_name.setText(p.name if p else ""); self.partner_companies.setPlainText("\n".join(p.companies) if p else "")
        self.partner_name.setEnabled(has); self.partner_companies.setEnabled(has)
        self._loading_partner = False

    def add_partner(self):
        self.settings.partners.append(Partner(f"客戶 {len(self.settings.partners) + 1}", []))
        self.settings.save(); self.reload_partner_list(len(self.settings.partners) - 1)
        self.partner_name.setFocus(); self.partner_name.selectAll()

    def remove_partner(self):
        row = self.partner_list.currentRow()
        if 0 <= row < len(self.settings.partners):
            del self.settings.partners[row]
            self.settings.save(); self.reload_partner_list(row)

    def save_partners(self, *_):
        if self._loading_partner:
            return
        self.settings.partner_only = self.partner_only.isChecked()
        row = self.partner_list.currentRow()
        if 0 <= row < len(self.settings.partners):
            p = self.settings.partners[row]
            p.name = engine.safe(self.partner_name.text().strip() or p.name)
            p.companies = [c.strip() for c in self.partner_companies.toPlainText().splitlines() if c.strip()]
            self.partner_list.item(row).setText(f"{p.name}（{len(p.companies)} 間）")
        self.settings.save()

    def pick_companies(self):
        row = self.partner_list.currentRow()
        if not (0 <= row < len(self.settings.partners)):
            return
        if not self.settings.connected:
            QMessageBox.warning(self, "未連接", "請先喺「連接 Zoho」連接。")
            return
        dlg = CompanyPicker(self.settings, row, self)
        if not dlg.exec():
            return
        chosen = dlg.chosen()
        chosen_norm = {engine.norm_company(c) for c in chosen}
        # move: drop chosen companies from every other 客戶
        for i, p in enumerate(self.settings.partners):
            if i != row:
                p.companies = [c for c in p.companies if engine.norm_company(c) not in chosen_norm]
        self.settings.partners[row].companies = chosen
        self.settings.save()
        self.reload_partner_list(row)

    # ---------- tab: 自動同步
    def build_auto_tab(self):
        w = QWidget(); lay = form_layout(w)
        s = self.settings
        self.auto_cb = QCheckBox("開啟自動同步（只同步新單同改過嘅單）"); self.auto_cb.setChecked(s.auto_sync)
        self.interval = QSpinBox(); self.interval.setRange(5, 240); self.interval.setSuffix(" 分鐘"); self.interval.setValue(s.interval_min)
        self.login_cb = QCheckBox("開機自動啟動（喺背景運行）"); self.login_cb.setChecked(s.start_at_login)
        self.notify_cb = QCheckBox("有新檔案或者出錯時通知我"); self.notify_cb.setChecked(s.notify)
        for wd in (self.auto_cb, self.login_cb, self.notify_cb):
            wd.toggled.connect(self.save_auto)
        self.interval.valueChanged.connect(self.save_auto)
        lay.addRow(self.auto_cb)
        lay.addRow("檢查頻率", self.interval)
        lay.addRow(self.login_cb)
        lay.addRow(self.notify_cb)
        note = QLabel("關咗視窗程式會留喺選單列 / 系統匣繼續運行。")
        note.setWordWrap(True); note.setStyleSheet("color:gray")
        lay.addRow(note)

        box = QGroupBox("Zoho API 使用上限"); bl = form_layout(box)
        self.q_plan, self.q_daily, self.q_minute = QLabel(), QLabel(), QLabel()
        self.q_remaining, self.q_reset, self.q_local, self.q_estimate = QLabel(), QLabel(), QLabel(), QLabel()
        for lab in (self.q_plan, self.q_daily, self.q_minute, self.q_remaining, self.q_reset, self.q_local, self.q_estimate):
            lab.setWordWrap(True); lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addRow("Zoho 方案", self.q_plan)
        bl.addRow("每日上限", self.q_daily)
        bl.addRow("每分鐘上限", self.q_minute)
        bl.addRow("今日剩餘", self.q_remaining)
        bl.addRow("重設時間", self.q_reset)
        bl.addRow("本機今日已用", self.q_local)
        bl.addRow("自動同步預計", self.q_estimate)
        self.q_refresh = QPushButton("立即更新（用 1 次 API）"); self.q_refresh.clicked.connect(self.refresh_quota)
        bl.addRow("", self.q_refresh)
        hint = QLabel("每日上限係成個 Zoho 機構共用（包括同事部機同其他整合），數字由 Zoho 每次回應即時提供。")
        hint.setWordWrap(True); hint.setStyleSheet("color:gray")
        bl.addRow(hint)
        lay.addRow(box)
        return w

    def save_auto(self, *_):
        s = self.settings
        login_changed = s.start_at_login != self.login_cb.isChecked()
        s.auto_sync, s.interval_min = self.auto_cb.isChecked(), self.interval.value()
        s.start_at_login, s.notify = self.login_cb.isChecked(), self.notify_cb.isChecked()
        s.save()
        if login_changed:
            try:
                autostart.set_enabled(s.start_at_login)
            except Exception as e:
                QMessageBox.warning(self, "設定失敗", f"開機啟動設定失敗：{e}")
        self.apply_auto(); self.refresh_status(); self.refresh_quota_ui()

    # ---------- API quota
    def on_api_call(self, rate: dict):
        self.quota = apply_api_call(self.quota, rate)
        save_quota(self.quota)
        self.refresh_quota_ui()

    def refresh_quota(self):
        if not self.settings.connected or getattr(self, "_quota_task", None) is not None:
            return
        s = Settings(**self.settings.__dict__)
        self.q_refresh.setEnabled(False)

        def work(task):
            client = make_client(s)
            orgs = client.organizations()                   # plan name (no quota headers on this one)
            client.quota_probe()                            # org call -> X-Rate-Limit-* headers
            return next((o.get("plan_name") or "" for o in orgs if o["organization_id"] == s.org_id), "")

        def ok(plan):
            if plan:
                self.settings.plan_name = plan; self.settings.save()
            self.refresh_quota_ui()

        def done():
            self._quota_task = None; self.q_refresh.setEnabled(True)

        task = Task(work, self)
        task.done.connect(ok)
        task.failed.connect(lambda m: self.statusBar().showMessage(f"讀取 API 用量失敗：{m}", 8000))
        task.finished.connect(done); task.finished.connect(task.deleteLater)
        self._quota_task = task
        task.start()

    def quota_view(self) -> dict:
        """Numbers to show; limit falls back to the plan table until Zoho has reported one."""
        q, today = self.quota, date.today().isoformat()
        plan = self.settings.plan_name or ""
        limit = q.get("limit") or plan_daily_limit(plan)
        fresh = q.get("date") == today and "remaining" in q
        reset_at = q.get("reset_at")
        if reset_at and reset_at < datetime.now().timestamp():  # window already rolled over
            fresh = False
        return {"plan": plan, "limit": limit, "remaining": q.get("remaining") if fresh else None,
                "reset_at": reset_at if fresh else None, "per_minute": q.get("per_minute"),
                "local_used": q.get("local_used", 0) if q.get("date") == today else 0,
                "updated_at": q.get("updated_at") if fresh else None}

    def refresh_quota_ui(self):
        if not hasattr(self, "quota_label"):
            return
        v, s = self.quota_view(), self.settings
        plan = v["plan"] or "未知"
        limit = f"{v['limit']:,}" if v["limit"] else "未知"
        if v["remaining"] is not None and v["limit"]:
            rem = f"{v['remaining']:,} / {limit}"
            low = v["remaining"] < v["limit"] * 0.1
        else:
            rem, low = "未有資料（同步一次或撳「立即更新」）", False
        reset = datetime.fromtimestamp(v["reset_at"]).strftime("%H:%M") if v["reset_at"] else "未知"
        upd = datetime.fromtimestamp(v["updated_at"]).strftime("%H:%M") if v["updated_at"] else None
        per_cycle = max(1, len(s.doc_types))
        per_day = (24 * 60 // max(1, s.interval_min)) * per_cycle
        est = f"每 {s.interval_min} 分鐘 × {per_cycle} 種文件 ≈ 每日 {per_day:,} 次"
        if v["limit"]:
            pct = per_day * 100 // v["limit"]
            est += f"（約佔每日上限 {pct}%）"
            if s.auto_sync and pct >= 50:
                est = "⚠️ " + est + "，建議拉長檢查頻率或者減少文件類型"
        if not s.auto_sync:
            est += "（自動同步未開）"
        if hasattr(self, "q_plan"):
            self.q_plan.setText(plan)
            self.q_daily.setText(f"{limit} 次（成個 Zoho 機構共用）")
            self.q_minute.setText(f"{v['per_minute']:,} 次" if v["per_minute"] else "未知")
            self.q_remaining.setText(rem + (f"（{upd} 更新）" if upd else ""))
            self.q_remaining.setStyleSheet("color:#c0392b" if low else "")
            self.q_reset.setText(reset)
            self.q_local.setText(f"{v['local_used']:,} 次")
            self.q_estimate.setText(est)
        short_rem = f"{v['remaining']:,} / {limit}" if v["remaining"] is not None and v["limit"] else "—"
        self.quota_label.setText(f"Zoho {plan} 方案　｜　今日 API 剩餘 {short_rem}"
                                 + (f"（{reset} 重設）" if v["reset_at"] else "")
                                 + f"　｜　本機今日已用 {v['local_used']:,} 次")
        self.quota_label.setStyleSheet("color:#c0392b" if low else "")

    def apply_auto(self):
        self.timer.stop()
        if self.settings.auto_sync:
            self.timer.start(self.settings.interval_min * 60_000)
        self.pause_action.setChecked(not self.settings.auto_sync)

    # ---------- tray
    def build_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self)
        menu = QMenu()
        menu.addAction("開啟 Zoho 同步", self.show_window)
        menu.addAction("立即同步新單", lambda: self.start_sync("new"))
        menu.addAction("開啟資料夾", lambda: self.open_path(self.settings.output_root))
        self.pause_action = QAction("暫停自動同步", menu, checkable=True)
        self.pause_action.toggled.connect(self.toggle_pause)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction("結束", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger and sys.platform == "win32" else None)
        self.tray.show()

    def toggle_pause(self, paused):
        if self.settings.auto_sync == (not paused):
            return
        self.auto_cb.setChecked(not paused)

    def show_window(self):
        self.show(); self.raise_(); self.activateWindow()

    def closeEvent(self, e):
        if self.quitting or not QSystemTrayIcon.isSystemTrayAvailable():
            return super().closeEvent(e)
        e.ignore(); self.hide()
        if not getattr(self, "_told_tray", False):
            self.tray.showMessage("Zoho 同步", "程式仍然喺背景運行，可以喺選單列 / 系統匣開返。")
            self._told_tray = True

    def quit_app(self):
        self.quitting = True
        if self.task:
            self.task.cancel(); self.task.wait(5000)
        QApplication.quit()

    # ---------- sync
    def confirm_all(self):
        if QMessageBox.question(self, "全部同步",
                                "會讀取 Zoho 所有歷史單據，同步未同步過或者改過嘅單（唔理開始日期）。\n"
                                "單據多嘅話會用較多 API 次數。繼續？") == QMessageBox.Yes:
            self.start_sync("all")

    def open_select(self):
        dlg = SelectDialog(self.settings, load_state(), self)
        if dlg.exec():
            docs, keys = dlg.selection()
            if docs:
                self.start_sync("selected", docs=docs, keys=keys)

    def start_sync(self, mode: str, silent: bool = False, docs=None, keys=None):
        if self.task is not None or not self.settings.connected:
            return
        s = Settings(**self.settings.__dict__)  # snapshot so edits mid-run don't race

        def work(task):
            client = make_client(s)
            state = load_state()
            if docs is None:
                task.report(0, 0, "讀取 Zoho…")
                found = engine.list_documents(client, s.doc_types, max_pages=None if mode == "all" else 1,
                                              cancelled=task.cancelled)
            else:
                found = docs
            jobs = engine.plan(found, s, state, mode=mode, selected=keys)
            results = engine.run(client, jobs, s, state, cancelled=task.cancelled, save=save_state,
                                 progress=lambda i, n, j, o: task.report(i, n, f"{j.doc.number} {o}"))
            save_state(state)
            return results, client.calls

        def ok(result):
            results, calls = result
            self.last_sync = datetime.now()
            for job, outcome, path in results:
                self.add_activity(job, outcome, path)
                log.info("%s %s %s %s", job.doc.type.key, job.doc.number, outcome, path)
            new = [r for r in results if r[1] in ("已建立", "新版本", "已覆蓋")]
            bad = [r for r in results if r[1].startswith("失敗")]
            log.info("sync %s: %d written, %d failed, %d api calls", mode, len(new), len(bad), calls)
            if self.settings.notify and (new or bad):
                msg = f"已同步 {len(new)} 個檔案" + (f"，{len(bad)} 個失敗" if bad else "")
                self.tray.showMessage("Zoho 同步", msg,
                                      QSystemTrayIcon.Warning if bad else QSystemTrayIcon.Information)
            if not silent and not results:
                self.statusBar().showMessage("冇新單需要同步", 5000)

        def fail(msg):
            log.error("sync failed: %s", msg)
            if silent:
                if self.settings.notify:
                    self.tray.showMessage("Zoho 同步失敗", msg, QSystemTrayIcon.Warning)
            else:
                QMessageBox.warning(self, "同步失敗", msg)

        self.run_task(work, ok, fail)

    def run_task(self, fn, ok, fail, busy: bool = True):
        task = Task(fn, self)
        if busy:
            self.task = task
            self.btn_cancel.setEnabled(True); self.progress.setVisible(True); self.progress.setRange(0, 0)
            self.refresh_status()

        def on_progress(i, n, text):
            if n:
                self.progress.setRange(0, n); self.progress.setValue(i)
            self.progress.setFormat(text); self.statusBar().showMessage(text)

        def finish():
            if busy:
                self.task = None
                self.btn_cancel.setEnabled(False); self.progress.setVisible(False)
                self.refresh_status()
            task.deleteLater()

        task.progress.connect(on_progress)
        task.done.connect(ok); task.failed.connect(fail)
        task.finished.connect(finish)
        task.start()

    @staticmethod
    def open_path(path: str):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
