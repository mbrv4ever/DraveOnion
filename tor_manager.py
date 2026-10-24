# -*- coding: utf-8 -*-
"""DraveOnion - Tor-beheer.

- detect(): vindt een al draaiende Tor (Tor Browser op 9150, systeem op 9050).
- ensure_tor(cb): detecteert; anders haalt de Tor Expert Bundle automatisch op
  naar de eigen cache-map, start tor.exe en wacht op verbinding. Geen losse
  bestanden voor de gebruiker.
- new_identity(): vraagt een nieuw Tor-circuit (alleen voor onze eigen tor).

Puur Python (geen Qt), zodat het los te testen is.
"""
import os
import re
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request

SOCKS_PORT = 9052          # eigen Tor (zelf gestart)
CTRL_PORT = 9053
ARCHIVE = "https://archive.torproject.org/tor-package-archive/torbrowser/"

_proc = None               # draaiend tor-proces (indien zelf gestart)
_data_dir = None


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def cache_dir():
    d = os.path.join(app_dir(), "cache")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _port_open(port, host="127.0.0.1", timeout=1.0):
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True
    except OSError:
        return False


def detect():
    """Geeft een SOCKS-poort van een draaiende Tor, of None."""
    for p in (9150, 9050, SOCKS_PORT):
        if _port_open(p):
            return p
    return None


# ---------------------------------------------------------------------------
def _latest_version():
    html = urllib.request.urlopen(ARCHIVE, timeout=25).read().decode(
        "utf-8", "replace")
    vers = set(re.findall(r'href="(\d+\.\d+(?:\.\d+)?)/"', html))

    def key(v):
        return tuple(int(x) for x in v.split("."))

    return sorted(vers, key=key)[-1] if vers else None


def _find_tor_exe(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower() == "tor.exe":
                return os.path.join(root, f)
    return None


def _download_tor(cb):
    outdir = os.path.join(cache_dir(), "tor")
    exe = _find_tor_exe(outdir)
    if exe:
        return exe
    cb("Tor-versie opzoeken...")
    ver = _latest_version()
    if not ver:
        raise RuntimeError("geen versie gevonden")
    url = (ARCHIVE + "%s/tor-expert-bundle-windows-x86_64-%s.tar.gz"
           % (ver, ver))
    cb("Tor downloaden (%s)..." % ver)
    dst = os.path.join(cache_dir(), "tor.tar.gz")
    urllib.request.urlretrieve(url, dst)
    cb("Tor uitpakken...")
    os.makedirs(outdir, exist_ok=True)
    with tarfile.open(dst) as t:
        t.extractall(outdir)
    try:
        os.remove(dst)
    except Exception:
        pass
    exe = _find_tor_exe(outdir)
    if not exe:
        raise RuntimeError("tor.exe niet gevonden na uitpakken")
    return exe


def _write_torrc(data_dir):
    rc = os.path.join(cache_dir(), "torrc")
    with open(rc, "w", encoding="utf-8") as f:
        f.write("SocksPort %d\n" % SOCKS_PORT)
        f.write("ControlPort %d\n" % CTRL_PORT)
        f.write("CookieAuthentication 1\n")
        f.write("DataDirectory %s\n" % data_dir.replace("\\", "/"))
    return rc


def launch_tor(cb):
    """Start onze eigen tor en wacht op verbinding. Geeft SOCKS-poort of None."""
    global _proc, _data_dir
    try:
        exe = _download_tor(cb)
    except Exception as e:
        cb("Tor ophalen mislukt: %s" % e)
        return None
    _data_dir = os.path.join(cache_dir(), "tordata")
    os.makedirs(_data_dir, exist_ok=True)
    rc = _write_torrc(_data_dir)
    cb("Tor starten...")
    flags = 0
    if os.name == "nt":
        flags = 0x08000000      # CREATE_NO_WINDOW
    try:
        _proc = subprocess.Popen([exe, "-f", rc], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 creationflags=flags)
    except Exception as e:
        cb("Tor starten mislukt: %s" % e)
        return None
    cb("Verbinden met het Tor-netwerk...")
    t0 = time.time()
    while time.time() - t0 < 90:
        line = _proc.stdout.readline()
        if not line:
            if _proc.poll() is not None:
                break
            continue
        if "Bootstrapped 100%" in line:
            cb("Verbonden met Tor.")
            return SOCKS_PORT
        m = re.search(r"Bootstrapped (\d+)%", line)
        if m:
            cb("Tor verbinden... %s%%" % m.group(1))
    cb("Tor kon niet verbinden (time-out).")
    return None


def ensure_tor(cb):
    """Detecteer of start Tor. Geeft (socks_port, managed_bool) of (None, False)."""
    p = detect()
    if p:
        cb("Bestaande Tor gevonden op poort %d." % p)
        return p, False
    cb("Geen Tor gevonden - automatisch ophalen...")
    p = launch_tor(cb)
    return (p, True) if p else (None, False)


def new_identity():
    """Vraag een nieuw circuit (alleen voor onze eigen tor met cookie-auth)."""
    if _data_dir is None:
        return False
    cookie = os.path.join(_data_dir, "control_auth_cookie")
    try:
        with open(cookie, "rb") as f:
            data = f.read().hex()
        s = socket.create_connection(("127.0.0.1", CTRL_PORT), 5)
        s.sendall(("AUTHENTICATE %s\r\n" % data).encode())
        if b"250" not in s.recv(256):
            s.close()
            return False
        s.sendall(b"SIGNAL NEWNYM\r\n")
        ok = b"250" in s.recv(256)
        s.close()
        return ok
    except Exception:
        return False


def shutdown():
    global _proc
    if _proc and _proc.poll() is None:
        try:
            _proc.terminate()
        except Exception:
            pass
    _proc = None


if __name__ == "__main__":
    print("detect:", detect())
    print("versie-parse test:")
    html = 'href="13.0.1/" href="12.5.6/" href="13.5/" href="6.0.2/"'
    vers = set(re.findall(r'href="(\d+\.\d+(?:\.\d+)?)/"', html))
    print("  gevonden:", sorted(vers),
          "-> nieuwste:", sorted(vers, key=lambda v: tuple(
              int(x) for x in v.split(".")))[-1])
