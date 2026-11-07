"""PySide6 GUI: main window (status / connect / sync settings / customer folders / auto sync), tray icon,
selection and company-picker dialogs. All user-visible text goes through i18n.tr()."""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime

from PySide6.QtCore import QDate, QLibraryInfo, QLocale, QObject, QThread, QTimer, QTranslator, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from . import __version__, autostart, engine, i18n
from .config import (Partner, Settings, apply_api_call, get_secret, load_companies, load_quota, load_state,
                     save_companies, save_quota, save_state, set_secret)
from .i18n import tr
from .zoho import DATA_CENTERS, BooksClient, ZohoError, browser_login, exchange_code, plan_daily_limit

log = logging.getLogger("zohobooksync")

_qt_translator: QTranslator | None = None


def system_language() -> str:
    return i18n.detect(QLocale.system().uiLanguages())


def apply_language(code: str) -> str:
    """Set the UI language ("" = follow the system) and load Qt's own strings (Yes/No, Cancel…)."""
    global _qt_translator
    lang = code if code in i18n.LANGUAGES else system_language()
    i18n.set_language(lang)
    app = QApplication.instance()
    if app is not None:
        if _qt_translator is not None:
            app.removeTranslator(_qt_translator)
        _qt_translator = QTranslator()
        path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if _qt_translator.load(f"qtbase_{i18n.QT_LOCALES[lang]}", path):
            app.installTranslator(_qt_translator)
    return lang


def doctype_label(key: str) -> str:
    return tr(f"doctype.{key}", default=key)


def status_label(code: str) -> str:
    return tr(f"status.{code}", default=code)


