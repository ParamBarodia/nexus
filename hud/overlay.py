"""Nexus HUD — full-screen transparent overlay with JARVIS ring, click-through + minimize."""

import sys
import json
import math
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import psutil
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QLineEdit, QPushButton,
    QFrame, QSystemTrayIcon, QMenu, QTextEdit, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QBrush, QPen,
    QIcon, QPixmap, QRadialGradient,
)

# ---------------------------------------------------------------------------
BRAIN_URL = "http://localhost:8765"
BEARER_TOKEN = ""
ENV_FILE = Path(r"C:\jarvis\.env")
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("BRAIN_BEARER_TOKEN="):
            BEARER_TOKEN = line.split("=", 1)[1].strip()

VENV_PYTHON = r"C:\jarvis\venv\Scripts\python.exe"
JARVIS_DIR = r"C:\jarvis"
CYAN, GREEN, YELLOW, RED, DIM, TEXT = "#00d4ff", "#00ff88", "#ffd700", "#ff4444", "#555", "#e0e0e0"
BG_ALPHA = 180

def _h():
    return {"Authorization": f"Bearer {BEARER_TOKEN}"} if BEARER_TOKEN else {}
def _get(ep):
    try: return requests.get(f"{BRAIN_URL}{ep}", headers=_h(), timeout=5).json()
    except: return None
def _post(ep, d=None):
    try: return requests.post(f"{BRAIN_URL}{ep}", json=d or {}, headers=_h(), timeout=30).json()
    except: return None
def _font(sz, bold=False):
    f = QFont("Segoe UI", sz); f.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal); return f
def _glow(w, c, r=15):
    e = QGraphicsDropShadowEffect(); e.setBlurRadius(r); e.setColor(QColor(c)); e.setOffset(0,0); w.setGraphicsEffect(e)

BTN = ("QPushButton{background:rgba(0,212,255,0.12);color:#00d4ff;border:1px solid rgba(0,212,255,0.25);"
       "border-radius:4px;padding:5px 12px;font-size:11px;font-weight:bold;}"
       "QPushButton:hover{background:rgba(0,212,255,0.25);}")
INPUT_S = ("QLineEdit{background:rgba(255,255,255,0.06);color:#e0e0e0;border:1px solid rgba(0,212,255,0.3);"
           "border-radius:5px;padding:8px 12px;font-size:13px;}QLineEdit:focus{border-color:#00d4ff;}")
CHAT_S = ("QTextEdit{background:rgba(0,0,0,0.4);color:#e0e0e0;border:none;border-radius:6px;"
          "padding:10px;font-size:11px;font-family:'Segoe UI';}")

# ---------------------------------------------------------------------------
class Panel(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(4)
        if title:
            hdr = QLabel(title); hdr.setFont(_font(8, True)); hdr.setStyleSheet(f"color:{CYAN};letter-spacing:2px;")
            self._layout.addWidget(hdr)
    def add(self, w):
        self._layout.addWidget(w); return w
    def add_layout(self, l):
        self._layout.addLayout(l)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(12, 12, 20, BG_ALPHA)))
        p.setPen(QPen(QColor(0,212,255,25), 1))
        p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1), 8, 8)
        p.end()

