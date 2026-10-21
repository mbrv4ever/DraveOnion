# -*- coding: utf-8 -*-
"""DraveOnion - een privacy-browser op het Tor-netwerk (PyQt6 + Chromium).

Echte browser-engine (QtWebEngine), al het verkeer via Tor, privé by default
(geen geschiedenis/cache), tracker-blokkering, JS-schakelaar, nieuwe identiteit,
.onion. Taal volgt de pc (NL/EN). Donationware.

LET OP: dit is een echte privacy-browser op Tor, maar niet zo waterdicht-
anoniem als de officiele Tor Browser (die heeft extra anti-fingerprinting).
"""
import html as _html
import json
import locale
import os
import sys
import threading
from urllib.parse import quote

from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (QIcon, QAction, QDesktopServices, QShortcut,
                         QKeySequence)
from PyQt6.QtNetwork import QNetworkProxy
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit,
                             QTabWidget, QPushButton, QLabel, QStyle,
                             QMessageBox, QStatusBar, QMenu, QToolButton,
                             QInputDialog, QDialog, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QFileDialog)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (QWebEngineProfile, QWebEnginePage,
                                   QWebEngineSettings, QWebEngineScript,
                                   QWebEngineUrlRequestInterceptor)

try:
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
    HAS_PRINT = True
except Exception:
    HAS_PRINT = False

try:
    import base64
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

import tor_manager as TM


def _lang():
    try:
        loc = (locale.getdefaultlocale()[0] or "")
    except Exception:
        loc = ""
    return "nl" if loc.lower().startswith("nl") else "en"


LANG = _lang()

TX = {
    "title": {"nl": "DraveOnion - privacy-browser", "en": "DraveOnion - privacy browser"},
    "connecting": {"nl": "Verbinden met Tor...", "en": "Connecting to Tor..."},
    "connected": {"nl": "Verbonden via Tor", "en": "Connected via Tor"},
    "notor": {"nl": "Geen Tor-verbinding", "en": "No Tor connection"},
    "newtab": {"nl": "Nieuw tabblad", "en": "New tab"},
    "newid": {"nl": "Nieuwe identiteit", "en": "New identity"},
    "js": {"nl": "JavaScript", "en": "JavaScript"},
    "donate": {"nl": "♥ Doneren", "en": "♥ Donate"},
    "info": {"nl": "Info", "en": "Info"},
    "save_bm": {"nl": "☆ Bewaren", "en": "☆ Save"},
    "rm_bm": {"nl": "Verwijderen", "en": "Remove"},
    "no_favs": {"nl": "  Sleep een URL hierheen of gebruik ☆ Bewaren  ",
                "en": "  Drag a URL here or use ☆ Save  "},
    "bm_added": {"nl": "Toegevoegd aan favorieten.", "en": "Added to favorites."},
    "new_folder": {"nl": "＋ Map", "en": "＋ Folder"},
    "rm_folder": {"nl": "Map verwijderen", "en": "Delete folder"},
    "rm_in_folder": {"nl": "Link verwijderen", "en": "Remove link"},
    "to_folder": {"nl": "Naar map", "en": "Move to folder"},
    "print": {"nl": "🖨 Print", "en": "🖨 Print"},
    "pdf": {"nl": "📄 PDF", "en": "📄 PDF"},
    "pw": {"nl": "🔑 Wachtwoorden", "en": "🔑 Passwords"},
    "pw_title": {"nl": "Wachtwoordbeheer", "en": "Password manager"},
    "pw_set": {"nl": "Kies een hoofdwachtwoord:", "en": "Choose a master password:"},
    "pw_set2": {"nl": "Herhaal het hoofdwachtwoord:", "en": "Repeat master password:"},
    "pw_enter": {"nl": "Hoofdwachtwoord:", "en": "Master password:"},
    "pw_wrong": {"nl": "Onjuist hoofdwachtwoord.", "en": "Wrong master password."},
    "pw_nomatch": {"nl": "Wachtwoorden komen niet overeen.",
                   "en": "Passwords do not match."},
    "pw_site": {"nl": "Site / omschrijving:", "en": "Site / label:"},
    "pw_user": {"nl": "Gebruikersnaam:", "en": "Username:"},
    "pw_pass": {"nl": "Wachtwoord:", "en": "Password:"},
    "pw_add": {"nl": "Toevoegen", "en": "Add"},
    "pw_del": {"nl": "Verwijderen", "en": "Remove"},
    "pw_copyu": {"nl": "Kopieer gebruiker", "en": "Copy user"},
    "pw_copyp": {"nl": "Kopieer wachtwoord", "en": "Copy password"},
    "pw_copied": {"nl": "Gekopieerd (na 30s gewist).", "en": "Copied (cleared in 30s)."},
    "pw_nocrypto": {"nl": "Module 'cryptography' ontbreekt (zit in Start-bat).",
                    "en": "Module 'cryptography' missing (in Start bat)."},
    "folder_name": {"nl": "Naam van de map:", "en": "Folder name:"},
    "scripts": {"nl": "🧩 Scripts", "en": "🧩 Scripts"},
    "scripts_title": {"nl": "Userscripts (Tampermonkey-stijl)",
                      "en": "Userscripts (Tampermonkey-style)"},
    "new_script": {"nl": "Nieuw script", "en": "New script"},
    "rm_script": {"nl": "Verwijderen", "en": "Remove"},
    "open_folder": {"nl": "Map openen", "en": "Open folder"},
    "script_name": {"nl": "Naam van het script (zonder .js):",
                    "en": "Script name (without .js):"},
    "script_code": {"nl": "Plak hier je JavaScript:", "en": "Paste your JavaScript:"},
    "retry": {"nl": "Opnieuw proberen", "en": "Retry"},
    "blocked": {"nl": "trackers geblokkeerd", "en": "trackers blocked"},
    "newid_ok": {"nl": "Nieuwe identiteit aangevraagd.", "en": "New identity requested."},
    "newid_no": {"nl": "Nieuwe identiteit werkt alleen met de ingebouwde Tor "
                       "(niet met een al draaiende Tor Browser).",
                 "en": "New identity only works with the built-in Tor "
                       "(not with an already-running Tor Browser)."},
    "newid_fail": {"nl": "Kon geen nieuwe identiteit aanvragen.",
                   "en": "Could not request a new identity."},
    "newid_info": {"nl": "'Nieuwe identiteit' vraagt een nieuw Tor-circuit aan, "
                         "zodat je via een ander exit-knooppunt (ander IP) surft. "
                         "Hieronder zie je je huidige IP.",
                   "en": "'New identity' requests a fresh Tor circuit so you "
                         "browse via a different exit node (new IP). Below you "
                         "see your current IP."},
    "wait_tor": {"nl": "Wacht tot Tor verbonden is.", "en": "Wait until Tor is connected."},
    "loading": {"nl": "Laden", "en": "Loading"},
    "save_as": {"nl": "Opslaan als", "en": "Save as"},
    "downloading": {"nl": "Downloaden:", "en": "Downloading:"},
    "download_done": {"nl": "Download klaar:", "en": "Download done:"},
    "find": {"nl": "Zoek op pagina...", "en": "Find on page..."},
    "close": {"nl": "Sluiten", "en": "Close"},
    "downloads": {"nl": "⬇ Downloads", "en": "⬇ Downloads"},
    "dl_none": {"nl": "Nog geen downloads.", "en": "No downloads yet."},
    "dl_open": {"nl": "Map openen", "en": "Open folder"},
    "dl_clear": {"nl": "Lijst wissen", "en": "Clear list"},
    "dl_busy": {"nl": "bezig", "en": "running"},
    "dl_ok": {"nl": "klaar", "en": "done"},
    "reader": {"nl": "📖 Leesmodus", "en": "📖 Reader mode"},
    "engine": {"nl": "Zoekmachine", "en": "Search engine"},
    "https_only": {"nl": "Alleen HTTPS (veiliger)", "en": "HTTPS-only (safer)"},
    "blocked_lbl": {"nl": "geblokkeerd", "en": "blocked"},
    "start_tip": {"nl": "Zoek of voer een adres in",
                  "en": "Search or type an address"},
    "start_favs": {"nl": "Favorieten", "en": "Favorites"},
    "start_check": {"nl": "Controleer Tor", "en": "Check Tor"},
    "start_secure": {"nl": "Privé & via Tor", "en": "Private & over Tor"},
    "about": {
        "nl": "DraveOnion is een privacy-browser die al je verkeer via het "
              "Tor-netwerk stuurt. Geen geschiedenis of cache, trackers "
              "geblokkeerd. Het is GEEN vervanging voor de officiele Tor "
              "Browser voor echt gevoelig werk.\n\nDonationware - "
              "https://paypal.me/roger076",
        "en": "DraveOnion is a privacy browser routing all traffic through the "
              "Tor network. No history or cache, trackers blocked. It is NOT a "
              "replacement for the official Tor Browser for truly sensitive "
              "work.\n\nDonationware - https://paypal.me/roger076"},
}