def outcome_label(outcome: str, error: str = "") -> str:
    return tr(f"outcome.{outcome}", default=outcome, error=error)


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
        raise ZohoError(tr("err.not_connected"))
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
    """Pick documents from a filtered list."""

    def __init__(self, settings: Settings, state: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("sel.title"))
        self.resize(900, 560)
        self.settings, self.state, self.docs, self.task = settings, state, [], None
        lay = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.type_box = QComboBox()
        self.type_box.addItem(tr("sel.all_types"), None)
        for t in engine.DOC_TYPES:
            if t.key in settings.doc_types:
                self.type_box.addItem(doctype_label(t.key), t.key)
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-3)); self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate()); self.date_to.setCalendarPopup(True)
        for w in (self.date_from, self.date_to):
            w.setDisplayFormat("yyyy-MM-dd")
        load = QPushButton(tr("sel.load")); load.clicked.connect(self.load)
        bar.addWidget(QLabel(tr("sel.type"))); bar.addWidget(self.type_box)
        bar.addWidget(QLabel(tr("sel.from"))); bar.addWidget(self.date_from)
        bar.addWidget(QLabel(tr("sel.to"))); bar.addWidget(self.date_to); bar.addWidget(load); bar.addStretch()
        lay.addLayout(bar)

        bar2 = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("sel.search"))
        self.search.textChanged.connect(self.apply_filter)
        self.only_new = QCheckBox(tr("sel.only_new")); self.only_new.toggled.connect(self.apply_filter)
        sel_all = QPushButton(tr("sel.check_visible")); sel_all.clicked.connect(lambda: self.check_visible(True))
        sel_none = QPushButton(tr("sel.uncheck_all")); sel_none.clicked.connect(lambda: self.check_visible(False))
        for w in (self.search, self.only_new, sel_all, sel_none):
            bar2.addWidget(w)
        lay.addLayout(bar2)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", tr("col.type"), tr("col.number"), tr("col.date"),
                                              tr("col.company"), tr("col.status"), tr("col.synced")])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.cellDoubleClicked.connect(self.toggle_row)
        lay.addWidget(self.table)

        self.info = QLabel(tr("sel.hint"))
        lay.addWidget(self.info)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText(tr("sel.ok"))
        btns.button(QDialogButtonBox.Cancel).setText(tr("common.cancel"))
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def load(self):
        key = self.type_box.currentData()
        types = [key] if key else [t for t in self.settings.doc_types]
        dfrom, dto = self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")
        s = self.settings
        self.info.setText(tr("sel.loading"))

        def work(task):
            client = make_client(s)
            return engine.list_documents(client, types, max_pages=None, cancelled=task.cancelled,
                                         date_start=dfrom, date_end=dto)

        self.task = Task(work, self)
        self.task.done.connect(self.fill)
        self.task.failed.connect(lambda m: self.info.setText(tr("sel.failed", error=m)))
        self.task.start()

    def fill(self, docs):
        self.docs = sorted(docs, key=lambda d: (d.date, d.number), reverse=True)
        seen = self.state.get("docs", {})
        self.table.setRowCount(len(self.docs))
        for r, d in enumerate(self.docs):
            self.table.setItem(r, 0, QTableWidgetItem())
            self.table.setCellWidget(r, 0, self._check_cell())
            synced = "✓" if (seen.get(d.key) or {}).get("path") else ""
            vals = [doctype_label(d.type.key), d.number, d.date, d.company or d.customer,
                    status_label(d.status), synced]
            for c, v in enumerate(vals, 1):
                self.table.setItem(r, c, QTableWidgetItem(v))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 36)
        self.apply_filter()
        self.info.setText(tr("sel.count", n=len(self.docs)))

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
    """Opens instantly, loads the Zoho customer list (cached 24h) with a busy indicator."""

    def __init__(self, settings: Settings, row: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("pick.title"))
        self.resize(480, 600)
        self.settings, self.row = settings, row
        self.current = set(settings.partners[row].companies)
        # company (normalized) -> name of the *other* customer folder that already owns it
        self.owner = {engine.norm_company(c): p.name for i, p in enumerate(settings.partners)
                      if i != row for c in p.companies}
        self.task: Task | None = None
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("pick.search"))
        self.search.textChanged.connect(self.apply_filter)
        self.reload_btn = QPushButton(tr("pick.reload")); self.reload_btn.clicked.connect(lambda: self.load(force=True))
        top.addWidget(self.search, 1); top.addWidget(self.reload_btn)
        lay.addLayout(top)

        self.busy = QProgressBar(); self.busy.setRange(0, 0); self.busy.setTextVisible(False)  # animated "working"
        self.status = QLabel()
        lay.addWidget(self.busy); lay.addWidget(self.status)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.NoSelection)
        lay.addWidget(self.list, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Cancel).setText(tr("common.cancel"))
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        QTimer.singleShot(0, self.load)

    def load(self, force: bool = False):
        s = self.settings
        cached = None if force else load_companies(s.org_id)
        if cached is not None:
            self.fill(cached, tr("pick.cached"))
            return
        self.set_busy(True, tr("pick.loading"))

        def work(task):
            names = engine.list_companies(make_client(s), cancelled=task.cancelled)
            save_companies(s.org_id, names)
            return names

        self.task = Task(work, self.parent())  # parent = main window, so closing the dialog can't kill a live thread
        self.task.done.connect(lambda names: self.isVisible() and self.fill(names, tr("pick.fresh")))
        self.task.failed.connect(lambda m: self.isVisible() and self.set_busy(False, tr("pick.failed", error=m)))
        self.task.finished.connect(self.task.deleteLater)
        self.task.start()

    def set_busy(self, on: bool, text: str):
        self.busy.setVisible(on); self.status.setText(text)
        self.reload_btn.setEnabled(not on); self.list.setEnabled(not on)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not on)

    def fill(self, names: list[str], note: str):
        # keep companies already in this customer folder even if Zoho no longer lists them
        known = {engine.norm_company(n) for n in names}
        extra = [c for c in self.current if engine.norm_company(c) not in known]
        current_norm = {engine.norm_company(c) for c in self.current}
        self.list.clear()
        for name in sorted(names + extra, key=str.casefold):
            owner = self.owner.get(engine.norm_company(name))
            cb = QCheckBox(name + (tr("pick.owned", owner=owner) if owner else ""))
            cb.setProperty("company", name)
            cb.setChecked(engine.norm_company(name) in current_norm)
            it = QListWidgetItem(); it.setSizeHint(cb.sizeHint())
            self.list.addItem(it); self.list.setItemWidget(it, cb)  # real checkbox per row (macOS item-view bug)
        self.set_busy(False, tr("pick.count", n=len(names), note=note))
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
        current_norm = {engine.norm_company(x) for x in self.current}
        moves = sorted({f"{self.owner[engine.norm_company(c)]}: {c}" for c in self.chosen()
                        if engine.norm_company(c) in self.owner and engine.norm_company(c) not in current_norm})
        if moves:
            target = self.settings.partners[self.row].name
            if QMessageBox.question(self, tr("pick.move.title"),
                                    tr("pick.move.body", target=target, moves="\n".join(moves))) != QMessageBox.Yes:
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
        self.activity_log: list[tuple] = []  # (time, job, outcome, path, error), newest first; survives language switch
        self.setWindowIcon(make_icon())
        self.resize(860, 620)

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.start_sync("new", silent=True))
        self.quota = load_quota()
        self.quota_label = QLabel()
        self.statusBar().addPermanentWidget(self.quota_label)
        API_BUS.call.connect(self.on_api_call)
        self.tray = QSystemTrayIcon(make_icon(), self)
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger and sys.platform == "win32" else None)

        self.build_ui()
        self.tray.show()
        self.apply_auto()
        if self.settings.connected and self.quota.get("date") != date.today().isoformat():
            QTimer.singleShot(1500, self.refresh_quota)  # first launch today: fetch live remaining
        if not self.settings.connected:
            self.tabs.setCurrentIndex(1)
        if not start_hidden:
            self.show()

    def build_ui(self):
        """(Re)build every widget in the current language."""
        current = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        self.setWindowTitle(f"{tr('app.name')} {__version__}")
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_status_tab(), tr("tab.status"))
        self.tabs.addTab(self.build_connect_tab(), tr("tab.connect"))
        self.tabs.addTab(self.build_sync_tab(), tr("tab.sync"))
        self.tabs.addTab(self.build_partner_tab(), tr("tab.customers"))
        self.tabs.addTab(self.build_auto_tab(), tr("tab.auto"))
        self.setCentralWidget(self.tabs)  # deletes the previous tabs
        self.tabs.setCurrentIndex(current)
        self.build_tray_menu()
        for entry in reversed(self.activity_log):
            self._insert_activity_row(*entry)
        self.refresh_status()
        self.refresh_quota_ui()

    # ---------- language
    def build_language_box(self) -> QComboBox:
        box = QComboBox()
        box.addItem(tr("language.system", name=i18n.LANGUAGES[system_language()]), "")
        for code, name in i18n.LANGUAGES.items():
            box.addItem(name, code)
        box.setCurrentIndex(max(0, box.findData(self.settings.language)))
        box.currentIndexChanged.connect(lambda i: self.change_language(box.itemData(i)))
        return box

    def change_language(self, code: str):
        if code == self.settings.language:
            return
        self.settings.language = code
        self.settings.save()
        apply_language(code)
        QTimer.singleShot(0, self.build_ui)  # rebuild after the combo's signal has returned

    # ---------- tab: status
    def build_status_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        top = QHBoxLayout()
        self.status_label = QLabel(); self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.status_label, 1)
        lang = QHBoxLayout(); lang.addWidget(QLabel(tr("language"))); lang.addWidget(self.build_language_box())
        top.addLayout(lang); top.setAlignment(lang, Qt.AlignTop)
        lay.addLayout(top)
        row = QHBoxLayout()
        self.btn_new = QPushButton(tr("btn.sync_new")); self.btn_new.setToolTip(tr("btn.sync_new.tip"))
        self.btn_all = QPushButton(tr("btn.sync_all")); self.btn_all.setToolTip(tr("btn.sync_all.tip"))
        self.btn_sel = QPushButton(tr("btn.sync_select"))
        self.btn_cancel = QPushButton(tr("btn.stop")); self.btn_cancel.setEnabled(self.task is not None)
        btn_open = QPushButton(tr("btn.open_folder"))
        self.btn_new.clicked.connect(lambda: self.start_sync("new"))
        self.btn_all.clicked.connect(self.confirm_all)
        self.btn_sel.clicked.connect(self.open_select)
        self.btn_cancel.clicked.connect(lambda: self.task and self.task.cancel())
        btn_open.clicked.connect(lambda: self.open_path(self.settings.output_root))
        for b in (self.btn_new, self.btn_all, self.btn_sel, self.btn_cancel):
            row.addWidget(b)
        row.addStretch(); row.addWidget(btn_open)
        lay.addLayout(row)
        self.progress = QProgressBar(); self.progress.setVisible(self.task is not None); self.progress.setRange(0, 0)
        lay.addWidget(self.progress)

        lay.addWidget(QLabel(tr("status.recent")))
        self.activity = QTableWidget(0, 6)
        self.activity.setHorizontalHeaderLabels([tr("col.sync_time"), tr("col.type"), tr("col.number"),
                                                 tr("col.company"), tr("col.result"), tr("col.file")])
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
        conn = tr("status.connected", org=s.org_name or s.org_id) if s.connected else tr("status.not_connected")
        auto = tr("status.every_min", n=s.interval_min) if s.auto_sync else tr("status.off")
        last = self.last_sync.strftime("%H:%M:%S") if self.last_sync else tr("status.never")
        types = tr("status.list_sep").join(doctype_label(k) for k in s.doc_types) or tr("status.none_selected")
        self.status_label.setText(tr("status.summary", conn=conn, root=s.output_root, types=types, auto=auto, last=last))
        for b in (self.btn_new, self.btn_all, self.btn_sel):
            b.setEnabled(s.connected and self.task is None)
        self.tray.setToolTip(tr("status.tray_tip", app=tr("app.name"), last=last))

    def add_activity(self, job, outcome, path, error=""):
        entry = (datetime.now().strftime("%m-%d %H:%M"), job, outcome, path, error)
        self.activity_log.insert(0, entry)
        del self.activity_log[300:]
        self._insert_activity_row(*entry)

    def _insert_activity_row(self, when, job, outcome, path, error):
        self.activity.insertRow(0)
        vals = [when, doctype_label(job.doc.type.key), job.doc.number, job.doc.company or job.doc.customer,
                outcome_label(outcome, error), str(path or "")]
        for c, v in enumerate(vals):
            it = QTableWidgetItem(v)
            if outcome == engine.FAILED:
                it.setForeground(QColor("#c0392b"))
            self.activity.setItem(0, c, it)
        while self.activity.rowCount() > 300:
            self.activity.removeRow(self.activity.rowCount() - 1)

    # ---------- tab: connect
    def build_connect_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        s = self.settings
        mode_box = QGroupBox(tr("conn.method")); ml = QVBoxLayout(mode_box)
        self.rb_browser = QRadioButton(tr("conn.browser"))
        self.rb_manual = QRadioButton(tr("conn.manual"))
        grp = QButtonGroup(w); grp.addButton(self.rb_browser); grp.addButton(self.rb_manual)
        (self.rb_manual if s.auth_mode == "manual" else self.rb_browser).setChecked(True)
        ml.addWidget(self.rb_browser); ml.addWidget(self.rb_manual)
        lay.addWidget(mode_box)

        form = form_layout()
        self.dc_box = QComboBox()
        for k in DATA_CENTERS:
            self.dc_box.addItem(tr(f"dc.{k}", default=k), k)
        self.dc_box.setCurrentIndex(max(0, self.dc_box.findData(s.dc)))
        self.client_id = QLineEdit(s.client_id)
        self.client_secret = QLineEdit(get_secret("client_secret")); self.client_secret.setEchoMode(QLineEdit.Password)
        self.grant_code = QLineEdit(); self.grant_code.setPlaceholderText(tr("conn.code_hint"))
        form.addRow(tr("conn.region"), self.dc_box)
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
        copy_btn = QPushButton(tr("conn.copy"))
        copy_btn.clicked.connect(self.copy_help_value)
        copy_row.addWidget(self.copy_label); copy_row.addWidget(self.copy_value, 1); copy_row.addWidget(copy_btn)
        lay.addLayout(copy_row)

        row = QHBoxLayout()
        self.btn_connect = QPushButton(tr("conn.connect")); self.btn_connect.clicked.connect(self.connect_zoho)
        btn_disc = QPushButton(tr("conn.disconnect")); btn_disc.clicked.connect(self.disconnect_zoho)
        row.addWidget(self.btn_connect); row.addWidget(btn_disc); row.addStretch()
        lay.addLayout(row)

        org_row = QHBoxLayout()
        self.org_box = QComboBox()
        if s.org_id:
            self.org_box.addItem(s.org_name or s.org_id, s.org_id)
        self.org_box.currentIndexChanged.connect(self.org_changed)
        org_row.addWidget(QLabel(tr("conn.org"))); org_row.addWidget(self.org_box, 1)
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
        console = f"https://api-console.zoho.{self.dc_box.currentData() or 'com'}"
        from .zoho import REDIRECT_URI, SCOPES
        if manual:
            self.help.setText(tr("conn.help.manual", console=console))
            self.copy_label.setText("Scope"); self.copy_value.setText(SCOPES)
        else:
            self.help.setText(tr("conn.help.browser", console=console))
            self.copy_label.setText("Redirect URI"); self.copy_value.setText(REDIRECT_URI)
        self.copy_value.setCursorPosition(0)

    def copy_help_value(self):
        QApplication.clipboard().setText(self.copy_value.text())
        self.statusBar().showMessage(tr("conn.copied", what=self.copy_label.text()), 3000)

    def connect_zoho(self):
        dc = self.dc_box.currentData()
        cid, secret, code = self.client_id.text().strip(), self.client_secret.text().strip(), self.grant_code.text().strip()
        manual = self.rb_manual.isChecked()
        if not cid or not secret or (manual and not code):
            QMessageBox.warning(self, tr("conn.missing.title"),
                                tr("conn.missing.body_code" if manual else "conn.missing.body"))
            return
        self.conn_msg.setText(tr("conn.connecting" if manual else "conn.connecting_browser"))
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
                self.conn_msg.setText(tr("conn.no_org"))
            else:
                idx = max(0, self.org_box.findData(s.org_id))
                self.org_box.setCurrentIndex(idx); self.org_changed(idx)
                self.conn_msg.setText(tr("conn.ok", org=s.org_name) + (tr("conn.ok_many") if len(orgs) > 1 else ""))
                self.first_run_choice()
                QTimer.singleShot(0, self.refresh_quota)  # read live limits for the chosen org
            self.btn_connect.setEnabled(True)
            self.refresh_status()

        def fail(msg):
            self.conn_msg.setText(f"❌ {msg}")
            self.btn_connect.setEnabled(True)

        self.run_task(work, ok, fail, busy=False)

    def org_changed(self, idx):
        if idx < 0 or not self.org_box.itemData(idx):
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
        box.setWindowTitle(tr("conn.first.title"))
        box.setText(tr("conn.first.body"))
        today = box.addButton(tr("conn.first.today"), QMessageBox.AcceptRole)
        box.addButton(tr("conn.first.later"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is today:
            self.settings.since_date = date.today().isoformat()
            self.since_enabled.setChecked(True); self.since_date.setDate(QDate.currentDate())
            self.settings.save()

    def disconnect_zoho(self):
        if QMessageBox.question(self, tr("conn.disc.title"), tr("conn.disc.body")) != QMessageBox.Yes:
            return
        set_secret("refresh_token", "")
        self.settings.org_id = self.settings.org_name = ""
        self.settings.save(); self.org_box.clear()
        self.conn_msg.setText(tr("conn.disc.done")); self.refresh_status()

    # ---------- tab: sync settings
    def build_sync_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        s = self.settings
        types = QGroupBox(tr("sync.types")); tl = QHBoxLayout(types)
        self.type_checks = {}
        for t in engine.DOC_TYPES:
            cb = QCheckBox(doctype_label(t.key)); cb.setChecked(t.key in s.doc_types)
            cb.toggled.connect(self.save_sync)
            self.type_checks[t.key] = cb; tl.addWidget(cb)
        tl.addStretch()
        lay.addWidget(types)

        st = QGroupBox(tr("sync.skip")); sl = QHBoxLayout(st)
        self.status_checks = {}
        for k in ("draft", "void", "declined", "expired"):
            cb = QCheckBox(status_label(k)); cb.setChecked(k in s.skip_statuses)
            cb.toggled.connect(self.save_sync)
            self.status_checks[k] = cb; sl.addWidget(cb)
        sl.addStretch()
        lay.addWidget(st)

        form = form_layout()
        since_row = QHBoxLayout()
        self.since_enabled = QCheckBox(tr("sync.since"))
        self.since_date = QDateEdit(QDate.fromString(s.since_date, "yyyy-MM-dd") if s.since_date else QDate.currentDate())
        self.since_date.setCalendarPopup(True); self.since_date.setDisplayFormat("yyyy-MM-dd")
        self.since_enabled.setChecked(bool(s.since_date))
        self.since_enabled.toggled.connect(self.save_sync); self.since_date.dateChanged.connect(self.save_sync)
        since_row.addWidget(self.since_enabled); since_row.addWidget(self.since_date); since_row.addStretch()
        form.addRow(tr("sync.start_date"), since_row)

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(s.output_root); self.out_edit.editingFinished.connect(self.save_sync)
        browse = QPushButton(tr("sync.browse")); browse.clicked.connect(self.pick_folder)
        out_row.addWidget(self.out_edit, 1); out_row.addWidget(browse)
        form.addRow(tr("sync.storage"), out_row)

        self.template = QLineEdit(s.path_template)
        self.template.textChanged.connect(self.update_preview); self.template.editingFinished.connect(self.save_sync)
        form.addRow(tr("sync.template"), self.template)
        tip = QLabel(tr("sync.template.help")); tip.setWordWrap(True)
        tip.setTextInteractionFlags(Qt.TextSelectableByMouse); tip.setStyleSheet("color:gray")
        form.addRow("", tip)
        self.preview = QLabel(); self.preview.setStyleSheet("color:#1f7a4d")
        form.addRow(tr("sync.example"), self.preview)

        conflict = QWidget(); cl = QVBoxLayout(conflict); cl.setContentsMargins(0, 0, 0, 0)
        self.conflict_btns = {}
        for k in ("version", "overwrite", "skip"):
            rb = QRadioButton(tr(f"sync.conflict.{k}")); rb.setChecked(s.conflict == k); rb.toggled.connect(self.save_sync)
            self.conflict_btns[k] = rb; cl.addWidget(rb)
        form.addRow(tr("sync.conflict"), conflict)
        lay.addLayout(form)
        lay.addStretch()
        self.update_preview()
        return w

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, tr("sync.storage.pick"), self.out_edit.text())
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
            self.preview.setText(tr("sync.template.error", error=e))

    def save_sync(self, *_):
        s = self.settings
        s.doc_types = [k for k, cb in self.type_checks.items() if cb.isChecked()]
        s.skip_statuses = [k for k, cb in self.status_checks.items() if cb.isChecked()]
        s.since_date = self.since_date.date().toString("yyyy-MM-dd") if self.since_enabled.isChecked() else ""
        s.output_root = self.out_edit.text().strip() or s.output_root
        s.path_template = self.template.text().strip() or "{partner}/{type}/{number}.pdf"
        s.conflict = next(k for k, rb in self.conflict_btns.items() if rb.isChecked())
        s.save(); self.refresh_status(); self.refresh_quota_ui()

    # ---------- tab: customer folders
    def build_partner_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self._loading_partner = True
        self.partner_only = QCheckBox(tr("cust.only"))
        self.partner_only.setChecked(self.settings.partner_only)
        self.partner_only.toggled.connect(self.save_partners)
        lay.addWidget(self.partner_only)
        help_label = QLabel(tr("cust.help")); help_label.setWordWrap(True)
        lay.addWidget(help_label)
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.partner_list = QListWidget(); self.partner_list.currentRowChanged.connect(self.partner_selected)
        left.addWidget(self.partner_list)
        pr = QHBoxLayout()
        add = QPushButton(tr("cust.add")); add.clicked.connect(self.add_partner)
        rm = QPushButton(tr("cust.delete")); rm.clicked.connect(self.remove_partner)
        pr.addWidget(add); pr.addWidget(rm); left.addLayout(pr)
        body.addLayout(left, 1)

        right = QVBoxLayout()
        self.partner_name = QLineEdit(); self.partner_name.setPlaceholderText(tr("cust.name_hint"))
        self.partner_name.editingFinished.connect(self.save_partners)
        right.addWidget(QLabel(tr("cust.folder_name"))); right.addWidget(self.partner_name)
        right.addWidget(QLabel(tr("cust.companies")))
        self.partner_companies = QPlainTextEdit()
        self.partner_companies.textChanged.connect(self.save_partners)
        right.addWidget(self.partner_companies)
        pick = QPushButton(tr("cust.pick")); pick.clicked.connect(self.pick_companies)
        right.addWidget(pick)
        body.addLayout(right, 2)
        lay.addLayout(body)
        self._loading_partner = False
        self.reload_partner_list()
        return w

    def partner_item_text(self, p: Partner) -> str:
        return tr("cust.item", name=p.name, n=len(p.companies))

    def reload_partner_list(self, select: int = 0):
        self.partner_list.blockSignals(True); self.partner_list.clear()
        for p in self.settings.partners:
            self.partner_list.addItem(self.partner_item_text(p))
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
        self.settings.partners.append(Partner(tr("cust.default_name", n=len(self.settings.partners) + 1), []))
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
            self.partner_list.item(row).setText(self.partner_item_text(p))
        self.settings.save()

    def pick_companies(self):
        row = self.partner_list.currentRow()
        if not (0 <= row < len(self.settings.partners)):
            return
        if not self.settings.connected:
            QMessageBox.warning(self, tr("cust.not_connected.title"), tr("cust.not_connected.body"))
            return
        dlg = CompanyPicker(self.settings, row, self)
        if not dlg.exec():
            return
        chosen = dlg.chosen()
        chosen_norm = {engine.norm_company(c) for c in chosen}
        # move: drop chosen companies from every other customer folder
        for i, p in enumerate(self.settings.partners):
            if i != row:
                p.companies = [c for c in p.companies if engine.norm_company(c) not in chosen_norm]
        self.settings.partners[row].companies = chosen
        self.settings.save()
        self.reload_partner_list(row)

    # ---------- tab: auto sync
    def build_auto_tab(self):
        w = QWidget(); lay = form_layout(w)
        s = self.settings
        self.auto_cb = QCheckBox(tr("auto.enable")); self.auto_cb.setChecked(s.auto_sync)
        self.interval = QSpinBox(); self.interval.setRange(5, 240); self.interval.setSuffix(tr("auto.minutes"))
        self.interval.setValue(s.interval_min)
        self.login_cb = QCheckBox(tr("auto.login")); self.login_cb.setChecked(s.start_at_login)
        self.notify_cb = QCheckBox(tr("auto.notify")); self.notify_cb.setChecked(s.notify)
        for wd in (self.auto_cb, self.login_cb, self.notify_cb):
            wd.toggled.connect(self.save_auto)
        self.interval.valueChanged.connect(self.save_auto)
        lay.addRow(self.auto_cb)
        lay.addRow(tr("auto.interval"), self.interval)
        lay.addRow(self.login_cb)
        lay.addRow(self.notify_cb)
        note = QLabel(tr("auto.note"))
        note.setWordWrap(True); note.setStyleSheet("color:gray")
        lay.addRow(note)

        box = QGroupBox(tr("quota.box")); bl = form_layout(box)
        self.q_plan, self.q_daily, self.q_minute = QLabel(), QLabel(), QLabel()
        self.q_remaining, self.q_reset, self.q_local, self.q_estimate = QLabel(), QLabel(), QLabel(), QLabel()
        for lab in (self.q_plan, self.q_daily, self.q_minute, self.q_remaining, self.q_reset, self.q_local, self.q_estimate):
            lab.setWordWrap(True); lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addRow(tr("quota.plan"), self.q_plan)
        bl.addRow(tr("quota.daily"), self.q_daily)
        bl.addRow(tr("quota.minute"), self.q_minute)
        bl.addRow(tr("quota.remaining"), self.q_remaining)
        bl.addRow(tr("quota.reset"), self.q_reset)
        bl.addRow(tr("quota.local"), self.q_local)
        bl.addRow(tr("quota.estimate"), self.q_estimate)
        self.q_refresh = QPushButton(tr("quota.refresh")); self.q_refresh.clicked.connect(self.refresh_quota)
        self.q_refresh.setEnabled(getattr(self, "_quota_task", None) is None)
        bl.addRow("", self.q_refresh)
        hint = QLabel(tr("quota.hint"))
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
                QMessageBox.warning(self, tr("auto.login_failed.title"), tr("auto.login_failed.body", error=e))
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
        task.failed.connect(lambda m: self.statusBar().showMessage(tr("quota.failed", error=m), 8000))
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
        if not hasattr(self, "q_plan"):
            return
        v, s = self.quota_view(), self.settings
        unknown = tr("common.unknown")
        plan = v["plan"] or unknown
        limit = f"{v['limit']:,}" if v["limit"] else unknown
        if v["remaining"] is not None and v["limit"]:
            rem = f"{v['remaining']:,} / {limit}"
            low = v["remaining"] < v["limit"] * 0.1
        else:
            rem, low = tr("quota.no_data"), False
        reset = datetime.fromtimestamp(v["reset_at"]).strftime("%H:%M") if v["reset_at"] else unknown
        upd = datetime.fromtimestamp(v["updated_at"]).strftime("%H:%M") if v["updated_at"] else None
        per_cycle = max(1, len(s.doc_types))
        per_day = (24 * 60 // max(1, s.interval_min)) * per_cycle
        est = tr("quota.est", interval=s.interval_min, types=per_cycle, per_day=f"{per_day:,}")
        if v["limit"]:
            pct = per_day * 100 // v["limit"]
            est += tr("quota.est_pct", pct=pct)
            if s.auto_sync and pct >= 50:
                est = "⚠️ " + est + tr("quota.est_warn")
        if not s.auto_sync:
            est += tr("quota.est_off")
        self.q_plan.setText(plan)
        self.q_daily.setText(tr("quota.daily_value", limit=limit))
        self.q_minute.setText(tr("common.calls", n=f"{v['per_minute']:,}") if v["per_minute"] else unknown)
        self.q_remaining.setText(rem + (tr("quota.updated", time=upd) if upd else ""))
        self.q_remaining.setStyleSheet("color:#c0392b" if low else "")
        self.q_reset.setText(reset)
        self.q_local.setText(tr("common.calls", n=f"{v['local_used']:,}"))
        self.q_estimate.setText(est)
        short_rem = f"{v['remaining']:,} / {limit}" if v["remaining"] is not None and v["limit"] else "—"
        self.quota_label.setText(tr("quota.bar", plan=plan, remaining=short_rem)
                                 + (tr("quota.bar_reset", time=reset) if v["reset_at"] else "")
                                 + tr("quota.bar_local", n=f"{v['local_used']:,}"))
        self.quota_label.setStyleSheet("color:#c0392b" if low else "")

    def apply_auto(self):
        self.timer.stop()
        if self.settings.auto_sync:
            self.timer.start(self.settings.interval_min * 60_000)
        self.pause_action.blockSignals(True)
        self.pause_action.setChecked(not self.settings.auto_sync)
        self.pause_action.blockSignals(False)

    # ---------- tray
    def build_tray_menu(self):
        menu = QMenu(self)
        menu.addAction(tr("tray.open"), self.show_window)
        menu.addAction(tr("tray.sync_now"), lambda: self.start_sync("new"))
        menu.addAction(tr("btn.open_folder"), lambda: self.open_path(self.settings.output_root))
        self.pause_action = QAction(tr("tray.pause"), menu, checkable=True)
        self.pause_action.setChecked(not self.settings.auto_sync)
        self.pause_action.toggled.connect(self.toggle_pause)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(tr("tray.quit"), self.quit_app)
        old = self.tray.contextMenu()
        self.tray.setContextMenu(menu)
        if old is not None:
            old.deleteLater()

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
            self.tray.showMessage(tr("app.name"), tr("tray.still_running"))
            self._told_tray = True

    def quit_app(self):
        self.quitting = True
        if self.task:
            self.task.cancel(); self.task.wait(5000)
        QApplication.quit()

    # ---------- sync
    def confirm_all(self):
        if QMessageBox.question(self, tr("sync.all.title"), tr("sync.all.body")) == QMessageBox.Yes:
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
                task.report(0, 0, tr("sync.reading"))
                found = engine.list_documents(client, s.doc_types, max_pages=None if mode == "all" else 1,
                                              cancelled=task.cancelled)
            else:
                found = docs
            jobs = engine.plan(found, s, state, mode=mode, selected=keys)
            results = engine.run(client, jobs, s, state, cancelled=task.cancelled, save=save_state,
                                 progress=lambda i, n, j, o: task.report(i, n, f"{j.doc.number} {outcome_label(o)}"))
            save_state(state)
            return results, client.calls

        def ok(result):
            results, calls = result
            self.last_sync = datetime.now()
            for job, outcome, path, error in results:
                self.add_activity(job, outcome, path, error)
                log.info("%s %s %s %s %s", job.doc.type.key, job.doc.number, outcome, path, error)
            new = [r for r in results if r[1] in engine.WRITTEN]
            bad = [r for r in results if r[1] == engine.FAILED]
            log.info("sync %s: %d written, %d failed, %d api calls", mode, len(new), len(bad), calls)
            if self.settings.notify and (new or bad):
                msg = tr("sync.done", n=len(new)) + (tr("sync.done_failed", n=len(bad)) if bad else "")
                self.tray.showMessage(tr("app.name"), msg,
                                      QSystemTrayIcon.Warning if bad else QSystemTrayIcon.Information)
            if not silent and not results:
                self.statusBar().showMessage(tr("sync.nothing"), 5000)

        def fail(msg):
            log.error("sync failed: %s", msg)
            if silent:
                if self.settings.notify:
                    self.tray.showMessage(tr("sync.failed_title", app=tr("app.name")), msg, QSystemTrayIcon.Warning)
            else:
                QMessageBox.warning(self, tr("sync.failed"), msg)

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
