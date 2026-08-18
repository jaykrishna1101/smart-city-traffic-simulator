#!/usr/bin/env python3
"""
SmartFlow SUMO-GUI Window VNC Server
=====================================
Streams ONLY the sumo-gui.exe window (by HWND) as a valid RFB/VNC session.
Replaces TightVNC in the streaming path — TightVNC was streaming the
entire Windows desktop; this server captures only the SUMO window bounding box.

Architecture:
    sumo-gui.exe  <── traci (unchanged)
         |
         +── mss.grab(hwnd bounding box)  -> SUMO-GUI pixels ONLY
         +── win32api input injection     <- noVNC pointer/key events
         |
    [This Server -- port 5901]
         |
    websockify (port 6080)
         |
    Browser noVNC

Usage:
    python sumo_window_vnc.py [--port 5901] [--fps 15] [--no-topmost]

Dependencies:
    pip install mss pywin32 Pillow
"""

import argparse
import socket
import struct
import threading
import time
import sys
import os

try:
    import mss
    import win32gui
    import win32con
    import win32api
    import win32process
    from PIL import Image
except ImportError as e:
    print(f"\n[ERROR] Missing dependency: {e}")
    print("Install with: pip install mss pywin32 Pillow\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# RFB / VNC Protocol Constants
# ---------------------------------------------------------------------------
RFB_VERSION         = b"RFB 003.008\n"
SEC_NONE            = 1
MSG_FRAMEBUFFER_REQ = 3
MSG_KEY_EVENT       = 4
MSG_POINTER_EVENT   = 5
MSG_CLIENT_CUT_TEXT = 6
ENCODING_RAW        = 0


# ---------------------------------------------------------------------------
# Window Discovery
# ---------------------------------------------------------------------------

def find_sumo_hwnd():
    """
    Find the main window handle for sumo-gui.exe.
    Returns HWND (int) or None if not found.
    """
    results = []

    def enum_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        # Only top-level windows — skip child/sub-windows like toolbars
        if win32gui.GetParent(hwnd) != 0:
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False, pid
            )
            exe = win32process.GetModuleFileNameEx(handle, 0)
            win32api.CloseHandle(handle)
            if "sumo-gui" in exe.lower():
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                # Skip tiny sub-windows (toolbars, status bars, etc.)
                if w > 300 and h > 200:
                    results.append((hwnd, w * h))  # prefer largest window
        except Exception:
            pass

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        pass

    if not results:
        # Fallback: title search — also top-level only
        def title_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            if win32gui.GetParent(hwnd) != 0:
                return
            title = win32gui.GetWindowText(hwnd)
            if "sumo" in title.lower():
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 300 and h > 200:
                    results.append((hwnd, w * h))
        try:
            win32gui.EnumWindows(title_callback, None)
        except Exception:
            pass

    if results:
        results.sort(key=lambda x: -x[1])
        return results[0][0]
    return None


def get_window_rect(hwnd):
    """Returns (left, top, width, height) or None."""
    try:
        rect = win32gui.GetWindowRect(hwnd)
        left   = rect[0]
        top    = rect[1]
        width  = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width > 0 and height > 0:
            return left, top, width, height
    except Exception:
        pass
    return None


def set_window_topmost(hwnd):
    """Keep SUMO-GUI always-on-top so mss always captures SUMO, not a covering window."""
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )
    except Exception as e:
        print(f"[VNC] Warning: could not set HWND_TOPMOST: {e}")


# ---------------------------------------------------------------------------
# Screen Capture
# ---------------------------------------------------------------------------