def T(k):
    d = TX.get(k, {})
    return d.get(LANG) or d.get("en") or k


DONATE = "https://paypal.me/roger076"
HOME = "https://check.torproject.org/"
UA = ("Mozilla/5.0 (Windows NT 10.0; rv:115.0) Gecko/20100101 Firefox/115.0")

# beschikbare zoekmachines: sleutel -> (naam, basis-URL, queryparameter)
# Startpage staat eerst en is de standaard (meer/betere resultaten dan DDG)
SEARCH_ENGINES = {
    "startpage": ("Startpage", "https://www.startpage.com/sp/search", "query"),
    "ddg": ("DuckDuckGo", "https://duckduckgo.com/", "q"),
    "brave": ("Brave Search", "https://search.brave.com/search", "q"),
}
DEFAULT_ENGINE = "startpage"

# standaard-favorieten bij een verse installatie (ook in de EXE): een mapje
# met geverifieerde, legitieme onion-indexen. Controleer adressen bij gevoelig
# gebruik altijd op nep-klonen.
DEFAULT_FAVS = [
    {"type": "folder", "name": "🧅 Onion-indexen", "items": [
        {"type": "link", "title": "Ahmia (onion-zoeken)",
         "url": "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/"},
        {"type": "link", "title": "Tor Project",
         "url": "http://2gzyxa5ihm7nsggfxnu52rck2vv4rvmdlkiu3zzui5du4xyclen53wid.onion/"},
        {"type": "link", "title": "DuckDuckGo (onion)",
         "url": "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/"},
        {"type": "link", "title": "BBC News (onion)",
         "url": "https://bbcnewsd73hkzno2ini43t4gblxvycyac5aw4gnv7t2rccijh7745uqd.onion/"},
    ]},
]

# leesmodus: zoek het tekstrijkste blok en toon het opgeschoond
READER_JS = r"""(function(){
function score(e){var t=0,p=e.querySelectorAll('p');
for(var i=0;i<p.length;i++){t+=(p[i].innerText||'').length;}return t;}
var best=document.body,bs=0,cand=document.querySelectorAll('article,main,section,div');
for(var i=0;i<cand.length;i++){var s=score(cand[i]);if(s>bs){bs=s;best=cand[i];}}
if(bs<200){return;}
var title=(document.querySelector('h1')||{}).outerHTML||('<h1>'+document.title+'</h1>');
var html=best.innerHTML;
document.head.innerHTML='';
document.body.innerHTML='<div id="dro-reader">'+title+html+'</div>';
var st=document.createElement('style');
st.textContent='html,body{background:#16131f!important;}'+
'#dro-reader{max-width:760px;margin:48px auto;padding:0 22px;'+
'font:19px/1.75 Georgia,serif;color:#e8e6f0;}'+
'#dro-reader h1{font-size:30px;line-height:1.25;color:#cbb9ff;}'+
'#dro-reader h2,#dro-reader h3{color:#cbb9ff;}'+
'#dro-reader img{max-width:100%;height:auto;border-radius:8px;}'+
'#dro-reader a{color:#9fc1ff;}#dro-reader pre,#dro-reader code{white-space:pre-wrap;}';
document.documentElement.appendChild(st);
})();"""

# eenvoudige tracker/ad-blocklijst (domein-einde)
BLOCK = [
    "doubleclick.net", "googlesyndication.com", "google-analytics.com",
    "googletagmanager.com", "googletagservices.com", "adservice.google.com",
    "facebook.net", "connect.facebook.net", "graph.facebook.com",
    "scorecardresearch.com", "adnxs.com", "criteo.com", "criteo.net",
    "taboola.com", "outbrain.com", "pubmatic.com", "rubiconproject.com",
    "moatads.com", "amazon-adsystem.com", "adsrvr.org", "quantserve.com",
    "hotjar.com", "mixpanel.com", "segment.com", "branch.io", "appsflyer.com",
    "bing.com/bat", "ads.yahoo.com", "yieldmo.com", "openx.net", "casalemedia.com",
]

