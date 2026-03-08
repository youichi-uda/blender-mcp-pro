import bpy
import socket
import json
import threading
import queue
import struct
import time
import traceback
import uuid

from .handlers import dispatch_command

PORT = 9877
HEADER_SIZE = 4

_server_thread = None
_server_socket = None
_stop_event = threading.Event()
_command_queue = queue.Queue()
_pending_results = {}  # {request_id: {"event": Event, "result": None}}
_results_lock = threading.Lock()
_last_error = ""
_running = False
_modal_alive_time = 0.0  # last time a timer tick ran (kept name for compat)


def get_server_state():
    return {
        "running": _running,
        "port": PORT,
        "last_error": _last_error,
    }


def recv_all(conn):
    header = b""
    while len(header) < HEADER_SIZE:
        chunk = conn.recv(HEADER_SIZE - len(header))
        if not chunk:
            raise ConnectionError("Connection closed while reading header")
        header += chunk

    msg_len = struct.unpack(">I", header)[0]
    data = b""
    while len(data) < msg_len:
        chunk = conn.recv(min(65536, msg_len - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed while reading body")
        data += chunk

    return data.decode("utf-8")


def send_all(conn, data):
    encoded = data.encode("utf-8")
    header = struct.pack(">I", len(encoded))
    conn.sendall(header + encoded)


import os as _os
_LOG_PATH = _os.path.join(_os.path.expanduser("~"), "bmpro_debug.log")


def _log(msg):
    """Debug log to file and Blender console."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(f"[BM Pro] {msg}")
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


_TIMER_INTERVAL = 0.05  # 50ms — same responsiveness as old modal
_WATCHDOG_INTERVAL = 2.0  # check every 2s that the processor is alive


def _process_queue():
    """Timer callback: pull one command from the queue and execute it."""
    global _last_error, _modal_alive_time

    if not _running:
        _log("Process-queue timer stopping (_running=False)")
        return None  # unregister

    _modal_alive_time = time.time()

    try:
        cmd = _command_queue.get_nowait()
    except queue.Empty:
        return _TIMER_INTERVAL

    request_id = cmd.pop("_request_id", None)
    cmd_name = cmd.get("command", "?")
    _log(f"Processing: {cmd_name} (id={request_id[:8] if request_id else '?'})")

    # Skip commands whose connection already timed out
    if request_id:
        with _results_lock:
            if request_id not in _pending_results:
                _log(f"Skipping stale command: {cmd_name}")
                return _TIMER_INTERVAL

    try:
        result = dispatch_command(cmd)
        response = {"status": "ok", "result": result}
        _log(f"Command OK: {cmd_name}")
        _last_error = ""
    except Exception as e:
        hint = next(
            (h for t, h in ERROR_HINTS.items() if isinstance(e, t)),
            type(e).__name__
        )
        error_msg = str(e)
        _last_error = error_msg
        response = {
            "status": "error",
            "message": error_msg,
            "hint": hint,
            "traceback": traceback.format_exc(),
        }

    if request_id:
        with _results_lock:
            pending = _pending_results.get(request_id)
            if pending:
                pending["result"] = response
                pending["event"].set()

    return _TIMER_INTERVAL


def _watchdog():
    """Periodically ensure _process_queue timer is registered."""
    if not _running:
        return None  # unregister

    if not bpy.app.timers.is_registered(_process_queue):
        _log("Watchdog: _process_queue died — restarting")
        bpy.app.timers.register(
            _process_queue, first_interval=0.0, persistent=True,
        )

    return _WATCHDOG_INTERVAL


def _ensure_timer_alive():
    """Called from connection threads to kick-start timers if needed."""
    global _modal_alive_time
    if not _running:
        return
    elapsed = time.time() - _modal_alive_time
    if elapsed > _WATCHDOG_INTERVAL and _modal_alive_time > 0:
        _log(f"Timer appears dead (no tick for {elapsed:.1f}s), scheduling restart")

        def _restart():
            if not bpy.app.timers.is_registered(_process_queue):
                bpy.app.timers.register(
                    _process_queue, first_interval=0.0, persistent=True,
                )
            if not bpy.app.timers.is_registered(_watchdog):
                bpy.app.timers.register(
                    _watchdog, first_interval=0.0, persistent=True,
                )
            return None

        bpy.app.timers.register(_restart, first_interval=0.0)
        _modal_alive_time = time.time()


def _handle_connection(conn):
    """Handle a single client connection in its own thread."""
    request_id = None
    try:
        conn.settimeout(30.0)
        raw = recv_all(conn)
        cmd = json.loads(raw)
        _log(f"Received: {cmd.get('command')} params={cmd.get('params', {})}")

        request_id = uuid.uuid4().hex
        cmd["_request_id"] = request_id

        event = threading.Event()
        with _results_lock:
            # Clean up stale pending results (older than 60s)
            stale = [
                rid for rid, info in _pending_results.items()
                if info.get("_timestamp", 0) < time.time() - 60
            ]
            for rid in stale:
                _pending_results.pop(rid, None)

            _pending_results[request_id] = {
                "event": event,
                "result": None,
                "_timestamp": time.time(),
            }

        # Kick-start timers if they appear dead
        _ensure_timer_alive()

        _command_queue.put(cmd)
        _log(f"Enqueued {cmd.get('command')} (id={request_id[:8]}), queue size={_command_queue.qsize()}")

        if event.wait(timeout=120.0):
            with _results_lock:
                result = _pending_results.pop(request_id)["result"]
            send_all(conn, json.dumps(result, default=str))
        else:
            with _results_lock:
                _pending_results.pop(request_id, None)
            send_all(conn, json.dumps({
                "status": "error",
                "message": "Timeout waiting for Blender response.",
                "hint": "Blender may be busy or the operation is blocking.",
            }))
    except Exception as e:
        # Clean up pending result on error
        if request_id:
            with _results_lock:
                _pending_results.pop(request_id, None)
        try:
            send_all(conn, json.dumps({
                "status": "error",
                "message": str(e),
                "hint": "Connection or protocol error.",
            }))
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _socket_thread():
    global _server_socket
    try:
        _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_socket.settimeout(1.0)
        _server_socket.bind(("localhost", PORT))
        _server_socket.listen(5)

        while not _stop_event.is_set():
            try:
                conn, addr = _server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            t = threading.Thread(target=_handle_connection, args=(conn,), daemon=True)
            t.start()

    except Exception as e:
        global _last_error
        _last_error = str(e)
    finally:
        if _server_socket:
            try:
                _server_socket.close()
            except Exception:
                pass
            _server_socket = None


ERROR_HINTS = {
    AttributeError: "Object or property may not exist. Use get_scene_info() first.",
    TypeError: "Parameter type mismatch. Check the tool description.",
    KeyError: "Named item not found. Use list tools to see available options.",
    RuntimeError: "Blender operation failed. Object may be in wrong mode.",
    ValueError: "Invalid value provided. Check parameter ranges and types.",
    PermissionError: "Operation not permitted in current context.",
}


class BMPRO_OT_ModalServer(bpy.types.Operator):
    """Kept for backward-compat registration; actual work is done by timers."""
    bl_idname = "bmpro.modal_server"
    bl_label = "BM Pro Modal Server"

    def execute(self, context):
        # Legacy entry-point: just make sure timers are running
        if not bpy.app.timers.is_registered(_process_queue):
            bpy.app.timers.register(
                _process_queue, first_interval=0.0, persistent=True,
            )
        if not bpy.app.timers.is_registered(_watchdog):
            bpy.app.timers.register(
                _watchdog, first_interval=_WATCHDOG_INTERVAL, persistent=True,
            )
        return {"FINISHED"}


def start(context):
    global _running, _server_thread, _last_error, _modal_alive_time
    if _running:
        return
    # Clear previous log
    try:
        open(_LOG_PATH, "w").close()
    except Exception:
        pass
    _log("Server starting")

    _stop_event.clear()
    _running = True
    _last_error = ""
    _modal_alive_time = time.time()

    # Clear queues and pending results
    while not _command_queue.empty():
        try:
            _command_queue.get_nowait()
        except queue.Empty:
            break
    with _results_lock:
        _pending_results.clear()

    _server_thread = threading.Thread(target=_socket_thread, daemon=True)
    _server_thread.start()

    # Register timer-based command processor + watchdog (persistent survives undo/file-load)
    bpy.app.timers.register(_process_queue, first_interval=0.0, persistent=True)
    bpy.app.timers.register(_watchdog, first_interval=_WATCHDOG_INTERVAL, persistent=True)
    _log("Timer-based processor and watchdog registered")


def stop():
    global _running, _server_thread, _server_socket
    _running = False  # timers will unregister themselves on next tick
    _stop_event.set()

    # Eagerly unregister timers
    for fn in (_process_queue, _watchdog):
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except Exception:
            pass

    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None

    if _server_thread:
        _server_thread.join(timeout=3.0)
        _server_thread = None