class FrameGrabber:
    """
    Grabs the SUMO-GUI window region at up to `fps` frames per second.
    Thread-safe: get_frame() can be called from any thread.
    """

    def __init__(self, fps=15, topmost=True):
        self.fps      = fps
        self.topmost  = topmost
        self.hwnd     = None
        self.rect     = None
        self._lock    = threading.Lock()
        self._frame   = None      # latest raw RGB bytes
        self._width   = 0
        self._height  = 0
        self._running = False
        self._thread  = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _discover_window(self):
        """Block until sumo-gui.exe window is found. Returns (hwnd, rect)."""
        while self._running:
            hwnd = find_sumo_hwnd()
            if hwnd:
                rect = get_window_rect(hwnd)
                if rect:
                    print(f"[VNC] Found sumo-gui window: HWND={hwnd}, rect={rect}")
                    if self.topmost:
                        set_window_topmost(hwnd)
                    return hwnd, rect
            print("[VNC] Waiting for sumo-gui.exe window...")
            time.sleep(2.0)
        return None, None

    def _capture_loop(self):
        interval = 1.0 / self.fps
        hwnd, rect = self._discover_window()
        if not hwnd:
            return

        self.hwnd = hwnd
        self.rect = rect

        with mss.mss() as sct:
            while self._running:
                t0 = time.monotonic()

                # Re-check window position (user may have moved it)
                new_rect = get_window_rect(self.hwnd)
                if new_rect is None:
                    print("[VNC] sumo-gui window lost, re-searching...")
                    self.hwnd, self.rect = self._discover_window()
                    if not self.hwnd:
                        break
                    if self.topmost:
                        set_window_topmost(self.hwnd)
                    new_rect = self.rect

                if new_rect != self.rect:
                    self.rect = new_rect

                left, top, w, h = self.rect
                monitor = {"left": left, "top": top, "width": w, "height": h}
                try:
                    shot = sct.grab(monitor)
                    img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    raw  = img.tobytes()
                    with self._lock:
                        self._frame  = raw
                        self._width  = w
                        self._height = h
                except Exception as e:
                    print(f"[VNC] Capture error: {e}")

                elapsed = time.monotonic() - t0
                time.sleep(max(0.0, interval - elapsed))

    def get_frame(self):
        """Returns (raw_rgb_bytes, width, height). Thread-safe."""
        with self._lock:
            return self._frame, self._width, self._height


# ---------------------------------------------------------------------------
# Input Injection
# ---------------------------------------------------------------------------

def send_pointer_event(hwnd, window_rect, x, y, button_mask):
    """
    Inject pointer event into the SUMO window.
    x, y are absolute pixel positions within the streamed frame.
    """
    try:
        left, top, w, h = window_rect
        screen_x = left + min(x, w - 1)
        screen_y = top  + min(y, h - 1)
        win32api.SetCursorPos((screen_x, screen_y))

        client_x = screen_x - left
        client_y = screen_y - top
        lparam   = win32api.MAKELONG(client_x, client_y)

        if button_mask & 0x01:
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        else:
            win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

        if button_mask & 0x04:
            win32api.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)

        if button_mask & 0x08:   # scroll up
            win32api.PostMessage(hwnd, win32con.WM_MOUSEWHEEL,
                                 win32api.MAKELONG(0, 120), lparam)
        if button_mask & 0x10:   # scroll down
            win32api.PostMessage(hwnd, win32con.WM_MOUSEWHEEL,
                                 win32api.MAKELONG(0, -120), lparam)

        win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    except Exception:
        pass


KEYSYM_TO_VK = {
    0xff08: 0x08,   # Backspace
    0xff09: 0x09,   # Tab
    0xff0d: 0x0D,   # Enter
    0xff1b: 0x1B,   # Escape
    0xff50: 0x24,   # Home
    0xff51: 0x25,   # Left
    0xff52: 0x26,   # Up
    0xff53: 0x27,   # Right
    0xff54: 0x28,   # Down
    0xff55: 0x21,   # Page Up
    0xff56: 0x22,   # Page Down
    0xff57: 0x23,   # End
    0xffff: 0x2E,   # Delete
    0xffe1: 0xA0,   # LShift
    0xffe2: 0xA1,   # RShift
    0xffe3: 0xA2,   # LCtrl
    0xffe4: 0xA3,   # RCtrl
    0xffe9: 0xA4,   # LAlt
    0xffea: 0xA5,   # RAlt
    0xffbe: 0x70,   # F1
    0xffbf: 0x71,   # F2
    0xffc0: 0x72,   # F3
    0xffc1: 0x73,   # F4
    0xffc2: 0x74,   # F5
    0xffc3: 0x75,   # F6
    0xffc4: 0x76,   # F7
    0xffc5: 0x77,   # F8
    0xffc6: 0x78,   # F9
    0xffc7: 0x79,   # F10
    0xffc8: 0x7A,   # F11
    0xffc9: 0x7B,   # F12
}


