import bpy
import socket
import json
import threading
import queue
import struct
import traceback

from .handlers import dispatch_command

PORT = 9877
HEADER_SIZE = 4

_server_thread = None
_server_socket = None
_stop_event = threading.Event()
_command_queue = queue.Queue()
_result_queue = queue.Queue()
_last_error = ""
_running = False


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


def _socket_thread():
    global _server_socket
    try:
        _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _server_socket.settimeout(1.0)
        _server_socket.bind(("localhost", PORT))
        _server_socket.listen(1)

        while not _stop_event.is_set():
            try:
                conn, addr = _server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                conn.settimeout(300.0)
                raw = recv_all(conn)
                cmd = json.loads(raw)
                _command_queue.put(cmd)
                result = _result_queue.get(timeout=300.0)
                send_all(conn, json.dumps(result, default=str))
            except Exception as e:
                try:
                    error_resp = json.dumps({
                        "status": "error",
                        "message": str(e),
                        "hint": "Connection or protocol error."
                    })
                    send_all(conn, error_resp)
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

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
    bl_idname = "bmpro.modal_server"
    bl_label = "BM Pro Modal Server"

    _timer = None

    def modal(self, context, event):
        global _last_error

        if not _running:
            self.cancel(context)
            return {"CANCELLED"}

        if event.type == "TIMER":
            try:
                cmd = _command_queue.get_nowait()
            except queue.Empty:
                return {"PASS_THROUGH"}

            try:
                result = dispatch_command(cmd)
                _result_queue.put({"status": "ok", "result": result})
                _last_error = ""
            except Exception as e:
                hint = next(
                    (h for t, h in ERROR_HINTS.items() if isinstance(e, t)),
                    type(e).__name__
                )
                error_msg = str(e)
                _last_error = error_msg
                _result_queue.put({
                    "status": "error",
                    "message": error_msg,
                    "hint": hint,
                    "traceback": traceback.format_exc(),
                })

        return {"PASS_THROUGH"}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None


def start(context):
    global _running, _server_thread, _last_error
    if _running:
        return

    _stop_event.clear()
    _running = True
    _last_error = ""

    # Clear queues
    while not _command_queue.empty():
        try:
            _command_queue.get_nowait()
        except queue.Empty:
            break
    while not _result_queue.empty():
        try:
            _result_queue.get_nowait()
        except queue.Empty:
            break

    _server_thread = threading.Thread(target=_socket_thread, daemon=True)
    _server_thread.start()

    bpy.ops.bmpro.modal_server()


def stop():
    global _running, _server_thread, _server_socket
    _running = False
    _stop_event.set()

    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None

    if _server_thread:
        _server_thread.join(timeout=3.0)
        _server_thread = None
