"""Native Qt desktop workspace. No embedded web browser or local HTTP server."""

import argparse
import html
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QLockFile, Qt, QThread, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QTextCursor, QTextBlockFormat, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QInputDialog,
    QTextBrowser,
    QTabWidget,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from . import desktop_backend as backend
from .desktop_logs import summarize_logs, error_summary
from .article_provenance import overview_html, original_html

BEIJING = timezone(timedelta(hours=8))
STAGES = {
    "taxonomy": "媒体分类",
    "research": "资料研究",
    "writer": "文章写作",
    "review": "稿件审阅",
}
STATE_NAMES = {
    "completed": "已完成",
    "not_available": "未出现卡片",
    "supplement_unavailable": "补充未取得",
    "pending": "等待",
    "submitted": "已提交",
    "ready": "可用",
    "waiting_for_model": "等待 API 处理",
    "accepted": "阶段已验收",
    "revision_requested": "已退回修订",
    "needs_attention": "需要处理",
    "idle": "暂无任务",
    "connection_or_delivery_error": "交接异常",
    "not_started": "尚未启动",
    "waiting_prerequisites": "等待采集、文章和本地交付全部通过",
    "observing": "连续观测中",
    "passed": "已通过",
    "failed": "失败，需处理",
    "requesting": "API 处理中",
    "waiting_05": "等待每日 05:00",
}
STYLE = """
QTextBrowser { background: white; border: 1px solid #d9dde4; border-radius: 7px; padding: 14px; }
QTabWidget::pane { border: 0; }
QTabBar::tab { padding: 9px 16px; background: #eef0f4; color: #626b79; border: 0; }
QTabBar::tab:selected { background: white; color: #2469bd; }
QWidget { color: #24262b; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 14px; }
QMainWindow, QWidget#main { background: #f6f7f9; }
QFrame#sidebar { background: #eceef2; border-right: 1px solid #dfe2e7; }
QLabel#heading { font-size: 23px; font-weight: 600; }
QLabel#brand { font-size: 17px; font-weight: 600; }
QLabel#muted { color: #737983; }
QLabel#metric { font-size: 29px; font-weight: 500; }
QFrame#card { background: white; border: 1px solid #e4e6eb; border-radius: 10px; }
QFrame#notice { background: #fff8ea; border: 1px solid #f0deb8; border-radius: 9px; }
QPushButton { background: white; border: 1px solid #d9dde4; border-radius: 7px; padding: 8px 14px; }
QPushButton:hover { background: #f0f3f8; }
QPushButton:pressed { background: #e7edf6; }
QPushButton:disabled { color: #9aa0aa; background: #f2f3f5; }
QPushButton#primary { color: white; background: #2676e6; border: 1px solid #2676e6; }
QPushButton#primary:hover { background: #1d67cf; }
QPushButton#primary:disabled { background: #e6ebf2; color: #8d97a5; border-color: #e1e5eb; }
QLineEdit, QComboBox, QTimeEdit, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #dfe2e8; border-radius: 7px; padding: 8px 10px; }
QComboBox::drop-down { border: none; width: 24px; }
QListWidget#nav { background: transparent; border: none; outline: none; }
QListWidget#nav::item { padding: 12px 15px; margin: 3px 0; border-radius: 7px; }
QListWidget#nav::item:selected { background: #dce7f8; color: #1759ae; }
QTableWidget { background: white; border: 1px solid #e4e6eb; border-radius: 8px; gridline-color: transparent; outline: none; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { color: #174779; background: #e8f0fb; }
QHeaderView::section { background: #fafbfc; color: #69717e; border: none; border-bottom: 1px solid #e9ebef; padding: 10px; }
QPlainTextEdit { background: white; border: 1px solid #e4e6eb; border-radius: 8px; padding: 12px; }
QProgressBar { background: #edf0f5; border: none; border-radius: 3px; height: 6px; }
QProgressBar::chunk { background: #2676e6; border-radius: 3px; }
QSplitter::handle { background: #f6f7f9; width: 12px; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #c8cdd5; border-radius: 4px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def label(text="", name=None):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(True)
    if name:
        item.setObjectName(name)
    return item


def clock(epoch):
    return (
        datetime.fromtimestamp(epoch, BEIJING).strftime("%m-%d %H:%M:%S")
        if epoch
        else "暂无记录"
    )


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(11)
    return frame, layout


class Worker(QThread):
    result = Signal(dict)
    error = Signal(str)

    def __init__(self, config, action="refresh", argument=None):
        super().__init__()
        self.config, self.action, self.argument = config, action, argument

    def run(self):
        try:
            function = {
                "refresh": backend.refresh,
                "sync": backend.synchronize,
                "relay": backend.relay_control,
                "control": backend.pipeline_control,
            }[self.action]
            result = (
                function(self.config)
                if self.argument is None
                else function(self.config, self.argument)
            )
            self.result.emit(result)
        except Exception as error:  # noqa: BLE001 -- background task errors must reach the UI without terminating Qt
            self.error.emit(type(error).__name__)


class Window(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.data, self.worker, self.preview_for, self.closing = {}, None, None, False
        self.setWindowTitle("内容工作台")
        self.resize(1220, 820)
        self.setMinimumSize(980, 700)
        main = QWidget()
        main.setObjectName("main")
        self.setCentralWidget(main)
        layout = QHBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 31, 22, 24)
        side.setSpacing(24)
        side.addWidget(label("内容工作台", "brand"))
        side.addWidget(label("媒体分析与文章生产", "muted"))
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.addItems(
            ["生产总览", "文章库", "任务与诊断", "计划与费用", "运行日志"]
        )
        self.nav.setMaximumHeight(270)
        side.addWidget(self.nav)
        side.addStretch()
        self.schedule_label = label("每日 05:00 开始采集\n每类最多 10 篇", "muted")
        side.addWidget(self.schedule_label)
        side.addWidget(label("本地桌面 · Qt", "muted"))
        layout.addWidget(sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(32, 28, 32, 24)
        content.setSpacing(22)
        header = QHBoxLayout()
        self.heading = label("生产总览", "heading")
        header.addWidget(self.heading)
        header.addStretch()
        self.connection = label("正在读取状态", "muted")
        self.connection.setWordWrap(False)
        header.addWidget(self.connection)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(lambda: self.run())
        header.addWidget(self.refresh_button)
        content.addLayout(header)
        self.pages = QStackedWidget()
        content.addWidget(self.pages, 1)
        self.make_overview()
        self.make_library()
        self.make_diagnostics()
        self.make_settings()
        self.make_logs()
        self.footer = label("正在连接服务器；后台文件交接独立运行。", "muted")
        content.addWidget(self.footer)
        layout.addLayout(content, 1)
        self.nav.currentRowChanged.connect(self.navigate)
        self.nav.setCurrentRow(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.run())
        self.timer.start(30000)
        QTimer.singleShot(100, lambda: self.run())

    def make_overview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        self.subtitle = label("", "muted")
        layout.addWidget(self.subtitle)
        notice = QFrame()
        notice.setObjectName("notice")
        row = QVBoxLayout(notice)
        row.setContentsMargins(16, 13, 16, 13)
        self.notice = label("正在核验运行状态")
        row.addWidget(self.notice)
        layout.addWidget(notice)
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.metrics = []
        for title in ("动态类别", "批次计划", "暂定通过", "需要处理"):
            frame, inner = card()
            inner.addWidget(label(title, "muted"))
            value = label("—", "metric")
            inner.addWidget(value)
            self.metrics.append(value)
            stats.addWidget(frame)
        layout.addLayout(stats)
        frame, inner = card()
        inner.addWidget(label("批次进度"))
        self.progress_caption = label("", "muted")
        inner.addWidget(self.progress_caption)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        inner.addWidget(self.progress)
        self.current_task = label("", "muted")
        inner.addWidget(self.current_task)
        self.capture_progress = label("", "muted")
        inner.addWidget(self.capture_progress)
        layout.addWidget(frame)
        frame, inner = card()
        inner.addWidget(label("运行环境"))
        self.service_labels = []
        for text in ("服务器队列", "DeepSeek 登录", "本机文件交接", "每日写作调度"):
            row = QHBoxLayout()
            row.addWidget(label(text))
            row.addStretch()
            value = label("核验中", "muted")
            row.addWidget(value)
            self.service_labels.append(value)
            inner.addLayout(row)
        self.resources = label("", "muted")
        inner.addWidget(self.resources)
        layout.addWidget(frame)
        buttons = QHBoxLayout()
        self.sync_button = QPushButton("同步已验收文章")
        self.sync_button.setObjectName("primary")
        self.sync_button.clicked.connect(lambda: self.run("sync"))
        buttons.addWidget(self.sync_button)
        open_button = QPushButton("打开文章目录")
        open_button.clicked.connect(
            lambda: (
                self.open_path(Path(self.data["root"]) / "articles")
                if self.data
                else None
            )
        )
        buttons.addWidget(open_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addStretch()
        self.pages.addWidget(page)

    def make_library(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        filters = QHBoxLayout()
        self.date_filter, self.category_filter = QComboBox(), QComboBox()
        self.library_initialized = False
        self.date_filter.addItem("全部日期")
        self.category_filter.addItem("全部类别")
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索文章标题")
        filters.addWidget(self.date_filter)
        filters.addWidget(self.category_filter, 1)
        filters.addWidget(self.search, 1)
        layout.addLayout(filters)
        for control in (self.date_filter, self.category_filter):
            control.currentTextChanged.connect(self.filter_articles)
        self.search.textChanged.connect(self.filter_articles)
        self.library_caption = label("等待读取本地归档", "muted")
        layout.addWidget(self.library_caption)
        split = QSplitter(Qt.Orientation.Vertical)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(12)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文章标题", "类别", "日期", "状态"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.setMinimumHeight(150)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.select_article)
        split.addWidget(self.table)
        preview = QWidget()
        box = QVBoxLayout(preview)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(10)
        self.article_title = label("选择文章查看正文")
        reading_bar = QHBoxLayout()
        reading_bar.addWidget(self.article_title, 1)
        self.reading_button = QPushButton("专注阅读")
        self.reading_button.setCheckable(True)
        self.reading_button.toggled.connect(self.toggle_reading)
        reading_bar.addWidget(self.reading_button)
        box.addLayout(reading_bar)
        self.article_title.setMinimumHeight(32)
        tabs = QTabWidget()
        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)
        self.preview.document().setDefaultStyleSheet("body {font-size:14px;} p {line-height:1.7; margin-bottom:12px;} h1 {font-size:22px;} h2 {font-size:18px;}")
        tabs.addTab(self.preview, "正文预览")
        self.source_preview = QTextBrowser()
        self.source_preview.setOpenExternalLinks(True)
        source_page = QWidget()
        source_layout = QVBoxLayout(source_page)
        self.source_choice = QComboBox()
        self.source_choice.currentIndexChanged.connect(self.show_source)
        source_layout.addWidget(self.source_choice)
        source_layout.addWidget(self.source_preview, 1)
        tabs.addTab(source_page, "原文与证据")
        self.review_preview = QTextBrowser()
        tabs.addTab(self.review_preview, "验收说明与记录")
        box.addWidget(tabs)
        preview.setMinimumHeight(220)
        split.addWidget(preview)
        split.setSizes([180, 340])
        layout.addWidget(split, 1)
        buttons = QHBoxLayout()
        self.word_button = QPushButton("打开完整 Word")
        self.word_button.setObjectName("primary")
        self.word_button.setEnabled(False)
        self.word_button.clicked.connect(lambda: self.open_selected("word"))
        buttons.addWidget(self.word_button)
        self.folder_button = QPushButton("打开所在文件夹")
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(lambda: self.open_selected("folder"))
        buttons.addWidget(self.folder_button)
        approve = QPushButton("验收通过")
        approve.clicked.connect(lambda: self.record_review("approved"))
        buttons.addWidget(approve)
        reject = QPushButton("退回并记录原因")
        reject.clicked.connect(lambda: self.record_review("rejected"))
        buttons.addWidget(reject)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.pages.addWidget(page)

    def make_diagnostics(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        self.diagnostic_caption = label("", "muted")
        layout.addWidget(self.diagnostic_caption)
        self.attention_table = QTableWidget(0, 5)
        self.attention_table.setHorizontalHeaderLabels(["日期", "类别", "篇号", "阶段", "具体问题"])
        self.attention_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.attention_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.attention_table.verticalHeader().setVisible(False)
        for column in range(4):
            self.attention_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.attention_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.attention_table.setWordWrap(True)
        self.attention_table.itemSelectionChanged.connect(self.show_task_detail)
        layout.addWidget(self.attention_table, 1)
        self.task_detail = QTextBrowser()
        self.task_detail.setMaximumHeight(160)
        layout.addWidget(self.task_detail)
        technical = QPushButton("展开技术详情")
        technical.setCheckable(True)
        technical.toggled.connect(lambda checked: self.diagnostics.setVisible(checked))
        layout.addWidget(technical)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setVisible(False)
        layout.addWidget(self.diagnostics, 1)
        row = QHBoxLayout()
        pause = QPushButton("暂停文件交接")
        pause.clicked.connect(lambda: self.run("relay", False))
        row.addWidget(pause)
        start = QPushButton("启动文件交接")
        start.clicked.connect(lambda: self.run("relay", True))
        row.addWidget(start)
        row.addStretch()
        layout.addLayout(row)
        row = QHBoxLayout()
        instructions = QPushButton("复制运行说明")
        instructions.clicked.connect(self.copy_runbook)
        row.addWidget(instructions)
        evidence = QPushButton("打开中间产物目录")
        evidence.clicked.connect(
            lambda: (
                self.open_path(Path(self.data["root"]) / "diagnostics")
                if self.data
                else None
            )
        )
        row.addWidget(evidence)
        row.addStretch()
        layout.addLayout(row)
        self.pages.addWidget(page)

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        self.heading.setText(
            ["生产总览", "文章库", "任务与诊断", "计划与费用", "运行日志"][index]
        )

    def make_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            label(
                "北京时间开始采集，采集完成后分析与写作。每题每平台一轮；没有百度卡片时照常采集文心。",
                "muted",
            )
        )
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.start_time = QTimeEdit(QTime(5, 0))
        self.start_time.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.start_time.setDisplayFormat("HH:mm")
        form.addRow("每日开始采集", self.start_time)
        self.setting_fields = {}
        for key, title, low, high, default in (
            ("max_per_category", "每类每日最多篇数", 1, 100, 10),
            ("deepseek_interval", "DeepSeek 提问间隔（秒）", 300, 600, 600),
            ("article_budget_cny", "单篇预算（含共享分析，元）", 0.01, 1000, 0.20),
            ("daily_budget_cny", "每日 API 预算（元）", 0.01, 1000, 10),
            ("test_budget_cny", "开发测试累计预算（元）", 0.01, 1000, 0.50),
        ):
            field = QSpinBox() if isinstance(default, int) else QDoubleSpinBox()
            field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            field.setRange(low, high)
            field.setValue(default)
            if isinstance(field, QDoubleSpinBox):
                field.setDecimals(2)
                field.setSingleStep(0.05)
            self.setting_fields[key] = field
            form.addRow(title, field)
        layout.addLayout(form)
        self.save_settings_button = QPushButton("保存任务设置")
        self.save_settings_button.clicked.connect(self.save_task_settings)
        layout.addWidget(self.save_settings_button)
        self.cost_caption = label("", "muted")
        layout.addWidget(self.cost_caption)
        self.cost_detail = label("", "muted")
        layout.addWidget(self.cost_detail)
        self.control_caption = label("")
        layout.addWidget(self.control_caption)
        row = QHBoxLayout()
        self.recheck_button = QPushButton("重新检测环境")
        self.recheck_button.clicked.connect(
            lambda: self.run("control", {"action": "recheck"})
        )
        self.resume_button = QPushButton("继续任务")
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(
            lambda: self.run("control", {"action": "resume"})
        )
        self.pause_button = QPushButton("暂停任务")
        self.pause_button.clicked.connect(
            lambda: self.run("control", {"action": "pause"})
        )
        for button in (self.recheck_button, self.resume_button, self.pause_button):
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(
            label(
                "超预算、掉登录或余额不足都会暂停。登录或充值后不会自动恢复；请先检测，再继续。预算按高峰单价保守预留，显示估算费用，实际扣费以平台账单为准。",
                "muted",
            )
        )
        layout.addStretch()
        self.settings_loaded = False
        self.pages.addWidget(page)

    def save_task_settings(self):
        values = {key: field.value() for key, field in self.setting_fields.items()}
        values["start_time"] = self.start_time.time().toString("HH:mm")
        self.run("control", {"action": "settings", "settings": values})

    def make_logs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            label(
                "服务器最近 150 条运行日志，每 30 秒刷新。完整记录保存在服务器 logs/日期.jsonl。",
                "muted",
            )
        )
        self.runtime_logs = QPlainTextEdit()
        self.runtime_logs.setReadOnly(True)
        row = QHBoxLayout()
        self.log_view = QComboBox()
        self.log_view.addItems(["中文摘要", "只看异常", "技术详情"])
        self.log_view.currentIndexChanged.connect(self.filter_logs)
        row.addWidget(self.log_view)
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("搜索日志：阶段、类别、错误、票据编号…")
        self.log_search.textChanged.connect(self.filter_logs)
        row.addWidget(self.log_search)
        export = QPushButton("导出当前日志")
        export.clicked.connect(self.export_logs)
        row.addWidget(export)
        layout.addLayout(row)
        self.log_lines = []
        self.log_summaries = []
        layout.addWidget(self.runtime_logs)
        self.pages.addWidget(page)

    def filter_logs(self):
        query = self.log_search.text().strip().casefold()
        bar = self.runtime_logs.verticalScrollBar()
        position, at_end = bar.value(), bar.value() == bar.maximum()
        mode = self.log_view.currentIndex()
        lines = self.log_lines if mode == 2 else [item['text'] for item in self.log_summaries if mode != 1 or item['failed']]
        self.runtime_logs.setPlainText("\n\n".join(line for line in lines if query in line.casefold()))
        bar.setValue(bar.maximum() if at_end else position)

    def export_logs(self):
        if not self.data:
            return
        path = Path(self.data["root"]) / "diagnostics" / ("panel-log-" + datetime.now(BEIJING).strftime("%Y%m%d-%H%M%S") + ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.runtime_logs.toPlainText(), encoding="utf-8-sig")
        self.footer.setText("日志已导出：" + str(path))
        self.open_path(path.parent)

    def run(self, action="refresh", argument=None):
        if self.worker and self.worker.isRunning():
            return
        self.connection.setText("正在同步" if action == "sync" else "正在读取状态")
        self.refresh_button.setEnabled(False)
        self.sync_button.setEnabled(False)
        for button in (
            self.recheck_button,
            self.resume_button,
            self.pause_button,
            self.save_settings_button,
        ):
            button.setEnabled(False)
        self.worker = Worker(self.config, action, argument)
        self.worker.result.connect(self.apply)
        self.worker.error.connect(self.failed)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        self.refresh_button.setEnabled(True)
        self.sync_button.setEnabled(True)
        for button in (
            self.recheck_button,
            self.pause_button,
            self.save_settings_button,
        ):
            button.setEnabled(True)
        if self.closing:
            QApplication.quit()

    def failed(self, kind):
        self.connection.setText("无法核验")
        self.notice.setText(
            "当前操作失败：" + kind + "。保留上次数据，未重新发送任务。"
        )
        self.footer.setText("操作失败；查看诊断或检查连接后刷新。")

    def apply(self, data):
        self.data = data
        server = data.get("server") or {}
        days = server.get("days") or []
        latest = days[0] if days else {}
        health = server.get("health") or {}
        connected = data["connection"] == "connected"
        self.connection.setText(
            "服务器已连接" if connected else "连接未核验 · 显示缓存"
        )
        today = datetime.now(BEIJING).date().isoformat()
        batch_date = latest.get("date", "暂无批次")
        self.subtitle.setText(
            f"{today}  ·  最近验收批次 {batch_date}"
            + ("  ·  今日采集尚未进入文章生产" if batch_date != today else "")
        )
        current_attention = [item for item in server.get("attention", []) if item.get("date") == batch_date]
        counts = {**health.get("counts", {}), "needs_attention": len(current_attention)}
        values = [
            latest.get("categories", "—"),
            latest.get("planned_articles", "—"),
            latest.get("accepted_articles", 0),
            counts.get("needs_attention", 0),
        ]
        for widget, value in zip(self.metrics, values):
            widget.setText(str(value))
        total = int(latest.get("planned_articles") or 0)
        accepted = int(latest.get("accepted_articles") or 0)
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(accepted)
        self.progress_caption.setText(
            f"已通过自动检查 {accepted} / {total} 篇；最终内容由你验收。"
        )
        active, relay = server.get("api") or {}, data.get("relay") or {}
        local_today = [a for a in data.get("articles", []) if a.get("date") == batch_date]
        user_accepted = sum(a.get("user_review", {}).get("decision") == "approved" for a in local_today)
        self.current_task.setText(
            f"信源正文 {latest.get('media_articles', 0)} 篇 → 分类 {latest.get('categories', 0)} 类 → 本机已收到 {len(local_today)} 篇 → 你已验收 {user_accepted} 篇\n"
            + (f"当前等待处理 {len(current_attention)} 篇失败稿，没有继续自动修订。" if current_attention else "当前阶段：" + STAGES.get(active.get("stage"), STATE_NAMES.get(active.get("status"), "等待任务")))
        )
        self.capture_progress.setText("今日采集  " + "  ·  ".join(
            name + "：" + " / ".join(f"{('已检查' if key == 'baidu_ai' and k == 'completed' else STATE_NAMES.get(k, k))} {v}" for k, v in states.items())
            for key, name in (("deepseek", "DeepSeek"), ("wenxin_card", "文心"), ("baidu_ai", "百度补充"))
            if (states := server.get("captures", {}).get(key))
        ))
        self.attention_table.setRowCount(len(current_attention))
        for row, item in enumerate(current_attention):
            for column, value in enumerate((item.get("date"), item.get("category"), item.get("number"), STAGES.get(item.get("stage"), item.get("stage")), item.get("error"))):
                cell = QTableWidgetItem(error_summary(value) if column == 4 else str(value or ""))
                cell.setToolTip(str(value or ""))
                cell.setData(Qt.ItemDataRole.UserRole, item)
                self.attention_table.setItem(row, column, cell)
        self.attention_table.resizeRowsToContents()
        self.show_task_detail()
        coordinator = server.get("services", {}).get(
            "geo-editorial-coordinator.service", {}
        )
        self.service_labels[0].setText(
            "运行中"
            if connected and coordinator.get("ActiveState") == "active"
            else "未核验"
        )
        session = server.get("deepseek") or {}
        session_fresh = time.time() - float(session.get("checked_epoch") or 0) < 420
        self.service_labels[1].setText(
            "已登录"
            if connected and session_fresh and session.get("status") == "ready"
            else "需要登录"
            if session.get("status") == "login_required"
            else "状态待核验"
        )
        relay_fresh = time.time() - float(relay.get("checked_epoch") or 0) < 120
        self.service_labels[2].setText(
            STATE_NAMES.get(relay.get("status"), relay.get("status", "未启动"))
            if relay_fresh
            else "状态已过期"
        )
        schedule = server.get("schedule") or {}
        config = server.get("settings") or {}
        if config and not self.settings_loaded:
            self.start_time.setTime(QTime.fromString(config["start_time"], "HH:mm"))
            for key, field in self.setting_fields.items():
                field.setValue(config[key])
            self.settings_loaded = True
        self.schedule_label.setText(
            f"每日 {config.get('start_time', '05:00')} 开始采集\n每类最多 {config.get('max_per_category', 10)} 篇"
        )
        control, checked = (
            server.get("control") or {},
            server.get("environment_check") or {},
        )
        self.resume_button.setEnabled(
            connected
            and control.get("paused", False)
            and checked.get("ok", False)
            and checked.get("control_revision") == control.get("revision", 0)
            and 0 <= time.time() - checked.get("checked_epoch", 0) <= 300
        )
        self.control_caption.setText(
            ("已暂停：" + control.get("message", ""))
            if control.get("paused")
            else f"当前批次有 {len(current_attention)} 篇待处理；自动写作正在等待。" if current_attention
            else "任务已启用，按计划运行。"
        )
        costs = server.get("costs") or {}
        balance = server.get("balance") or {}
        self.cost_caption.setText(
            f"已记录估算费用 {costs.get('estimated_cny', 0):.4f} 元 · 尚未结算预留 {costs.get('reserved_cny', 0):.4f} 元\n最近余额："
            + " / ".join(
                str(i.get("total_balance")) + " " + str(i.get("currency"))
                for i in balance.get("balance_infos", [])
            )
        )
        self.cost_detail.setText(
            "其中开发测试估算 "
            + f"{costs.get('test_estimated_cny', 0):.4f} 元"
            + "；"
            + " · ".join(
                STAGES.get(i["stage"], i["stage"])
                + f" {i['estimated_cny'] or 0:.4f} 元"
                for i in costs.get("by_stage", [])
            )
        )
        lines = []
        for item in server.get("runtime_logs", []):
            fields = {
                k: v for k, v in item.items() if k not in {"epoch", "phase", "message"}
            }
            lines.append(
                clock(item.get("epoch"))
                + "  ["
                + item.get("phase", "")
                + "]  "
                + item.get("message", "")
                + ("  " + json.dumps(fields, ensure_ascii=False) if fields else "")
            )
        self.log_lines = lines
        self.log_summaries = summarize_logs(server.get("runtime_logs", []), server.get("attention", []))
        self.filter_logs()
        self.service_labels[3].setText(
            "已暂停"
            if control.get("paused")
            else "每日 " + config.get("start_time", "05:00")
        )
        soak = server.get("soak") or {}
        schedule_note = (
            "DeepSeek API 每日调度待核验"
            if schedule.get("status") != "enabled"
            else "服务器 DeepSeek Flash API 调度已启用"
        )
        soak_note = (
            "六小时无人值守验收尚未启动"
            if soak.get("status") == "not_started"
            else "六小时测试状态："
            + STATE_NAMES.get(soak.get("status"), soak.get("status", "待核验"))
        )
        self.notice.setText(
            f"今天已交付 {accepted}/{total} 篇，{len(current_attention)} 篇需要处理。文章仍需你验收。"
            if connected
            else "当前无法连接服务器核验；以下为最近保存的数据。"
        )
        current_capture_attention = [item for item in server.get("capture_attention", []) if str(item.get("batch", "")).startswith(today + "-")]
        if current_capture_attention:
            self.notice.setText(
                self.notice.text() + " 采集存在待处理问题，详见任务与诊断。"
            )
        if control.get("paused"):
            self.notice.setText(
                "任务已暂停："
                + control.get("message", "")
                + "。到“计划与费用”重新检测环境后继续。"
            )
        if data.get("operation"):
            operation = data["operation"]
            if not operation.get("ok"):
                self.control_caption.setText(operation.get("error", "操作未完成"))
            elif operation.get("result", {}).get("ok") is False:
                self.control_caption.setText(
                    "环境检测未通过，任务保持暂停，请查看诊断。"
                )
        memory = server.get("memory") or {}
        total_memory, available = (
            memory.get("MemTotal", 0),
            memory.get("MemAvailable", 0),
        )
        self.resources.setText(
            f"服务器内存  {(total_memory - available) / 2**30:.1f} / {total_memory / 2**30:.1f} GB  ·  登录检查每 3 分钟  ·  文章同步每 60 秒"
            if total_memory
            else "服务器资源尚未核验"
        )
        self.footer.setText(
            "最近读取 "
            + clock(data["checked_epoch"])
            + "  ·  关闭面板不停止后台文件交接。"
        )
        self.diagnostic_caption.setText(
            f"当前批次 {batch_date}：{len(current_attention)} 篇待处理。失败任务已停止，不会定时自动重试。选中一行查看处理建议。"
        )
        diagnostic = {
            "最近读取": clock(data["checked_epoch"]),
            "连接": data["connection"],
            "连接错误类型": data.get("connection_error"),
            "本地交接": relay,
            "API 执行": server.get("api"),
            "等待关闭旧Word": data.get("revocation_pending"),
            "需处理票据": server.get("attention", []),
            "今日平台采集": server.get("captures", {}),
            "采集待处理": current_capture_attention,
            "每日调度": schedule,
            "六小时测试": server.get("soak", {"status": "not_started"}),
            "本地文章目录": str(Path(data["root"]) / "articles"),
        }
        self.diagnostics.setPlainText(
            json.dumps(diagnostic, ensure_ascii=False, indent=2)
        )
        records = data.get("articles", [])
        for control, key, default in (
            (self.date_filter, "date", "全部日期"),
            (self.category_filter, "category", "全部类别"),
        ):
            current = control.currentText()
            control.blockSignals(True)
            control.clear()
            control.addItems(
                [default] + sorted({item[key] for item in records}, reverse=True)
            )
            control.setCurrentText(
                current if control.findText(current) >= 0 else default
            )
            control.blockSignals(False)
        if not self.library_initialized and self.date_filter.findText(today) >= 0:
            self.date_filter.blockSignals(True)
            self.date_filter.setCurrentText(today)
            self.date_filter.blockSignals(False)
            self.library_initialized = True
        self.filter_articles()

    def filter_articles(self):
        records = self.data.get("articles", [])
        date, category, query = (
            self.date_filter.currentText(),
            self.category_filter.currentText(),
            self.search.text().strip().lower(),
        )
        selected = self.selected()
        folder = selected.get("folder") if selected else None
        rows = [
            item
            for item in records
            if (date == "全部日期" or item["date"] == date)
            and (category == "全部类别" or item["category"] == category)
            and query in item["title"].lower()
        ]
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        target = 0
        for index, item in enumerate(rows):
            for column, value in enumerate(
                (
                    item["title"],
                    item["category"],
                    item["date"],
                    ({"approved": "你已验收", "rejected": "你已退回"}.get(item.get("user_review", {}).get("decision"), "待你验收")) if item.get("integrity") == "verified" else "文件已变更",
                )
            ):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(str(value))
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item)
                self.table.setItem(index, column, cell)
            self.table.setRowHeight(index, 45)
            if item["folder"] == folder:
                target = index
        self.table.blockSignals(False)
        self.library_caption.setText(
            f"本地已归档 {len(records)} 篇  ·  当前显示 {len(rows)} 篇  ·  按原批次日期与类别保存"
        )
        if rows:
            self.table.selectRow(target)
            self.select_article()
        else:
            self.preview.clear()
            self.article_title.setText("暂无符合条件的文章")
            self.word_button.setEnabled(False)
            self.folder_button.setEnabled(False)

    def selected(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select_article(self):
        item = self.selected()
        if not item:
            return
        self.article_title.setText(f"{item['date']}  ·  {item['category']}  ·  第{item['number']}篇")
        identity = (item["folder"], item.get("word_sha256"))
        if self.preview_for != identity:
            self.preview.setMarkdown(item["text"])
            block = self.preview.document().begin()
            while block.isValid():
                cursor = QTextCursor(block)
                formatting = block.blockFormat()
                formatting.setLineHeight(150, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
                formatting.setTopMargin(8)
                formatting.setBottomMargin(10)
                cursor.setBlockFormat(formatting)
                level = formatting.headingLevel()
                if level:
                    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    font = QTextCharFormat()
                    font.setFontPointSize(17 if level == 1 else 13)
                    cursor.mergeCharFormat(font)
                block = block.next()
            self.preview_for = identity
        source_identity = (identity, bool(item.get("provenance")))
        if getattr(self, "source_identity", None) != source_identity:
            self.source_identity = source_identity
            self.source_choice.blockSignals(True)
            self.source_choice.clear()
            self.source_choice.addItem("正文声明 → 引用证据对照", None)
            for source in item.get("provenance", {}).get("sources", []):
                self.source_choice.addItem("原文 · " + source.get("title", source["url"]), source)
            self.source_choice.blockSignals(False)
            self.show_source()
        review = item.get("user_review", {})
        self.review_preview.setHtml("<h2>验收这篇文章</h2><p>核对参考来源、产品事实、是否满足写作需求，以及 Word 的标题、段落、编号和分页。</p><p>程序检查通过不等于人工认可。验收结果只针对当前文件版本。</p><p><b>当前记录：</b>" + {"approved": "你已验收通过", "rejected": "你已退回，等待处理"}.get(review.get("decision"), "尚未验收") + "</p><p>" + html.escape(review.get("reason", "")) + "</p><p>验收与退回原因保存在本机，退回不会自动启动收费重写，也不会自动发布。</p>")
        self.word_button.setEnabled(True)
        self.folder_button.setEnabled(True)

    def show_source(self):
        item = self.selected()
        if not item:
            self.source_preview.clear()
            return
        original = self.source_choice.currentData()
        packet = item.get("provenance", {})
        if original:
            rendered = original_html(original)
        elif packet and item.get("integrity") == "verified":
            rendered = overview_html(packet)
        else:
            rendered = "<h2>来源对照尚未就绪</h2><p>此版本尚未同步完整证据包，或文件完整性检查未通过。下列为候选信源，不代表实际采用。</p>" + "".join(f'<p><a href="{html.escape(url, quote=True)}">{html.escape(url)}</a></p>' for url in item.get("sources", []) if url.startswith(("http://", "https://")))
        self.source_preview.setHtml(rendered)

    def toggle_reading(self, enabled):
        self.table.setVisible(not enabled)
        self.reading_button.setText("返回文章列表" if enabled else "专注阅读")

    def record_review(self, decision):
        item = self.selected()
        if not item:
            return
        reason = ""
        if decision == "rejected":
            reason, ok = QInputDialog.getMultiLineText(self, "退回修改", "写下需要修改的地方（只记录，不自动收费重写）：")
            if not ok or not reason.strip():
                return
        try:
            record = backend.review_article(self.data["root"], item["folder"], decision, reason)
        except (OSError, ValueError) as error:
            QMessageBox.information(self, "未保存", str(error))
            return
        for row in self.data.get("articles", []):
            if row["folder"] == item["folder"]:
                row["user_review"] = record
        self.filter_articles()
        self.footer.setText("已保存你的验收记录；没有启动模型调用或发布。")

    def show_task_detail(self):
        row = self.attention_table.currentRow()
        cell = self.attention_table.item(row, 0) if row >= 0 else None
        item = cell.data(Qt.ItemDataRole.UserRole) if cell else None
        if not item:
            self.task_detail.setPlainText("选择上方任务查看原因和下一步。待处理任务不会自行恢复。")
            return
        self.task_detail.setHtml("<b>" + html.escape(str(item.get("category", ""))) + f" · 第{item.get('number', '')}篇</b><p>" + html.escape(error_summary(item.get("error"))) + "</p><p><b>下一步：</b>核对正文和证据；误判则修正规则，内容错误则定向修订。处理后重新检查。点击“继续任务”不能自动解决这类错误。</p>")

    def open_selected(self, key):
        item = self.selected()
        if item:
            self.open_path(item[key])

    def open_path(self, path):
        path = Path(path)
        if not path.exists() or not QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(path.resolve()))
        ):
            QMessageBox.information(
                self, "文件暂不可用", "文件尚未同步或系统未能打开该路径。"
            )

    def copy_runbook(self):
        if not self.data:
            return
        path = Path(self.data["root"]) / "API_RUNBOOK.md"
        if path.is_file():
            QApplication.clipboard().setText(path.read_text(encoding="utf8"))
            self.footer.setText("运行说明已复制。API 任务在服务器后台执行。")

    def closeEvent(self, event):
        self.timer.stop()
        if self.worker and self.worker.isRunning():
            self.closing = True
            self.hide()
            event.ignore()
        else:
            event.accept()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", choices=["overview", "articles", "diagnostics", "settings", "logs"], default="overview")
    parser.add_argument(
        "--config", type=Path, default=Path.home() / ".geo-editorial/bridge.json"
    )
    args = parser.parse_args(argv)
    application = QApplication(sys.argv[:1])
    application.setApplicationName("内容工作台")
    application.setStyle("Fusion")
    application.setFont(QFont("Microsoft YaHei UI", 10))
    application.setStyleSheet(STYLE)
    if not args.config.is_file():
        QMessageBox.information(
            None, "需要项目配置", "未找到本机文件交接配置。请按部署文档配置后启动。"
        )
        return 2
    try:
        config = json.loads(args.config.read_text(encoding="utf8"))
        root = Path(config["local_root"])
        root.mkdir(parents=True, exist_ok=True)
    except (ValueError, KeyError, OSError):
        QMessageBox.information(
            None,
            "配置需要修复",
            "本机文件交接配置格式不正确或目录不可访问，请按部署文档修复。",
        )
        return 2
    lock = QLockFile(str(Path(config["local_root"]) / "desktop_panel.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(
            None, "面板已运行", "已有一个内容工作台窗口，请使用已打开的窗口。"
        )
        return 0
    window = Window(args.config)
    window.nav.setCurrentRow(["overview", "articles", "diagnostics", "settings", "logs"].index(args.page))
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