def send_key_event(hwnd, key, down):
    try:
        vk = KEYSYM_TO_VK.get(key)
        if vk is None:
            if 0x20 <= key <= 0x7e:
                vk = win32api.VkKeyScan(chr(key)) & 0xFF
            else:
                return
        flag = 0 if down else win32con.KEYEVENTF_KEYUP
        win32api.keybd_event(vk, 0, flag, 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# RFB Client Handler
# ---------------------------------------------------------------------------

class RFBClientHandler(threading.Thread):
    """
    Handles one VNC/RFB client connection (VNC 3.8, no-auth, RAW encoding).
    """

    def __init__(self, conn, addr, grabber):
        super().__init__(daemon=True)
        self.conn    = conn
        self.addr    = addr
        self.grabber = grabber

    def run(self):
        print(f"[VNC] Client connected: {self.addr}")
        try:
            if self._handshake():
                self._serve()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except Exception as e:
            print(f"[VNC] Client {self.addr} error: {e}")
        finally:
            try:
                self.conn.close()
            except Exception:
                pass
            print(f"[VNC] Client disconnected: {self.addr}")

    # -- Handshake ------------------------------------------------------------

    def _handshake(self):
        self.conn.sendall(RFB_VERSION)
        if not self.conn.recv(12):
            return False

        self.conn.sendall(struct.pack("!BB", 1, SEC_NONE))
        sec = self.conn.recv(1)
        if not sec or sec[0] != SEC_NONE:
            return False

        self.conn.sendall(struct.pack("!I", 0))  # SecurityResult OK
        self.conn.recv(1)                         # ClientInit

        # Wait for first frame to know dimensions
        print("[VNC] Waiting for first SUMO-GUI frame...")
        for _ in range(60):
            _, w, h = self.grabber.get_frame()
            if w > 0 and h > 0:
                break
            time.sleep(0.5)
        else:
            print("[VNC] Timed out waiting for SUMO-GUI frame.")
            return False

        print(f"[VNC] Sending ServerInit: {w}x{h}")
        name = b"SUMO-GUI"
        fmt  = struct.pack("!BBBBHHHBBBxxx",
            32, 24, 0, 1,   # bpp, depth, big-endian, true-colour
            255, 255, 255,   # rgb-max
            16, 8, 0,        # rgb-shift (R at byte2, G at byte1, B at byte0)
        )
        self.conn.sendall(
            struct.pack("!HH", w, h) + fmt +
            struct.pack("!I", len(name)) + name
        )
        return True

    # -- Serve loop -----------------------------------------------------------

    def _serve(self):
        while True:
            data = self._recv_exact(1)
            if not data:
                break
            msg = data[0]

            if msg == 0:  # SetPixelFormat
                # Client specifies its preferred pixel format — read and ignore.
                # Format: 3 bytes padding + 16 bytes pixel format = 19 bytes after msg type.
                self._recv_exact(19)

            elif msg == 2:  # SetEncodings
                # Client sends list of supported encodings — read and ignore.
                # Format: 1 byte padding + 2 bytes count, then count * 4 bytes.
                hdr = self._recv_exact(3)
                if hdr:
                    count = struct.unpack("!xH", hdr)[0]
                    self._recv_exact(count * 4)

            elif msg == MSG_FRAMEBUFFER_REQ:  # 3
                self._recv_exact(9)   # incremental + x,y,w,h
                frame, w, h = self.grabber.get_frame()
                if frame and w > 0 and h > 0:
                    self._send_frame(frame, w, h)

            elif msg == MSG_POINTER_EVENT:   # 5
                raw = self._recv_exact(5)
                if raw:
                    button_mask, x, y = struct.unpack("!BHH", raw)
                    hwnd = self.grabber.hwnd
                    rect = self.grabber.rect
                    if hwnd and rect:
                        send_pointer_event(hwnd, rect, x, y, button_mask)

            elif msg == MSG_KEY_EVENT:       # 4
                raw = self._recv_exact(7)
                if raw:
                    down = raw[0]
                    key  = struct.unpack("!I", raw[3:7])[0]
                    hwnd = self.grabber.hwnd
                    if hwnd:
                        send_key_event(hwnd, key, bool(down))

            elif msg == MSG_CLIENT_CUT_TEXT:  # 6
                self._recv_exact(3)
                ld = self._recv_exact(4)
                if ld:
                    self._recv_exact(struct.unpack("!I", ld)[0])

            else:
                print(f"[VNC] Unhandled message type {msg} — ignoring (safe)")
                # Don't close: just skip. noVNC may send extension messages.

    def _send_frame(self, raw_rgb, width, height):
        """
        Send FramebufferUpdate with one full-screen RAW rectangle.
        Convert RGB -> BGRX (matches declared ServerInit pixel format: shifts 16,8,0).
        """
        try:
            img    = Image.frombytes("RGB", (width, height), raw_rgb)
            pixels = img.tobytes()  # RGB, 3 bytes per pixel
            n      = width * height
            buf    = bytearray(n * 4)
            for i in range(n):
                s       = i * 3
                d       = i * 4
                buf[d]  = pixels[s + 2]   # B  (blue-shift=0)
                buf[d+1]= pixels[s + 1]   # G  (green-shift=8)
                buf[d+2]= pixels[s]       # R  (red-shift=16)
                buf[d+3]= 0               # padding

            header = struct.pack("!BBHHHHHI",
                0, 0,          # type=FramebufferUpdate, padding
                1,             # 1 rectangle
                0, 0,          # x, y
                width, height,
                ENCODING_RAW
            )
            self.conn.sendall(header + bytes(buf))
        except Exception as e:
            print(f"[VNC] Frame send error: {e}")
            raise

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf


# ---------------------------------------------------------------------------
# Main Server
# ---------------------------------------------------------------------------

class SumoWindowVNCServer:
    def __init__(self, host="127.0.0.1", port=5901, fps=15, topmost=True):
        self.host    = host
        self.port    = port
        self.grabber = FrameGrabber(fps=fps, topmost=topmost)

    def run(self):
        print("=" * 60)
        print("  SmartFlow SUMO-GUI Window VNC Server")
        print(f"  Listen : {self.host}:{self.port}")
        print(f"  Mode   : HWND window capture (sumo-gui.exe only)")
        print("=" * 60)
        print()
        print("[VNC] Starting frame grabber...")
        self.grabber.start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.port))
            srv.listen(5)
            print(f"[VNC] RFB listening on {self.host}:{self.port}")
            print(f"[VNC] Run websockify: python -m websockify 6080 {self.host}:{self.port}")
            print("[VNC] Waiting for noVNC client...\n")
            try:
                while True:
                    conn, addr = srv.accept()
                    RFBClientHandler(conn, addr, self.grabber).start()
            except KeyboardInterrupt:
                print("\n[VNC] Stopped.")
            finally:
                self.grabber.stop()