# ---------------------------------------------------------------------------
class JarvisRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 280)
        self._angle = 0; self._cpu = 0; self._ram = 0
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)
        st = QTimer(self); st.timeout.connect(self._stats); st.start(2000); self._stats()
    def _tick(self):
        self._angle = (self._angle + 0.8) % 360; self.update()
    def _stats(self):
        self._cpu = psutil.cpu_percent(interval=0); self._ram = psutil.virtual_memory().percent
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = 140, 140
        p.setPen(QPen(QColor(0,212,255,60),3)); p.drawEllipse(cx-130,cy-130,260,260)
        p.setPen(QPen(QColor(0,212,255,180),4))
        p.drawArc(QRectF(cx-130,cy-130,260,260), int((90-self._angle)*16), int(-self._cpu*3.6*16))
        p.setPen(QPen(QColor(0,255,136,50),2)); p.drawEllipse(cx-105,cy-105,210,210)
        p.setPen(QPen(QColor(0,255,136,160),3))
        p.drawArc(QRectF(cx-105,cy-105,210,210), int((270+self._angle*0.7)*16), int(-self._ram*3.6*16))
        p.setPen(QPen(QColor(0,212,255,35),1)); p.drawEllipse(cx-80,cy-80,160,160)
        for i in range(12):
            a = math.radians(self._angle + i*30)
            p.setPen(QPen(QColor(0,212,255, 80 if i%3==0 else 30), 1))
            p.drawLine(int(cx+75*math.cos(a)),int(cy+75*math.sin(a)),int(cx+82*math.cos(a)),int(cy+82*math.sin(a)))
        gr = QRadialGradient(cx,cy,50)
        gr.setColorAt(0, QColor(0,212,255,25)); gr.setColorAt(1, QColor(0,0,0,0))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(gr)); p.drawEllipse(cx-50,cy-50,100,100)
        p.setPen(QColor(0,212,255,200)); p.setFont(_font(8, True))
        p.drawText(QRectF(cx-40,cy-25,80,16), Qt.AlignmentFlag.AlignCenter, "N E X U S")
        p.setPen(QColor(TEXT)); p.setFont(_font(7))
        p.drawText(QRectF(cx-40,cy-8,80,14), Qt.AlignmentFlag.AlignCenter, f"CPU {self._cpu:.0f}%")
        p.drawText(QRectF(cx-40,cy+6,80,14), Qt.AlignmentFlag.AlignCenter, f"RAM {self._ram:.0f}%")
        ram_gb = psutil.virtual_memory().used / (1024**3)
        p.setPen(QColor(0,212,255,120)); p.setFont(_font(7))
        p.drawText(QRectF(cx-135,cy+100,270,14), Qt.AlignmentFlag.AlignCenter,
                   f"MEM {ram_gb:.1f} GB  |  DISK {psutil.disk_usage('/').percent:.0f}%")
        p.end()

# ---------------------------------------------------------------------------
class DataFetcher(QObject):
    data_ready = pyqtSignal(dict)
    def fetch(self):
        r = {}
        s = _get("/status")
        if s: r["status"] = s
        cn = _get("/connectors")
        if cn: r["connectors"] = cn; r["n_active"] = len([c for c in cn if c["status"]=="active"]); r["n_total"] = len(cn)
        b = _get("/briefing/today")
        if b and b.get("briefing"): r["briefing"] = b["briefing"]
        cr = _post("/connectors/crypto/fetch")
        if cr and "prices" in cr: r["crypto"] = cr["prices"]
        hn = _post("/connectors/hackernews/fetch")
        if hn and "stories" in hn: r["hn"] = hn["stories"][:4]
        fx = _post("/connectors/forex/fetch")
        if fx and "rates" in fx: r["forex"] = fx["rates"]
        w = _post("/connectors/weather/fetch")
        if w and "error" not in (w or {}): r["weather"] = w
        self.data_ready.emit(r)

# ---------------------------------------------------------------------------
class ChatWorker(QObject):
    chunk = pyqtSignal(str)
    done = pyqtSignal()
    def send(self, msg, tier=None):
        try:
            r = requests.post(f"{BRAIN_URL}/chat", json={"message":msg,"tier":tier},
                              stream=True, timeout=120, headers=_h())
            for line in r.iter_lines(decode_unicode=True):
                if not line: continue
                pay = line[6:] if line.startswith("data: ") else line[5:] if line.startswith("data:") else None
                if not pay: continue
                try:
                    c = json.loads(pay); ct = c.get("type")
                    if ct in ("token","text"): self.chunk.emit(c.get("content",""))
                    elif ct=="routing": self.chunk.emit(f'[T{c["tier"]}] ')
                    elif ct=="tool_call": self.chunk.emit(f'\n[{c["tool"]}] ')
                    elif ct=="done": break
                except: pass
        except Exception as e: self.chunk.emit(f"\n[Error: {e}]")
        self.done.emit()