# kant-en-klare userscripts (standaard UIT; aan te zetten in de scriptbeheerder)
BUILTIN_SCRIPTS = {
    "Donkere modus": """(function(){
var c=document.documentElement;
c.style.filter='invert(0.92) hue-rotate(180deg)';
c.style.background='#111';
var st=document.createElement('style');
st.textContent='img,video,picture,canvas,svg,[style*=background-image]'+
'{filter:invert(1) hue-rotate(180deg)!important}';
document.documentElement.appendChild(st);
})();""",
    "Cookiebanners verbergen": """(function(){
var sel=['#onetrust-banner-sdk','#onetrust-consent-sdk','.cc-window',
'#cookieConsent','.qc-cmp2-container','[class*=cookie-consent]',
'[id*=cookie-banner]','[aria-label*=cookie]','[aria-label*=Cookie]'];
function clean(){sel.forEach(function(s){
document.querySelectorAll(s).forEach(function(e){e.style.display='none';});});
if(document.body)document.body.style.overflow='auto';}
clean();setTimeout(clean,1200);setTimeout(clean,3000);
})();""",
    "Grotere leesbare tekst": """(function(){
var st=document.createElement('style');
st.textContent='html{font-size:118%!important}'+
'p,li,span,a,div{line-height:1.6!important}';
document.documentElement.appendChild(st);
})();""",
    "Links in nieuw tabblad": """(function(){
function fix(){document.querySelectorAll('a[href]').forEach(function(a){
a.target='_blank';a.rel='noopener';});}
fix();document.addEventListener('DOMContentLoaded',fix);setTimeout(fix,1500);
})();""",
    "Zwevende balken verwijderen": """(function(){
function unstick(){document.querySelectorAll('*').forEach(function(e){
var p=getComputedStyle(e).position;
if(p==='fixed'||p==='sticky'){e.style.position='static';}});}
unstick();setTimeout(unstick,1500);
})();""",
}


class Blocker(QWebEngineUrlRequestInterceptor):
    def __init__(self, browser=None):
        super().__init__()
        self.browser = browser
        self.count = 0

    def interceptRequest(self, info):
        u = info.requestUrl()
        host = u.host().lower()
        url = u.toString().lower()
        for d in BLOCK:
            if host.endswith(d) or d in url:
                info.block(True)
                self.count += 1
                return
        # HTTPS-only: onveilige http automatisch naar https tillen
        try:
            if (self.browser is not None
                    and self.browser.settings.get("https_only", True)
                    and u.scheme() == "http"
                    and not host.endswith(".onion")
                    and host not in ("127.0.0.1", "localhost")):
                up = QUrl(u)
                up.setScheme("https")
                info.redirect(up)
        except Exception:
            pass


class FavBar(QToolBar):
    """Favorietenbalk die gesleepte URL's accepteert."""
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.setMovable(False)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasUrls() or md.hasText():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        url = ""
        if md.hasUrls() and md.urls():
            url = md.urls()[0].toString()
        elif md.hasText():
            url = md.text().strip()
        if url:
            self.browser.add_bookmark_url(url)
        e.acceptProposedAction()


class WebPage(QWebEnginePage):
    """Pagina met: links in nieuw tabblad, rechten weigeren, fullscreen."""
    def __init__(self, profile, browser):
        super().__init__(profile, browser)
        self.browser = browser
        self.featurePermissionRequested.connect(self._perm)
        self.fullScreenRequested.connect(self._fs)

    def createWindow(self, _type):
        return self.browser.add_tab(QUrl("about:blank"), return_page=True)

    def _perm(self, origin, feature):
        # privacy-first: alle aanvragen (mic, camera, locatie, meldingen) weigeren
        self.setFeaturePermission(
            origin, feature,
            QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)

    def _fs(self, req):
        req.accept()
        self.browser.set_fullscreen(req.toggleOn())