def main():
    parser = argparse.ArgumentParser(
        description="SmartFlow SUMO-GUI Window VNC Server"
    )
    parser.add_argument("--host",        default="127.0.0.1")
    parser.add_argument("--port",        type=int, default=5901)
    parser.add_argument("--fps",         type=int, default=15)
    parser.add_argument("--no-topmost",  action="store_true",
                        help="Disable HWND_TOPMOST on SUMO-GUI window")
    parser.add_argument("--test",        action="store_true",
                        help="Test window discovery and capture, then exit")
    args = parser.parse_args()

    if args.test:
        print("[TEST] Searching for sumo-gui.exe window...")
        hwnd = find_sumo_hwnd()
        if hwnd:
            rect = get_window_rect(hwnd)
            print(f"[TEST] Found: HWND={hwnd}, rect={rect}")
            left, top, w, h = rect
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": w, "height": h}
                shot = sct.grab(monitor)
                print(f"[TEST] Captured {shot.width}x{shot.height} pixels. Success.")
        else:
            print("[TEST] sumo-gui.exe window not found. Is SUMO running?")
        return

    SumoWindowVNCServer(
        host    = args.host,
        port    = args.port,
        fps     = args.fps,
        topmost = not args.no_topmost,
    ).run()


if __name__ == "__main__":
    main()