# ---------------------------------------------------------------------------
def _get_pins():
    pins = []
    tb = Path(os.environ.get("APPDATA","")) / r"Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
    if tb.exists():
        for lnk in tb.glob("*.lnk"): pins.append({"name": lnk.stem, "path": str(lnk)})
    return pins[:10]

# ---------------------------------------------------------------------------
class NexusHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._chat_busy = False
        self._cmd_visible = False
        self._data = {}
        self._build_ui()
        self._setup_tray()
        self._start_data()




    def _build_ui(self):
        grid = QGridLayout(self)
        grid.setContentsMargins(30, 30, 30, 30)
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 2); grid.setColumnStretch(2, 1)
        grid.setRowStretch(0, 0); grid.setRowStretch(1, 1); grid.setRowStretch(2, 0)

        # ===== TOP LEFT: Clock =====
        clock_panel = Panel()
        self.clock_lbl = clock_panel.add(QLabel("00:00"))
        self.clock_lbl.setFont(QFont("Segoe UI Light", 42))
        self.clock_lbl.setStyleSheet("color:white;")
        _glow(self.clock_lbl, CYAN, 10)
        self.date_lbl = clock_panel.add(QLabel(""))
        self.date_lbl.setFont(_font(11))
        self.date_lbl.setStyleSheet(f"color:{DIM};")
        grid.addWidget(clock_panel, 0, 0)

        # ===== TOP CENTER: Status + ticker =====
        status_panel = Panel()
        self.status_lbl = status_panel.add(QLabel("Connecting..."))
        self.status_lbl.setFont(_font(10)); self.status_lbl.setStyleSheet(f"color:{GREEN};")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ticker_lbl = status_panel.add(QLabel(""))
        self.ticker_lbl.setFont(QFont("Consolas",9)); self.ticker_lbl.setStyleSheet(f"color:{TEXT};")
        self.ticker_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(status_panel, 0, 1)

        # ===== TOP RIGHT: Weather =====
        self.weather_panel = Panel("WEATHER")
        self.weather_lbl = self.weather_panel.add(QLabel("Loading..."))
        self.weather_lbl.setFont(_font(9)); self.weather_lbl.setStyleSheet(f"color:{TEXT};"); self.weather_lbl.setWordWrap(True)
        grid.addWidget(self.weather_panel, 0, 2)

        # ===== LEFT: Project + News + Shortcuts =====
        left = QVBoxLayout(); left.setSpacing(12)
        proj_panel = Panel("ACTIVE PROJECT")
        self.proj_lbl = proj_panel.add(QLabel("...")); self.proj_lbl.setFont(_font(9))
        self.proj_lbl.setStyleSheet(f"color:{TEXT};"); self.proj_lbl.setWordWrap(True)
        left.addWidget(proj_panel)

        news_panel = Panel("NEWS")
        self.news_lbl = news_panel.add(QLabel("Loading...")); self.news_lbl.setFont(_font(9))
        self.news_lbl.setStyleSheet("color:#ccc;"); self.news_lbl.setWordWrap(True)
        left.addWidget(news_panel)

        launch_panel = Panel("SHORTCUTS")
        for pin in _get_pins():
            b = QPushButton(f"  {pin['name']}")
            b.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT};border:none;text-align:left;padding:2px 4px;font-size:10px;}}"
                            f"QPushButton:hover{{color:{CYAN};background:rgba(0,212,255,0.08);}}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            path = pin["path"]
            b.clicked.connect(lambda _, p=path: os.startfile(p))
            launch_panel.add(b)
        left.addWidget(launch_panel)
        left.addStretch()
        grid.addLayout(left, 1, 0)

        # ===== CENTER: JARVIS Ring + System stats + cmd =====
        center = QVBoxLayout(); center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ring = JarvisRing()
        center.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        stats_panel = Panel("SYSTEM")
        srow = QHBoxLayout()
        self.cpu_lbl = QLabel("CPU --"); self.cpu_lbl.setFont(QFont("Consolas",9)); self.cpu_lbl.setStyleSheet(f"color:{CYAN};")
        self.ram_lbl = QLabel("RAM --"); self.ram_lbl.setFont(QFont("Consolas",9)); self.ram_lbl.setStyleSheet(f"color:{GREEN};")
        self.disk_lbl = QLabel("DISK --"); self.disk_lbl.setFont(QFont("Consolas",9)); self.disk_lbl.setStyleSheet(f"color:{YELLOW};")
        self.net_lbl = QLabel("NET --"); self.net_lbl.setFont(QFont("Consolas",9)); self.net_lbl.setStyleSheet(f"color:{TEXT};")
        for w in (self.cpu_lbl, self.ram_lbl, self.disk_lbl, self.net_lbl): srow.addWidget(w)
        stats_panel.add_layout(srow)
        center.addWidget(stats_panel)

        # Command bar (hidden)
        self.cmd_bar = QLineEdit()
        self.cmd_bar.setPlaceholderText("Ask JARVIS anything...")
        self.cmd_bar.setStyleSheet(INPUT_S); self.cmd_bar.setFont(_font(13)); self.cmd_bar.setFixedHeight(44)
        self.cmd_bar.returnPressed.connect(self._on_cmd)
        self.cmd_bar.setVisible(False)
        center.addWidget(self.cmd_bar)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True); self.chat_area.setStyleSheet(CHAT_S); self.chat_area.setFont(_font(10))
        self.chat_area.setMaximumHeight(200); self.chat_area.setVisible(False)
        center.addWidget(self.chat_area)

        grid.addLayout(center, 1, 1)

        # ===== RIGHT: Markets + Notes + Briefing + Status =====
        right = QVBoxLayout(); right.setSpacing(12)

        market_panel = Panel("MARKETS")
        self.crypto_lbl = market_panel.add(QLabel("Loading...")); self.crypto_lbl.setFont(QFont("Consolas",9))
        self.crypto_lbl.setStyleSheet(f"color:{TEXT};"); self.crypto_lbl.setWordWrap(True)
        self.forex_lbl = market_panel.add(QLabel("")); self.forex_lbl.setFont(QFont("Consolas",8))
        self.forex_lbl.setStyleSheet(f"color:{DIM};")
        right.addWidget(market_panel)

        todo_panel = Panel("NOTES")
        self.todo_lbl = todo_panel.add(QLabel("Connect Notion for tasks")); self.todo_lbl.setFont(_font(9))
        self.todo_lbl.setStyleSheet(f"color:{TEXT};"); self.todo_lbl.setWordWrap(True)
        right.addWidget(todo_panel)

        brief_panel = Panel("BRIEFING")
        self.brief_lbl = brief_panel.add(QLabel("No briefing yet.")); self.brief_lbl.setFont(_font(8))
        self.brief_lbl.setStyleSheet("color:#999;"); self.brief_lbl.setWordWrap(True)
        right.addWidget(brief_panel)

        conn_panel = Panel("STATUS")
        self.conn_lbl = conn_panel.add(QLabel("...")); self.conn_lbl.setFont(_font(8))
        self.conn_lbl.setStyleSheet(f"color:{DIM};"); self.conn_lbl.setWordWrap(True)
        right.addWidget(conn_panel)

        right.addStretch()
        grid.addLayout(right, 1, 2)

        # ===== BOTTOM: Actions =====
        act_panel = Panel("ACTIONS")
        arow = QHBoxLayout()
        for label, handler in [
            ("Briefing", self._act_briefing), ("Greet", self._act_greet),
            ("Backup", self._act_backup), ("Voice", self._act_ptt),
            ("Setup", self._act_setup), ("Minimize", self._minimize_to_tray),
        ]:
            b = QPushButton(label); b.setStyleSheet(BTN); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(handler); arow.addWidget(b)
        act_panel.add_layout(arow)

        mrow = QHBoxLayout()
        for m in ("personal","office","content","freelance"):
            b = QPushButton(m.title()); b.setStyleSheet(BTN); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _,mode=m: threading.Thread(target=lambda: _post("/mode",{"mode":mode}), daemon=True).start())
            mrow.addWidget(b)
        act_panel.add_layout(mrow)
        grid.addWidget(act_panel, 2, 0, 1, 3)

        # Timers
        ct = QTimer(self); ct.timeout.connect(self._tick_clock); ct.start(1000); self._tick_clock()
        st = QTimer(self); st.timeout.connect(self._tick_stats); st.start(2000); self._tick_stats()
        mt = QTimer(self); mt.timeout.connect(self._tick_media); mt.start(5000)

    def _tick_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%H:%M:%S"))
        self.date_lbl.setText(now.strftime("%A, %B %d, %Y"))

    def _tick_stats(self):
        cpu = psutil.cpu_percent(interval=0); ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/"); net = psutil.net_io_counters()
        self.cpu_lbl.setText(f"CPU {cpu:.0f}%"); self.ram_lbl.setText(f"RAM {ram.used/(1024**3):.1f}/{ram.total/(1024**3):.0f}GB")
        self.disk_lbl.setText(f"DISK {disk.percent:.0f}%"); self.net_lbl.setText(f"NET {net.bytes_sent/(1024**2):.0f}M sent")
        c = GREEN if cpu < 50 else YELLOW if cpu < 80 else RED
        self.cpu_lbl.setStyleSheet(f"color:{c};")

    def _tick_media(self):
        try:
            r = subprocess.run(["powershell","-Command",
                 "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
                 "Where-Object {$_.ProcessName -match 'spotify|vlc|chrome|msedge|firefox|Music'} | "
                 "Select-Object -First 1 -ExpandProperty MainWindowTitle"],
                capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
            pass  # media detection for future use
        except: pass

    # ---- Tray ----
    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        pm = QPixmap(32,32); pm.fill(QColor(0,0,0,0))
        pt = QPainter(pm); pt.setRenderHint(QPainter.RenderHint.Antialiasing)
        pt.setBrush(QBrush(QColor(0,212,255))); pt.setPen(Qt.PenStyle.NoPen); pt.drawEllipse(4,4,24,24); pt.end()
        self._tray.setIcon(QIcon(pm))
        menu = QMenu()
        menu.addAction("Show HUD").triggered.connect(self._restore)
        menu.addAction("Quit").triggered.connect(QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(lambda r: self._restore() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self._tray.show()

    def _minimize_to_tray(self):
        self.hide()
        self._tray.showMessage("Nexus", "HUD minimized. Double-click tray icon to restore.",
                               QSystemTrayIcon.MessageIcon.Information, 2000)

    def _restore(self):
        self.show(); self.raise_(); self.activateWindow()

    # ---- Data ----
    def _start_data(self):
        self.fetcher = DataFetcher()
        self.fetcher.data_ready.connect(self._on_data)
        self._dt = QTimer(self)
        self._dt.timeout.connect(lambda: threading.Thread(target=self.fetcher.fetch, daemon=True).start())
        self._dt.start(20000)
        QTimer.singleShot(1500, lambda: threading.Thread(target=self.fetcher.fetch, daemon=True).start())

    def _on_data(self, d):
        self._data = d
        st = d.get("status", {})
        if st.get("ok"):
            self.status_lbl.setText(f"ONLINE  |  {st.get('mode','')}  |  {st.get('project','')}")
            self.status_lbl.setStyleSheet(f"color:{GREEN};")
            self.conn_lbl.setText(f"Connectors: {d.get('n_active',0)}/{d.get('n_total',0)} | Memory: {st.get('memory_facts',0)} facts")
        else:
            self.status_lbl.setText("BRAIN OFFLINE"); self.status_lbl.setStyleSheet(f"color:{RED};")

        if st.get("project"):
            self.proj_lbl.setText(f"{st['project']}\nMemory: {st.get('memory_facts',0)} facts")

        w = d.get("weather")
        if w and isinstance(w, dict) and "temp" in w:
            lines = f'{w.get("description","").title()}\n'
            lines += f'Temp: {w["temp"]}C  Feels: {w.get("feels_like","")}C\n'
            lines += f'Humidity: {w.get("humidity","")}%  Wind: {w.get("wind_speed","")} km/h'
            if w.get("aqi") is not None:
                lines += f'\nAQI: {w["aqi"]} ({w.get("aqi_label","")})  PM2.5: {w.get("pm25","")}'
            self.weather_lbl.setText(lines)

        cr = d.get("crypto", {})
        if cr:
            parts = []
            for coin, info in cr.items():
                pr = info.get("usd",0); ch = info.get("change_24h",0) or 0
                clr = GREEN if ch >= 0 else RED; arrow = "+" if ch >= 0 else ""
                parts.append(f'<span style="color:#ddd">{coin.upper()}</span> <b>${pr:,.0f}</b> '
                             f'<span style="color:{clr}">{arrow}{ch:.1f}%</span>')
            self.crypto_lbl.setText("<br>".join(parts))

        ticker_parts = []
        if cr:
            for coin, info in cr.items(): ticker_parts.append(f"{coin.upper()} ${info.get('usd',0):,.0f}")
        fx = d.get("forex", {})
        if fx:
            for k, v in fx.items(): ticker_parts.append(f"{k} {v}")
            self.forex_lbl.setText("USD: " + " | ".join(f"{k} {v}" for k,v in fx.items()))
        if ticker_parts: self.ticker_lbl.setText("  |  ".join(ticker_parts))

        hn = d.get("hn", [])
        if hn:
            self.news_lbl.setText("<br>".join(
                f'<span style="color:{YELLOW}">{s["points"]}</span> '
                f'<span style="color:#ccc">{s["title"][:55]}</span>' for s in hn[:4]))

        br = d.get("briefing", "")
        if br: self.brief_lbl.setText(br[:350] + ("..." if len(br) > 350 else ""))

    # ---- Chat ----
    def _on_cmd(self):
        msg = self.cmd_bar.text().strip()
        if not msg or self._chat_busy: return
        self._chat_busy = True; self.cmd_bar.clear()
        self.chat_area.setVisible(True)
        self.chat_area.append(f'<br><span style="color:{CYAN};font-weight:bold;">You:</span> {msg}')
        self.chat_area.append(f'<span style="color:{GREEN};font-weight:bold;">JARVIS:</span> ')
        self._wk = ChatWorker()
        self._wk.chunk.connect(self._on_chunk)
        self._wk.done.connect(lambda: setattr(self, '_chat_busy', False))
        threading.Thread(target=self._wk.send, args=(msg,), daemon=True).start()
    def _on_chunk(self, text):
        cur = self.chat_area.textCursor(); cur.movePosition(cur.MoveOperation.End)
        cur.insertText(text); self.chat_area.setTextCursor(cur); self.chat_area.ensureCursorVisible()

    # ---- Actions ----
    def _act_briefing(self):
        self.brief_lbl.setText("Composing...")
        threading.Thread(target=lambda: (_post("/briefing/compose"), self.brief_lbl.setText("Done.")), daemon=True).start()
    def _act_greet(self):
        subprocess.Popen([VENV_PYTHON, os.path.join(JARVIS_DIR,"hud","startup_greeting.py")],
                         cwd=JARVIS_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
    def _act_backup(self):
        threading.Thread(target=lambda: _post("/backup"), daemon=True).start()
    def _act_ptt(self):
        subprocess.Popen(["cmd","/c","start","cmd","/k",
                          f'"{VENV_PYTHON}" -c "from brain.voice_session import run_push_to_talk; run_push_to_talk()"'],
                         cwd=JARVIS_DIR)
    def _act_setup(self):
        subprocess.Popen(["cmd","/c","start","cmd","/k",
                          f'"{VENV_PYTHON}" "{os.path.join(JARVIS_DIR,"hud","setup_wizard.py")}"'],
                         cwd=JARVIS_DIR)

    # ---- Paint grid ----
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0,212,255,8), 1); p.setPen(pen)
        w, h = self.width(), self.height()
        for x in range(0, w, 80): p.drawLine(x, 0, x, h)
        for y in range(0, h, 80): p.drawLine(0, y, w, y)
        p.end()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape: self._minimize_to_tray()


def run_hud():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    hud = NexusHUD()
    hud.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_hud()