class TorSig(QObject):
    status = pyqtSignal(str)
    ready = pyqtSignal(int, bool)
    failed = pyqtSignal()


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("title"))
        self.resize(1100, 760)
        ic = os.path.join(TM.app_dir(), "assets", "icon.ico")
        if os.path.exists(ic):
            self.setWindowIcon(QIcon(ic))
        self.tor_port = None
        self.managed = False
        self.tor_ok = False
        self.js_on = True
        self.settings = self._load_settings()
        self.favs = self._load_favs()
        self.downloads = []      # bijgehouden downloads (item-objecten)
        self._vkey = None        # wachtwoordkluis (in geheugen na ontgrendelen)
        self._vsalt = None
        self._vault = []

        # privé profiel (off-the-record: niets op schijf)
        self.profile = QWebEngineProfile(self)   # geen naam = off-the-record
        self.profile.setHttpUserAgent(UA)
        self.blocker = Blocker(self)
        self.profile.setUrlRequestInterceptor(self.blocker)
        s = self.profile.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        try:
            s.setAttribute(
                QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, True)
            s.setAttribute(
                QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        except Exception:
            pass

        self.profile.downloadRequested.connect(self.on_download)
        self._init_scripts()
        self._build_ui()
        self._apply_dark()
        self.rebuild_favbar()
        self._shortcuts()
        self.add_tab(QUrl("about:blank"))
        self.current_view().setHtml(self._wait_html())

        self.sig = TorSig()
        self.sig.status.connect(self.on_status)
        self.sig.ready.connect(self.on_ready)
        self.sig.failed.connect(self.on_failed)
        self.start_tor()

        # tracker-teller in de statusbalk bijwerken
        self._blk_timer = QTimer(self)
        self._blk_timer.timeout.connect(self._update_blocked)
        self._blk_timer.start(1500)

    # ---- UI ----
    def _build_ui(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        st = self.style()

        def act(sp, slot):
            a = QAction(st.standardIcon(sp), "", self)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        act(QStyle.StandardPixmap.SP_ArrowBack, lambda: self.current_view().back())
        act(QStyle.StandardPixmap.SP_ArrowForward,
            lambda: self.current_view().forward())
        act(QStyle.StandardPixmap.SP_BrowserReload,
            lambda: self.current_view().reload())
        act(QStyle.StandardPixmap.SP_DirHomeIcon,
            lambda: self.show_start(self.current_view()))
        self.bar = QLineEdit()
        self.bar.setPlaceholderText("https://...  /  .onion")
        self.bar.returnPressed.connect(self.nav)
        self.bar.setDragEnabled(True)   # sleep de URL naar de favorietenbalk
        tb.addWidget(self.bar)
        bnt = QPushButton("+")
        bnt.setToolTip(T("newtab"))
        bnt.clicked.connect(self.new_tab)
        tb.addWidget(bnt)
        star = QPushButton(T("save_bm"))
        star.setToolTip(T("save_bm"))
        star.clicked.connect(self.add_bookmark)
        tb.addWidget(star)
        fmap = QPushButton(T("new_folder"))
        fmap.clicked.connect(self.new_folder)
        tb.addWidget(fmap)
        pdfb = QPushButton(T("pdf"))
        pdfb.clicked.connect(self.save_pdf)
        tb.addWidget(pdfb)
        # ⋮-menu (zoals Chrome): minder gebruikte knoppen netjes bij elkaar
        menu_btn = QToolButton()
        menu_btn.setText("⋮")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(menu_btn)
        self.js_action = m.addAction(T("js"))
        self.js_action.setCheckable(True)
        self.js_action.setChecked(True)
        self.js_action.triggered.connect(self.toggle_js)
        m.addAction(T("newid"), self.new_identity)
        m.addAction(T("reader"), self.reader_mode)
        m.addAction(T("scripts"), self.open_scripts)
        m.addAction(T("pw"), self.open_passwords)
        m.addAction(T("downloads"), self.open_downloads)
        m.addAction(T("print"), self.do_print)
        m.addSeparator()
        # zoekmachine kiezen (radio)
        eng_menu = m.addMenu(T("engine"))
        self._eng_actions = {}
        for key, (label, _u, _p) in SEARCH_ENGINES.items():
            a = eng_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.settings.get("engine", DEFAULT_ENGINE) == key)
            a.triggered.connect(lambda _=False, k=key: self.set_engine(k))
            self._eng_actions[key] = a
        # HTTPS-only schakelaar
        self.https_action = m.addAction(T("https_only"))
        self.https_action.setCheckable(True)
        self.https_action.setChecked(self.settings.get("https_only", True))
        self.https_action.triggered.connect(self.toggle_https_only)
        m.addSeparator()
        m.addAction(T("donate"), lambda: QDesktopServices.openUrl(QUrl(DONATE)))
        m.addAction(T("info"), self.show_info)
        menu_btn.setMenu(m)
        tb.addWidget(menu_btn)
        tb.setIconSize(QSize(26, 26))
        tb.setStyleSheet(
            "QToolBar{padding:5px;spacing:7px;}"
            "QToolBar QPushButton,QToolBar QToolButton{font-size:14px;"
            "font-weight:bold;padding:8px 13px;background:#2a2440;color:#efeaff;"
            "border:1px solid #5a4d86;border-radius:9px;}"
            "QToolBar QPushButton:hover,QToolBar QToolButton:hover{"
            "background:#463a6e;}"
            "QToolBar QToolButton::menu-indicator{width:0px;}"
            "QToolBar QLineEdit{font-size:15px;padding:8px 12px;}")

        # favorietenbalk (tweede rij) - groter en duidelijker
        self.favbar = FavBar(self)
        self.favbar.setStyleSheet(
            "QToolBar{padding:5px;spacing:7px;background:#1b1729;}"
            "QToolBar QPushButton,QToolBar QToolButton{font-size:14px;"
            "font-weight:bold;padding:8px 14px;background:#2f2850;color:#efeaff;"
            "border:1px solid #5a4d86;border-radius:9px;}"
            "QToolBar QPushButton:hover,QToolBar QToolButton:hover{"
            "background:#463a6e;}"
            "QToolBar QToolButton::menu-indicator{width:0px;}"
            "QToolBar QLabel{font-size:13px;color:#9b90c0;}")
        self.addToolBarBreak()
        self.addToolBar(self.favbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.sec_lbl = QLabel("  ")
        self.status.addPermanentWidget(self.sec_lbl)
        self.blk_lbl = QLabel("  🛡 0  ")
        self.blk_lbl.setToolTip(T("blocked"))
        self.status.addPermanentWidget(self.blk_lbl)
        self.tor_lbl = QLabel("  " + T("connecting") + "  ")
        self.status.addPermanentWidget(self.tor_lbl)

        # zoekbalk (Ctrl+F), onderaan, standaard verborgen
        self.findbar = QToolBar()
        self.findbar.setMovable(False)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(T("find"))
        self.find_edit.textChanged.connect(self._find)
        self.find_edit.returnPressed.connect(
            lambda: self._find(self.find_edit.text()))
        self.findbar.addWidget(self.find_edit)
        for sym, fn in (("▲", self._find_prev),
                        ("▼", lambda: self._find(self.find_edit.text())),
                        ("✕", lambda: self.findbar.hide())):
            b = QPushButton(sym)
            b.clicked.connect(fn)
            self.findbar.addWidget(b)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.findbar)
        self.findbar.hide()

    def _apply_dark(self):
        self.setStyleSheet(
            "QMainWindow,QToolBar,QTabWidget::pane,QStatusBar{background:#16131f;}"
            "QLineEdit{background:#0e0c16;color:#e8e6f0;border:1px solid #4a3d66;"
            "border-radius:8px;padding:6px;}"
            "QPushButton{background:#2a2440;color:#e8e6f0;border:1px solid #4a3d66;"
            "border-radius:7px;padding:5px 9px;}QPushButton:hover{background:#3a3157;}"
            "QTabBar::tab{background:#241f36;color:#cfc8e6;padding:7px 12px;}"
            "QTabBar::tab:selected{background:#4a3d80;color:#fff;}"
            "QLabel{color:#bdb3da;}QStatusBar{color:#bdb3da;}")

    # ---- tabs ----
    def add_tab(self, url, load_wait=False, return_page=False):
        view = QWebEngineView()
        page = WebPage(self.profile, self)
        view.setPage(page)
        view.urlChanged.connect(lambda u, v=view: self._url_changed(u, v))
        view.titleChanged.connect(lambda t, v=view: self._title_changed(t, v))
        view.iconChanged.connect(lambda ic, v=view: self._icon_changed(ic, v))
        view.loadProgress.connect(lambda p, v=view: self._progress(p, v))
        page.linkHovered.connect(self._hover)
        i = self.tabs.addTab(view, "…")
        self.tabs.setCurrentIndex(i)
        if return_page:
            return page
        if load_wait:
            view.setHtml(self._wait_html())
        elif url.toString() not in ("", "about:blank"):
            view.load(url)
        return view

    def _icon_changed(self, icon, view):
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabIcon(i, icon)

    def _progress(self, p, view):
        if view is self.current_view():
            if 0 < p < 100:
                self.status.showMessage("%s %d%%" % (T("loading"), p))
            else:
                self.status.clearMessage()

    def _hover(self, link):
        if link:
            self.status.showMessage(link, 4000)

    def close_tab(self, i):
        if self.tabs.count() <= 1:
            return
        w = self.tabs.widget(i)
        self.tabs.removeTab(i)
        w.deleteLater()

    def current_view(self):
        return self.tabs.currentWidget()

    def tab_changed(self, i):
        v = self.current_view()
        if v:
            self.bar.setText(v.url().toString())

    def _url_changed(self, url, view):
        if view is self.current_view():
            s = url.toString()
            self.bar.setText("" if s in ("about:blank", "") else s)
            self._update_security(url)

    def _update_security(self, url):
        if url.scheme() == "https":
            self.sec_lbl.setText(" 🔒 ")
        elif url.host().endswith(".onion"):
            self.sec_lbl.setText(" 🧅 ")
        elif url.scheme() in ("http",):
            self.sec_lbl.setText(" ⚠ ")
        else:
            self.sec_lbl.setText("  ")

    def _title_changed(self, title, view):
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabText(i, (title[:18] + "…") if len(title) > 19
                                 else (title or "…"))

    # ---- navigatie ----
    def nav(self):
        self.go(self.bar.text().strip())

    def go(self, text):
        if not text:
            return
        if not self.tor_ok:
            self.status.showMessage(T("wait_tor"), 4000)
            return
        if "." in text and " " not in text and "://" not in text:
            text = "https://" + text
        elif "://" not in text:
            _name, base, param = SEARCH_ENGINES.get(
                self.settings.get("engine", DEFAULT_ENGINE), SEARCH_ENGINES["ddg"])
            text = "%s?%s=%s" % (base, param, quote(text))
        if (self.settings.get("https_only", True)
                and text.startswith("http://")
                and not QUrl(text).host().lower().endswith(".onion")):
            text = "https://" + text[len("http://"):]
        self.current_view().load(QUrl(text))

    # ---- tor ----
    def start_tor(self):
        threading.Thread(target=self._tor_worker, daemon=True).start()

    def _tor_worker(self):
        try:
            port, managed = TM.ensure_tor(lambda s: self.sig.status.emit(s))
            if port:
                self.sig.ready.emit(port, managed)
            else:
                self.sig.failed.emit()
        except Exception as e:
            self.sig.status.emit("Fout: %s" % e)
            self.sig.failed.emit()

    def on_status(self, s):
        self.tor_lbl.setText("  " + s + "  ")

    def on_ready(self, port, managed):
        self.tor_port = port
        self.managed = managed
        self.tor_ok = True
        proxy = QNetworkProxy(QNetworkProxy.ProxyType.Socks5Proxy,
                              "127.0.0.1", port)
        QNetworkProxy.setApplicationProxy(proxy)
        self.tor_lbl.setText("  🧅 %s (%d)  " % (T("connected"), port))
        self.show_start(self.current_view())

    def on_failed(self):
        self.tor_ok = False
        self.tor_lbl.setText("  ⚠ " + T("notor") + "  ")
        self.current_view().setHtml(self._fail_html())

    def new_identity(self):
        if not self.tor_ok:
            self.status.showMessage(T("wait_tor"), 4000)
            return
        if self.managed:
            msg = T("newid_ok") if TM.new_identity() else T("newid_fail")
        else:
            msg = T("newid_no")
        QMessageBox.information(self, T("newid"), msg + "\n\n" + T("newid_info"))
        self.add_tab(QUrl("https://check.torproject.org/"))

    def toggle_js(self, checked=None):
        self.js_on = (not self.js_on) if checked is None else bool(checked)
        self.profile.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, self.js_on)
        if hasattr(self, "js_action"):
            self.js_action.setChecked(self.js_on)
        v = self.current_view()
        if v:
            v.reload()

    def show_info(self):
        QMessageBox.information(self, T("info"), T("about"))

    # ---- instellingen (zoekmachine / https-only) ----
    def _settings_path(self):
        return os.path.join(TM.cache_dir(), "settings.json")

    def _load_settings(self):
        defaults = {"engine": DEFAULT_ENGINE, "https_only": True}
        try:
            with open(self._settings_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def _save_settings(self):
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings, f)
        except Exception:
            pass

    def set_engine(self, key):
        if key not in SEARCH_ENGINES:
            return
        self.settings["engine"] = key
        self._save_settings()
        for k, a in getattr(self, "_eng_actions", {}).items():
            a.setChecked(k == key)
        self.status.showMessage(SEARCH_ENGINES[key][0], 2500)

    def toggle_https_only(self, checked=None):
        self.settings["https_only"] = (
            not self.settings.get("https_only", True)
            if checked is None else bool(checked))
        self._save_settings()
        if hasattr(self, "https_action"):
            self.https_action.setChecked(self.settings["https_only"])

    # ---- startpagina / nieuw tabblad ----
    def new_tab(self):
        v = self.add_tab(QUrl("about:blank"))
        if self.tor_ok:
            self.show_start(v)
        else:
            v.setHtml(self._wait_html())
        return v

    def show_start(self, view):
        if view is not None:
            view.setHtml(self.start_html(), QUrl("about:blank"))
            self.bar.setText("")
            self.bar.setFocus()

    def _logo_uri(self):
        # logo (witte draak, transparant) als data-URI voor de startpagina
        if getattr(self, "_logo_cache", None) is not None:
            return self._logo_cache
        self._logo_cache = ""
        for n in ("logo_t.png", "logo.png", "icon-256.png"):
            p = os.path.join(TM.app_dir(), "assets", n)
            if os.path.exists(p):
                try:
                    import base64 as _b64
                    with open(p, "rb") as f:
                        b = _b64.b64encode(f.read()).decode("ascii")
                    self._logo_cache = "data:image/png;base64," + b
                    break
                except Exception:
                    pass
        return self._logo_cache

    def start_html(self):
        name, base, param = SEARCH_ENGINES.get(
            self.settings.get("engine", DEFAULT_ENGINE), SEARCH_ENGINES["ddg"])
        tiles = []
        for it in self.favs:
            if it.get("type") == "folder":
                for link in it.get("items", []):
                    tiles.append(link)
            else:
                tiles.append(it)
        cells = ""
        for link in tiles[:24]:
            url = _html.escape(link.get("url", ""), quote=True)
            label = _html.escape((link.get("title") or link.get("url") or "?")[:22])
            cells += ('<a class="tile" href="%s">%s</a>' % (url, label))
        cells += ('<a class="tile chk" href="%s">🧅 %s</a>'
                  % (HOME, _html.escape(T("start_check"))))
        favs_label = _html.escape(T("start_favs"))
        tip = _html.escape(T("start_tip"))
        secure = _html.escape(T("start_secure"))
        logo = self._logo_uri()
        logo_html = ('<img class="logo" src="%s" alt="DraveOnion">' % logo
                     if logo else '<div class="logo">🐉</div>')
        return """<!doctype html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;}
html,body{margin:0;height:100%%;background:#16131f;color:#e8e6f0;
font-family:'Segoe UI',sans-serif;}
.wrap{max-width:760px;margin:0 auto;padding:80px 24px 40px;text-align:center;}
.logo{font-size:54px;}
img.logo{width:190px;height:190px;object-fit:contain;margin-bottom:4px;
filter:drop-shadow(0 4px 16px rgba(150,110,210,.5));}
h1{font-weight:600;letter-spacing:.5px;margin:6px 0 2px;}
.sub{color:#9b90c0;margin-bottom:30px;font-size:14px;}
form{display:flex;gap:8px;justify-content:center;margin-bottom:14px;}
input[type=text]{flex:1;max-width:520px;font-size:17px;padding:14px 18px;
border-radius:30px;border:1px solid #5a4d86;background:#0e0c16;color:#e8e6f0;
outline:none;}
input[type=text]:focus{border-color:#9b7de0;}
button{font-size:16px;padding:0 22px;border-radius:30px;border:1px solid #5a4d86;
background:#463a6e;color:#fff;cursor:pointer;}
button:hover{background:#5a4a8a;}
.tip{color:#7d7299;font-size:13px;margin-bottom:36px;}
.section{color:#9b90c0;font-size:13px;text-transform:uppercase;
letter-spacing:1px;text-align:left;margin:0 0 12px 4px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
gap:12px;}
.tile{display:block;padding:16px 12px;border-radius:12px;background:#241f36;
border:1px solid #382f55;color:#dcd4f0;text-decoration:none;font-size:14px;
font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tile:hover{background:#34294f;border-color:#5a4d86;}
.tile.chk{background:#1d2a1d;border-color:#36502f;color:#bfe6b8;}
</style></head><body><div class="wrap">
%s
<h1>DraveOnion</h1>
<div class="sub">%s · %s</div>
<form action="%s" method="get" autocomplete="off">
<input type="text" name="%s" placeholder="%s" autofocus>
<button type="submit">%s</button>
</form>
<div class="section">%s</div>
<div class="grid">%s</div>
</div></body></html>""" % (
            logo_html, secure, _html.escape(name), base, param, tip,
            "🔍", favs_label, cells)

    # ---- leesmodus ----
    def reader_mode(self):
        v = self.current_view()
        if v:
            v.page().runJavaScript(READER_JS)

    # ---- tracker-teller ----
    def _update_blocked(self):
        try:
            self.blk_lbl.setText("  🛡 %d  " % self.blocker.count)
        except Exception:
            pass

    # ---- favorieten ----
    def _favs_path(self):
        return os.path.join(TM.cache_dir(), "favorites.json")

    def _load_favs(self):
        path = self._favs_path()
        # verse installatie (ook in de EXE): standaard onion-map klaarzetten
        if not os.path.exists(path):
            favs = json.loads(json.dumps(DEFAULT_FAVS))   # diepe kopie
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(favs, f)
            except Exception:
                pass
            return favs
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = []
            for it in data:
                if not isinstance(it, dict):
                    continue
                if it.get("type") == "folder":
                    it.setdefault("items", [])
                    out.append(it)
                else:
                    it["type"] = "link"
                    out.append(it)
            return out
        except Exception:
            return []

    def _save_favs(self):
        try:
            with open(self._favs_path(), "w", encoding="utf-8") as f:
                json.dump(self.favs, f)
        except Exception:
            pass

    def rebuild_favbar(self):
        self.favbar.clear()
        if not self.favs:
            self.favbar.addWidget(QLabel(T("no_favs")))
            return
        for i, item in enumerate(self.favs):
            if item.get("type") == "folder":
                tbn = QToolButton()
                tbn.setText("📁 " + (item.get("name") or "map"))
                tbn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                menu = QMenu(tbn)
                items = item.get("items", [])
                for link in items:
                    a = menu.addAction(link.get("title") or link.get("url", "?"))
                    a.triggered.connect(
                        lambda _=False, u=link.get("url", ""): self.go(u))
                if items:
                    menu.addSeparator()
                    rmsub = menu.addMenu(T("rm_in_folder"))
                    for j, link in enumerate(items):
                        ra = rmsub.addAction(link.get("title")
                                             or link.get("url", "?"))
                        ra.triggered.connect(
                            lambda _=False, fi=i, li=j:
                            self.remove_in_folder(fi, li))
                rm = menu.addAction(T("rm_folder"))
                rm.triggered.connect(lambda _=False, idx=i: self.remove_item(idx))
                tbn.setMenu(menu)
                self.favbar.addWidget(tbn)
            else:
                b = QPushButton(item.get("title") or item.get("url", "?"))
                b.setToolTip(item.get("url", ""))
                b.clicked.connect(
                    lambda _=False, u=item.get("url", ""): self.go(u))
                b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                b.customContextMenuRequested.connect(
                    lambda _pos, idx=i, btn=b: self._link_menu(idx, btn))
                self.favbar.addWidget(b)

    def _link_menu(self, idx, btn):
        m = QMenu(self)
        rm = m.addAction(T("rm_bm"))
        folder_acts = {}
        folders = [(k, it) for k, it in enumerate(self.favs)
                   if it.get("type") == "folder"]
        if folders:
            sub = m.addMenu(T("to_folder"))
            for k, it in folders:
                a = sub.addAction("📁 " + (it.get("name") or "map"))
                folder_acts[a] = k
        chosen = m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        if chosen == rm:
            self.remove_item(idx)
        elif chosen in folder_acts:
            self.move_to_folder(idx, folder_acts[chosen])

    def add_bookmark(self):
        v = self.current_view()
        if v:
            self.add_bookmark_url(v.url().toString(), v.title())

    def add_bookmark_url(self, url, title=None):
        url = (url or "").strip()
        if not url or url.startswith("about:") or url == "data:,":
            return
        if "://" not in url and "." in url:
            url = "https://" + url
        if any(it.get("type") != "folder" and it.get("url") == url
               for it in self.favs):
            self.status.showMessage(T("bm_added"), 3000)
            return
        if not title:
            title = QUrl(url).host() or url
        self.favs.append({"type": "link", "title": title[:22], "url": url})
        self._save_favs()
        self.rebuild_favbar()
        self.status.showMessage(T("bm_added"), 3000)

    def new_folder(self):
        name, ok = QInputDialog.getText(self, T("new_folder"), T("folder_name"))
        if ok and name.strip():
            self.favs.append({"type": "folder", "name": name.strip()[:18],
                              "items": []})
            self._save_favs()
            self.rebuild_favbar()

    def move_to_folder(self, link_idx, folder_idx):
        if not (0 <= link_idx < len(self.favs)):
            return
        link = self.favs[link_idx]
        if link.get("type") != "link":
            return
        self.favs[folder_idx].setdefault("items", []).append(link)
        del self.favs[link_idx]
        self._save_favs()
        self.rebuild_favbar()

    def remove_item(self, idx):
        if 0 <= idx < len(self.favs):
            del self.favs[idx]
            self._save_favs()
            self.rebuild_favbar()

    def remove_in_folder(self, fi, li):
        if 0 <= fi < len(self.favs) and self.favs[fi].get("type") == "folder":
            items = self.favs[fi].get("items", [])
            if 0 <= li < len(items):
                del items[li]
                self._save_favs()
                self.rebuild_favbar()

    # ---- userscripts (Tampermonkey-stijl) ----
    def _scripts_dir(self):
        d = os.path.join(TM.cache_dir(), "userscripts")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _meta_path(self):
        return os.path.join(self._scripts_dir(), "_enabled.json")

    def _load_meta(self):
        try:
            with open(self._meta_path(), "r", encoding="utf-8") as f:
                return dict(json.load(f))
        except Exception:
            return {}

    def _save_meta(self):
        meta = {s["name"]: s["enabled"] for s in self.userscripts}
        try:
            with open(self._meta_path(), "w", encoding="utf-8") as f:
                json.dump(meta, f)
        except Exception:
            pass

    def load_scripts(self):
        meta = self._load_meta()
        out = []
        d = self._scripts_dir()
        try:
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".js"):
                    name = fn[:-3]
                    out.append({"name": name, "path": os.path.join(d, fn),
                                "enabled": meta.get(name, True)})
        except Exception:
            pass
        return out

    def apply_scripts(self):
        coll = self.profile.scripts()
        coll.clear()
        for s in self.userscripts:
            if not s["enabled"]:
                continue
            try:
                with open(s["path"], "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                continue
            sc = QWebEngineScript()
            sc.setName(s["name"])
            sc.setSourceCode(code)
            sc.setInjectionPoint(
                QWebEngineScript.InjectionPoint.DocumentReady)
            sc.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            sc.setRunsOnSubFrames(False)
            coll.insert(sc)

    def _ensure_builtins(self):
        d = self._scripts_dir()
        marker = os.path.join(d, ".builtins_done")
        if os.path.exists(marker):
            return
        meta = self._load_meta()
        for name, code in BUILTIN_SCRIPTS.items():
            p = os.path.join(d, name + ".js")
            if not os.path.exists(p):
                try:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(code)
                except Exception:
                    continue
            meta.setdefault(name, False)   # standaard uit
        try:
            with open(self._meta_path(), "w", encoding="utf-8") as f:
                json.dump(meta, f)
            with open(marker, "w", encoding="utf-8") as f:
                f.write("1")
        except Exception:
            pass

    def _init_scripts(self):
        self._ensure_builtins()
        self.userscripts = self.load_scripts()
        self.apply_scripts()

    def open_scripts(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("scripts_title"))
        dlg.resize(420, 360)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(T("scripts_title")))
        lst = QListWidget()

        def fill():
            lst.clear()
            for s in self.userscripts:
                it = QListWidgetItem(s["name"])
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked if s["enabled"]
                                 else Qt.CheckState.Unchecked)
                lst.addItem(it)

        fill()
        lay.addWidget(lst)

        def sync():
            for i, s in enumerate(self.userscripts):
                it = lst.item(i)
                if it:
                    s["enabled"] = it.checkState() == Qt.CheckState.Checked
            self._save_meta()
            self.apply_scripts()

        lst.itemChanged.connect(lambda _i: sync())

        def add():
            name, ok = QInputDialog.getText(dlg, T("new_script"),
                                            T("script_name"))
            if not (ok and name.strip()):
                return
            code, ok2 = QInputDialog.getMultiLineText(
                dlg, T("new_script"), T("script_code"),
                "// " + name.strip() + "\nconsole.log('hallo van %s');"
                % name.strip())
            if not ok2:
                return
            safe = "".join(c for c in name.strip()
                           if c.isalnum() or c in " -_")[:40] or "script"
            try:
                with open(os.path.join(self._scripts_dir(), safe + ".js"),
                          "w", encoding="utf-8") as f:
                    f.write(code)
            except Exception:
                return
            self.userscripts = self.load_scripts()
            self.apply_scripts()
            fill()

        def remove():
            i = lst.currentRow()
            if 0 <= i < len(self.userscripts):
                try:
                    os.remove(self.userscripts[i]["path"])
                except Exception:
                    pass
                self.userscripts = self.load_scripts()
                self.apply_scripts()
                fill()

        row = QHBoxLayout()
        b1 = QPushButton(T("new_script"))
        b1.clicked.connect(add)
        b2 = QPushButton(T("rm_script"))
        b2.clicked.connect(remove)
        b3 = QPushButton(T("open_folder"))
        b3.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(self._scripts_dir())))
        b4 = QPushButton(T("close"))
        b4.clicked.connect(dlg.accept)
        for b in (b1, b2, b3, b4):
            row.addWidget(b)
        lay.addLayout(row)
        dlg.exec()
        v = self.current_view()
        if v:
            v.reload()

    # ---- pagina's ----
    def _page(self, title, body):
        return ("<html><body style='background:#16131f;color:#e8e6f0;"
                "font-family:Segoe UI;text-align:center;padding-top:90px'>"
                "<h1 style='color:#b59cff'>🧅 DraveOnion</h1>"
                "<h2>%s</h2><p style='color:#bdb3da'>%s</p></body></html>"
                % (title, body))

    def _wait_html(self):
        return self._page(T("connecting"),
                          "Tor wordt opgezet..." if LANG == "nl"
                          else "Setting up Tor...")

    def _fail_html(self):
        b = ("Kon geen Tor-verbinding maken. Open je Tor Browser of controleer "
             "je internet, en klik op 'Opnieuw proberen'."
             if LANG == "nl" else
             "Could not connect to Tor. Open your Tor Browser or check your "
             "internet, then click 'Retry'.")
        return self._page(T("notor"), b)

    # ---- downloads ----
    def on_download(self, item):
        name = item.downloadFileName()
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        try:
            os.makedirs(dl, exist_ok=True)
        except Exception:
            pass
        path, _ = QFileDialog.getSaveFileName(self, T("save_as"),
                                              os.path.join(dl, name))
        if not path:
            item.cancel()
            return
        item.setDownloadDirectory(os.path.dirname(path))
        item.setDownloadFileName(os.path.basename(path))
        item.accept()
        self.downloads.append(item)
        self.status.showMessage("%s %s" % (T("downloading"),
                                           os.path.basename(path)))
        item.isFinishedChanged.connect(lambda it=item: self._dl_done(it))

    def _dl_done(self, item):
        if item.isFinished():
            self.status.showMessage("%s %s" % (T("download_done"),
                                               item.downloadFileName()), 6000)

    def open_downloads(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("downloads"))
        dlg.resize(480, 360)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        lay.addWidget(lst)

        def fill():
            lst.clear()
            if not self.downloads:
                lst.addItem(T("dl_none"))
                return
            for it in self.downloads:
                try:
                    name = it.downloadFileName()
                    if it.isFinished():
                        state = "✓ " + T("dl_ok")
                    else:
                        recv = it.receivedBytes()
                        tot = it.totalBytes() or 0
                        pct = int(recv * 100 / tot) if tot > 0 else 0
                        state = "%d%% %s" % (pct, T("dl_busy"))
                    lst.addItem("%s  —  %s" % (name, state))
                except Exception:
                    pass
        fill()

        def open_folder():
            d = os.path.join(os.path.expanduser("~"), "Downloads")
            if self.downloads:
                try:
                    d = self.downloads[-1].downloadDirectory() or d
                except Exception:
                    pass
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))

        def clear():
            self.downloads = [it for it in self.downloads
                              if not it.isFinished()]
            fill()

        row = QHBoxLayout()
        for label, fn in ((T("retry"), fill), (T("dl_open"), open_folder),
                          (T("dl_clear"), clear), (T("close"), dlg.accept)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        dlg.exec()

    # ---- zoeken op pagina ----
    def show_find(self):
        self.findbar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def _find(self, text):
        v = self.current_view()
        if v:
            v.findText(text)

    def _find_prev(self):
        v = self.current_view()
        if v:
            v.findText(self.find_edit.text(),
                       QWebEnginePage.FindFlag.FindBackward)

    # ---- zoom / sneltoetsen / fullscreen ----
    def zoom(self, d):
        v = self.current_view()
        if not v:
            return
        z = 1.0 if d == 0 else max(0.3, min(3.0, v.zoomFactor() + d))
        v.setZoomFactor(z)

    def _focus_bar(self):
        self.bar.setFocus()
        self.bar.selectAll()

    def _next_tab(self):
        n = self.tabs.count()
        if n > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % n)

    def do_print(self):
        v = self.current_view()
        if not v:
            return
        if HAS_PRINT:
            try:
                # printer als attribuut bewaren: print() is asynchroon, dus de
                # printer mag niet worden opgeruimd terwijl het printen loopt
                self._printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                dlg = QPrintDialog(self._printer, self)
                if dlg.exec():
                    v.print(self._printer)
                return
            except Exception:
                pass
        self.save_pdf()

    def save_pdf(self):
        v = self.current_view()
        if not v:
            return
        title = (v.title() or "pagina").strip()
        safe = "".join(c for c in title
                       if c.isalnum() or c in " -_().") .strip()[:60] or "pagina"
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        path, _ = QFileDialog.getSaveFileName(
            self, T("save_as"), os.path.join(dl, safe + ".pdf"), "PDF (*.pdf)")
        if path:
            v.page().printToPdf(path)
            self.status.showMessage("PDF: " + path, 6000)

    def toggle_fullscreen(self):
        self.set_fullscreen(not self.isFullScreen())

    def set_fullscreen(self, on):
        # uitstellen naar de volgende lus-tik: voorkomt een QtWebEngine-crash
        # als de vensterstand midden in een toets-/pagina-event wisselt
        def apply():
            try:
                if on:
                    self.showFullScreen()
                else:
                    self.showNormal()
            except Exception:
                pass
        QTimer.singleShot(0, apply)

    def _shortcuts(self):
        def sc(seq, fn):
            QShortcut(QKeySequence(seq), self).activated.connect(fn)

        sc("Ctrl+T", self.new_tab)
        sc("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex()))
        sc("Ctrl+L", self._focus_bar)
        sc("Ctrl+R", lambda: self.current_view().reload())
        sc("F5", lambda: self.current_view().reload())
        sc("Alt+Left", lambda: self.current_view().back())
        sc("Alt+Right", lambda: self.current_view().forward())
        sc("Ctrl+F", self.show_find)
        sc("Escape", self.findbar.hide)
        sc("Ctrl+=", lambda: self.zoom(0.1))
        sc("Ctrl++", lambda: self.zoom(0.1))
        sc("Ctrl+-", lambda: self.zoom(-0.1))
        sc("Ctrl+0", lambda: self.zoom(0))
        sc("F11", self.toggle_fullscreen)
        sc("Ctrl+P", self.do_print)
        sc("Ctrl+Tab", self._next_tab)

    # ---- wachtwoordbeheer (versleutelde kluis) ----
    def _vault_path(self):
        return os.path.join(TM.cache_dir(), "vault.dat")

    def _derive_key(self, master, salt):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=200000)
        return base64.urlsafe_b64encode(kdf.derive(master.encode("utf-8")))

    def _save_vault(self):
        try:
            token = Fernet(self._vkey).encrypt(
                json.dumps(self._vault).encode("utf-8")).decode("utf-8")
            with open(self._vault_path(), "w", encoding="utf-8") as f:
                json.dump({"salt": base64.b64encode(self._vsalt).decode(),
                           "data": token}, f)
        except Exception:
            pass

    def _unlock_vault(self):
        if self._vkey is not None:
            return True
        if not HAS_CRYPTO:
            QMessageBox.information(self, T("pw_title"), T("pw_nocrypto"))
            return False
        path = self._vault_path()
        if os.path.exists(path):
            pw, ok = QInputDialog.getText(self, T("pw_title"), T("pw_enter"),
                                          QLineEdit.EchoMode.Password)
            if not ok:
                return False
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                salt = base64.b64decode(obj["salt"])
                key = self._derive_key(pw, salt)
                entries = json.loads(
                    Fernet(key).decrypt(obj["data"].encode()).decode())
                self._vkey, self._vsalt, self._vault = key, salt, entries
                return True
            except Exception:
                QMessageBox.warning(self, T("pw_title"), T("pw_wrong"))
                return False
        pw, ok = QInputDialog.getText(self, T("pw_title"), T("pw_set"),
                                      QLineEdit.EchoMode.Password)
        if not ok or not pw:
            return False
        pw2, ok2 = QInputDialog.getText(self, T("pw_title"), T("pw_set2"),
                                        QLineEdit.EchoMode.Password)
        if not ok2 or pw2 != pw:
            QMessageBox.warning(self, T("pw_title"), T("pw_nomatch"))
            return False
        self._vsalt = os.urandom(16)
        self._vkey = self._derive_key(pw, self._vsalt)
        self._vault = []
        self._save_vault()
        return True

    def open_passwords(self):
        if not self._unlock_vault():
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(T("pw_title"))
        dlg.resize(460, 380)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()

        def fill():
            lst.clear()
            for e in self._vault:
                lst.addItem("%s  —  %s" % (e.get("site", "?"), e.get("user", "")))
        fill()
        lay.addWidget(lst)

        def add():
            site, ok = QInputDialog.getText(dlg, T("pw_add"), T("pw_site"))
            if not (ok and site.strip()):
                return
            user, ok2 = QInputDialog.getText(dlg, T("pw_add"), T("pw_user"))
            if not ok2:
                return
            pw, ok3 = QInputDialog.getText(dlg, T("pw_add"), T("pw_pass"),
                                           QLineEdit.EchoMode.Password)
            if not ok3:
                return
            self._vault.append({"site": site.strip(), "user": user, "pass": pw})
            self._save_vault()
            fill()

        def remove():
            i = lst.currentRow()
            if 0 <= i < len(self._vault):
                del self._vault[i]
                self._save_vault()
                fill()

        def copy(field):
            i = lst.currentRow()
            if 0 <= i < len(self._vault):
                txt = self._vault[i].get(field, "")
                cb = QApplication.clipboard()
                cb.setText(txt)
                self.status.showMessage(T("pw_copied"), 4000)
                QTimer.singleShot(30000, lambda t=txt:
                                  cb.setText("") if cb.text() == t else None)

        row = QHBoxLayout()
        for label, fn in ((T("pw_add"), add), (T("pw_del"), remove),
                          (T("pw_copyu"), lambda: copy("user")),
                          (T("pw_copyp"), lambda: copy("pass")),
                          (T("close"), dlg.accept)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        dlg.exec()

    def closeEvent(self, e):
        try:
            TM.shutdown()
        except Exception:
            pass
        e.accept()


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    w = Browser()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
