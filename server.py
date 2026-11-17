from __future__ import annotations

import hmac
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from RAG.rag_engine import rag_answer
from pharmacity_chatbot.pharmacity_service import answer_product_question, search_products


ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "Web_emoji"
DATA_DIR = ROOT_DIR / "data"
CURRENT_ORDERS_XLSX = DATA_DIR / "current_orders.xlsx"
MEDICINE_ORDERS_JSON = DATA_DIR / "medicine_orders.json"
ROBOT_RUNTIME_JSON = DATA_DIR / "robot_runtime.json"
ARDUINO_SETTINGS_JSON = DATA_DIR / "arduino_settings.json"
MEDICINE_TEMPLATE_XLSX = DATA_DIR / "medicine_template.xlsx"
DOWNLOAD_TEMPLATE_SOURCE = Path.home() / "Downloads" / "File mẫu.xlsx"
DEFAULT_GEMINI_LIVE_MODEL = "gemini-3.1-flash-live-preview"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: https:; "
    "media-src 'self' blob:; "
    "connect-src 'self' wss://generativelanguage.googleapis.com"
)
REQUIRED_ORDER_COLUMNS = [
    "Vị trí khay",
    "Cửa",
    "ID bệnh nhân",
    "Họ và tên",
    "Giường",
    "Thông tin đơn thuốc",
    "Hướng dẫn uống thuốc",
]
POSITION_RE = re.compile(r"^K([12])_([1-8])$")
ARDUINO_BAUD_RATE = 9600
DEFAULT_ARDUINO_TIMEOUT_MS = 30000
ARDUINO_HOME_TIMEOUT_MS = 65000
SUPPLY_DOOR_NUMBER = 3
ARDUINO_BOOT_TIMEOUT_MS = 65000
ARDUINO_RECONNECT_INTERVAL_SECONDS = 3.0
ARDUINO_STATUS_INTERVAL_SECONDS = 5.0
DISPENSE_OPEN_SECONDS = 30
DISPENSE_COMMAND_TIMEOUT_MS = 35000
ACTIVE_DISPENSE_STATES = {"opening", "open", "closing", "interrupted"}
ORDER_STATES = {"pending_setup", "ready", "dispensing", "dispensed", "interrupted"}
_DATA_LOCK = threading.RLock()


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_PROCESS_MAIN_HOST = os.environ.get("ROBOT_APP_HOST") or os.environ.get("HOST")
_PROCESS_MAIN_PORT = os.environ.get("ROBOT_APP_PORT") or os.environ.get("PORT")
load_env_file(ROOT_DIR / ".env")


def main_server_address() -> tuple[str, int]:
    host = _PROCESS_MAIN_HOST or os.environ.get("ROBOT_APP_HOST") or os.environ.get("HOST") or "127.0.0.1"
    port_text = _PROCESS_MAIN_PORT or os.environ.get("ROBOT_APP_PORT") or os.environ.get("PORT") or "8000"
    return host, int(port_text)


class InvalidOrderDataError(ValueError):
    pass


class RobotWorkflowError(RuntimeError):
    def __init__(self, code: str, detail: str, status: HTTPStatus = HTTPStatus.CONFLICT):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, payload: dict) -> None:
    ensure_data_dir()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def default_orders_state() -> dict:
    return {
        "orders": [],
        "setup_done": {},
        "current_setup_slot": 1,
        "uploaded_file_name": "",
        "updated_at": None,
    }


def load_orders_state() -> dict:
    state = read_json_file(MEDICINE_ORDERS_JSON, default_orders_state())
    defaults = default_orders_state()
    defaults.update(state)
    orders = defaults.get("orders") if isinstance(defaults.get("orders"), list) else []
    setup_done = defaults.get("setup_done") if isinstance(defaults.get("setup_done"), dict) else {}
    for order in orders:
        if not isinstance(order, dict):
            raise InvalidOrderDataError("Danh sách đơn thuốc chứa phần tử không hợp lệ.")
        order["setup_done"] = bool(setup_done.get(order.get("position"), order.get("setup_done", False)))
        status = str(order.get("dispense_status") or "").strip().lower()
        if status not in ORDER_STATES:
            status = "ready" if order["setup_done"] else "pending_setup"
        order["dispense_status"] = status
        order["dispensed_at"] = order.get("dispensed_at") or None
        order["interrupted_at"] = order.get("interrupted_at") or None
    defaults["orders"] = orders
    defaults["setup_done"] = {
        order.get("position"): bool(order.get("setup_done"))
        for order in orders
        if isinstance(order, dict) and order.get("position")
    }
    try:
        slot = int(defaults.get("current_setup_slot") or 1)
    except (TypeError, ValueError):
        slot = 1
    defaults["current_setup_slot"] = slot if 1 <= slot <= 8 else 1
    return defaults


def save_orders_state(state: dict) -> None:
    orders = state.get("orders", [])
    setup_done = {
        order["position"]: bool(order.get("setup_done"))
        for order in orders
        if order.get("position")
    }
    payload = {
        "orders": orders,
        "setup_done": setup_done,
        "current_setup_slot": int(state.get("current_setup_slot") or 1),
        "uploaded_file_name": state.get("uploaded_file_name") or "",
        "updated_at": state.get("updated_at") or datetime.now().isoformat(timespec="seconds"),
    }
    with _DATA_LOCK:
        write_json_file(MEDICINE_ORDERS_JSON, payload)


def default_runtime_state() -> dict:
    return {"session": None, "updated_at": None}


def load_runtime_state() -> dict:
    with _DATA_LOCK:
        state = read_json_file(ROBOT_RUNTIME_JSON, default_runtime_state())
    return state if isinstance(state, dict) else default_runtime_state()


def save_runtime_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with _DATA_LOCK:
        write_json_file(ROBOT_RUNTIME_JSON, state)


def cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_excel_orders(path: Path) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("Thiếu openpyxl. Cài dependencies bằng: pip install -r requirements.txt") from exc

    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Không đọc được file Excel. Vui lòng upload file .xlsx đúng mẫu.") from exc

    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        raise ValueError("File Excel đang trống.")

    headers = [cell_to_text(value) for value in rows[0]]
    column_indexes = {header: index for index, header in enumerate(headers) if header}
    missing_columns = [column for column in REQUIRED_ORDER_COLUMNS if column not in column_indexes]
    if missing_columns:
        raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing_columns))

    errors: list[str] = []
    patient_ids: set[str] = set()
    positions: set[str] = set()
    orders: list[dict] = []

    for excel_row_number, row in enumerate(rows[1:], start=2):
        values = {
            column: cell_to_text(row[column_indexes[column]]) if column_indexes[column] < len(row) else ""
            for column in REQUIRED_ORDER_COLUMNS
        }
        if not any(values.values()):
            continue

        missing_values = [column for column, value in values.items() if not value]
        if missing_values:
            errors.append(f"Dòng {excel_row_number}: thiếu dữ liệu ở cột {', '.join(missing_values)}.")
            continue

        patient_id = values["ID bệnh nhân"]
        position = values["Vị trí khay"].upper()
        match = POSITION_RE.fullmatch(position)
        if not match:
            errors.append(f"Dòng {excel_row_number}: vị trí khay '{position}' không hợp lệ, chỉ dùng K1_1..K1_8 hoặc K2_1..K2_8.")
            continue
        if patient_id in patient_ids:
            errors.append(f"Dòng {excel_row_number}: ID bệnh nhân '{patient_id}' bị trùng.")
            continue
        if position in positions:
            errors.append(f"Dòng {excel_row_number}: vị trí khay '{position}' bị trùng.")
            continue

        try:
            door = int(values["Cửa"])
        except (TypeError, ValueError):
            door = 0
        if door not in {1, 2}:
            errors.append(f"Dòng {excel_row_number}: Cửa phải là 1 hoặc 2.")
            continue

        tray = int(match.group(1))
        slot = int(match.group(2))
        patient_ids.add(patient_id)
        positions.add(position)
        orders.append(
            {
                "id": patient_id,
                "patient_id": patient_id,
                "position": position,
                "tray": tray,
                "slot": slot,
                "door": door,
                "name": values["Họ và tên"],
                "bed": values["Giường"],
                "prescription": values["Thông tin đơn thuốc"],
                "instructions": values["Hướng dẫn uống thuốc"],
                "setup_done": False,
                "dispense_status": "pending_setup",
                "dispensed_at": None,
                "interrupted_at": None,
            }
        )

    if errors:
        raise ValueError("\n".join(errors))
    if not orders:
        raise ValueError("File Excel không có dòng đơn thuốc hợp lệ.")
    return sorted(orders, key=lambda item: (item["tray"], item["slot"], item["id"]))


def validate_order_data(order: object) -> dict:
    if not isinstance(order, dict):
        raise InvalidOrderDataError("Đơn thuốc không phải là một object hợp lệ.")

    patient_id = str(order.get("id") or order.get("patient_id") or "").strip()
    alternate_patient_id = str(order.get("patient_id") or order.get("id") or "").strip()
    if not patient_id or not alternate_patient_id or patient_id != alternate_patient_id:
        raise InvalidOrderDataError("Đơn thuốc thiếu ID bệnh nhân hợp lệ.")

    required_text = {
        "position": "vị trí khay",
        "name": "họ tên",
        "bed": "giường",
        "prescription": "thông tin đơn thuốc",
        "instructions": "hướng dẫn uống thuốc",
    }
    normalized_text: dict[str, str] = {}
    for key, label in required_text.items():
        value = str(order.get(key) or "").strip()
        if not value:
            raise InvalidOrderDataError(f"Đơn thuốc thiếu {label}.")
        normalized_text[key] = value

    position = normalized_text["position"].upper()
    match = POSITION_RE.fullmatch(position)
    if not match:
        raise InvalidOrderDataError("Vị trí khay phải có dạng K1_1..K1_8 hoặc K2_1..K2_8.")

    try:
        tray = int(order.get("tray"))
        slot = int(order.get("slot"))
        door = int(order.get("door"))
    except (TypeError, ValueError) as exc:
        raise InvalidOrderDataError("Đơn thuốc thiếu tray, slot hoặc door hợp lệ.") from exc

    expected_tray = int(match.group(1))
    expected_slot = int(match.group(2))
    if tray != expected_tray or slot != expected_slot or door not in {1, 2}:
        raise InvalidOrderDataError("Tray/slot không khớp vị trí hoặc cửa không phải 1/2.")

    dispense_status = str(order.get("dispense_status") or "").strip().lower()
    if dispense_status not in ORDER_STATES:
        dispense_status = "ready" if bool(order.get("setup_done")) else "pending_setup"

    return {
        "id": patient_id,
        "patient_id": patient_id,
        "position": position,
        "tray": tray,
        "slot": slot,
        "door": door,
        "name": normalized_text["name"],
        "bed": normalized_text["bed"],
        "prescription": normalized_text["prescription"],
        "instructions": normalized_text["instructions"],
        "setup_done": bool(order.get("setup_done")),
        "dispense_status": dispense_status,
        "dispensed_at": order.get("dispensed_at") or None,
        "interrupted_at": order.get("interrupted_at") or None,
    }


def public_order(order: dict) -> dict:
    return validate_order_data(order)


def find_order_by_patient_id(patient_id: str) -> dict | None:
    lookup = str(patient_id or "").strip()
    if not lookup:
        return None
    for order in load_orders_state().get("orders", []):
        if str(order.get("id") or order.get("patient_id") or "").strip() == lookup:
            return order
    return None


def create_template_workbook(path: Path) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("Thiếu openpyxl. Cài dependencies bằng: pip install -r requirements.txt") from exc
    ensure_data_dir()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(REQUIRED_ORDER_COLUMNS)
    sheet.append(
        [
            "K1_1",
            2,
            "066205000832",
            "Nguyễn Văn An",
            "A101-01",
            "Paracetamol 500mg: 1 viên; Vitamin C 500mg: 1 viên",
            "Uống sau ăn sáng và tối.",
        ]
    )
    sheet.append(
        [
            "K2_1",
            1,
            "032305000321",
            "Trần Thị Bình",
            "A101-02",
            "Omeprazole 20mg: 1 viên",
            "Uống trước ăn sáng 30 phút.",
        ]
    )
    widths = [16, 10, 20, 24, 14, 48, 48]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + index)].width = width
    workbook.save(path)


def ensure_template_file() -> Path:
    # Luon tao tu schema hien tai de khong phat lai mau cu thieu cot Cua.
    create_template_workbook(MEDICINE_TEMPLATE_XLSX)
    return MEDICINE_TEMPLATE_XLSX


class ArduinoCommandError(RuntimeError):
    pass


class ArduinoManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._serial = None
        self._last_error = ""
        self._last_response = ""
        self._connection_state = "unconfigured"
        self._door_states = [
            {"door": 1, "state": "UNKNOWN"},
            {"door": 2, "state": "UNKNOWN"},
            {"door": SUPPLY_DOOR_NUMBER, "state": "CLOSED"},
        ]
        self._switches = {}
        self._tray_position = None
        self._tray_calibrated = False
        self._tray_enabled = False
        self._tray_busy = False
        self._busy = False
        self._background_thread = None

    def settings(self) -> dict:
        saved = read_json_file(ARDUINO_SETTINGS_JSON, {})
        env_port = os.environ.get("ARDUINO_PORT", "").strip()
        saved_port = str(saved.get("port") or "").strip()
        port = env_port or saved_port
        source = "env" if env_port else "file" if saved_port else "default"
        timeout_ms = self._read_timeout_ms(saved)
        return {
            "port": port,
            "baud_rate": ARDUINO_BAUD_RATE,
            "timeout_ms": timeout_ms,
            "settings_source": source,
        }

    def configure(self, payload: dict) -> dict:
        port = str(payload.get("port") or payload.get("arduinoPort") or "").strip()
        timeout_ms = self._coerce_timeout_ms(
            payload.get("timeout_ms") or payload.get("arduinoTimeout") or DEFAULT_ARDUINO_TIMEOUT_MS
        )
        saved_settings = {
            "port": port,
            "baud_rate": ARDUINO_BAUD_RATE,
            "timeout_ms": timeout_ms,
        }
        with self._lock:
            self._close_locked()
            write_json_file(ARDUINO_SETTINGS_JSON, saved_settings)
            self._last_error = ""
            self._connection_state = "unconfigured"
        return self.settings()

    def status(self, *, ping: bool = False, refresh: bool = False) -> dict:
        settings = self.settings()
        if settings["port"] and (ping or refresh):
            try:
                if ping:
                    self.send("PING", timeout_ms=5000)
                self.refresh_status(timeout_ms=5000)
            except Exception:
                pass

        with self._lock:
            connected = bool(self._serial and getattr(self._serial, "is_open", False))
            if not settings["port"]:
                self._connection_state = "unconfigured"
            return {
                "configured": bool(settings["port"]),
                "connected": connected,
                "connection_state": self._connection_state,
                "port": settings["port"],
                "baud_rate": settings["baud_rate"],
                "timeout_ms": settings["timeout_ms"],
                "settings_source": settings["settings_source"],
                "last_error": self._last_error,
                "last_response": self._last_response,
                "door_states": self._door_states,
                "switches": self._switches,
                "tray_position": self._tray_position,
                "tray_calibrated": self._tray_calibrated,
                "tray_enabled": self._tray_enabled,
                "tray_busy": self._tray_busy,
                "busy": self._busy,
            }

    def send(self, command: str, *, timeout_ms: int | None = None) -> str:
        command = str(command or "").strip().upper()
        if not command:
            raise ValueError("Thiếu lệnh Arduino.")
        settings = self.settings()
        if not settings["port"]:
            raise RuntimeError("Chưa cấu hình Arduino port.")
        with self._lock:
            self._busy = True
            try:
                self._ensure_serial_locked(settings)
                response = self._send_locked(command, settings, timeout_ms or settings["timeout_ms"])
                self._connection_state = "connected"
                if command == "STATUS":
                    self._parse_status_line(response)
                return response
            except ArduinoCommandError as exc:
                self._last_error = str(exc)
                self._connection_state = "hardware_error"
                raise
            except Exception as exc:
                self._last_error = str(exc)
                self._connection_state = "error"
                self._close_locked()
                raise
            finally:
                self._busy = False

    def home(self) -> str:
        # Cua vat tu (cua 3) dang tam khoa; tuyet doi khong kich motor cua nay.
        for door in (1, 2):
            self.send(f"DOOR:{door}:CLOSE", timeout_ms=ARDUINO_HOME_TIMEOUT_MS)
        try:
            self.refresh_status(timeout_ms=5000)
        except Exception:
            pass
        return "DONE:HOME"

    def calibrate_tray(self) -> str:
        response = self.send("CALIBRATE:1", timeout_ms=5000)
        self.refresh_status(timeout_ms=5000)
        return response

    def release_tray(self) -> str:
        response = self.send("TRAY:RELEASE", timeout_ms=5000)
        self.refresh_status(timeout_ms=5000)
        return response

    def refresh_status(self, *, timeout_ms: int = 5000) -> str:
        return self.send("STATUS", timeout_ms=timeout_ms)

    def start_background_worker(self) -> None:
        if self._background_thread and self._background_thread.is_alive():
            return
        self._background_thread = threading.Thread(target=self._background_loop, daemon=True)
        self._background_thread.start()

    def _background_loop(self) -> None:
        while True:
            settings = self.settings()
            if not settings["port"]:
                with self._lock:
                    self._connection_state = "unconfigured"
                    self._close_locked()
                time.sleep(ARDUINO_RECONNECT_INTERVAL_SECONDS)
                continue

            try:
                self._connect_and_probe(settings)
                time.sleep(ARDUINO_STATUS_INTERVAL_SECONDS)
            except ArduinoCommandError:
                time.sleep(ARDUINO_RECONNECT_INTERVAL_SECONDS)
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
                    self._connection_state = "error"
                    self._close_locked()
                time.sleep(ARDUINO_RECONNECT_INTERVAL_SECONDS)

    def _connect_and_probe(self, settings: dict) -> None:
        with self._lock:
            was_disconnected = not (self._serial and getattr(self._serial, "is_open", False))
            self._busy = True
            try:
                self._ensure_serial_locked(settings)
                if was_disconnected:
                    try:
                        for door in (1, 2):
                            self._send_locked(f"DOOR:{door}:CLOSE", settings, ARDUINO_HOME_TIMEOUT_MS)
                    except ArduinoCommandError:
                        self._connection_state = "hardware_error"
                try:
                    status_line = self._send_locked("STATUS", settings, 5000)
                    self._parse_status_line(status_line)
                    if self._connection_state != "hardware_error":
                        self._connection_state = "connected"
                    if not self._last_error.startswith("ERROR:"):
                        self._last_error = ""
                except ArduinoCommandError:
                    self._connection_state = "hardware_error"
                    raise
            finally:
                self._busy = False

    def _ensure_serial_locked(self, settings: dict):
        if self._serial and getattr(self._serial, "is_open", False):
            return self._serial
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Thiếu pyserial. Cài dependencies bằng: pip install -r requirements.txt") from exc

        self._connection_state = "connecting"
        timeout_seconds = max(settings["timeout_ms"] / 1000, 0.5)
        self._serial = serial.Serial(
            settings["port"],
            ARDUINO_BAUD_RATE,
            timeout=0.12,
            write_timeout=timeout_seconds,
        )
        self._wait_for_ready_locked()
        self._connection_state = "connected"
        return self._serial

    def _wait_for_ready_locked(self) -> None:
        deadline = time.monotonic() + (ARDUINO_BOOT_TIMEOUT_MS / 1000)
        next_ping_at = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_ping_at:
                try:
                    self._serial.write(b"PING\n")
                    self._serial.flush()
                except Exception:
                    pass
                next_ping_at = time.monotonic() + 2.0
            raw_line = self._serial.readline()
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            self._last_response = line
            if line.startswith("ERROR:"):
                self._last_error = line
            if line in {"READY", "READY:ERROR"}:
                return
            if line == "DONE:PONG":
                return
        raise TimeoutError("Arduino không gửi READY sau khi mở cổng serial.")

    def _send_locked(self, command: str, settings: dict, timeout_ms: int) -> str:
        serial_port = self._serial
        if not serial_port or not getattr(serial_port, "is_open", False):
            raise RuntimeError("Arduino serial chưa mở.")
        try:
            serial_port.reset_input_buffer()
        except Exception:
            pass
        serial_port.write((command + "\n").encode("utf-8"))
        serial_port.flush()
        deadline = time.monotonic() + (max(timeout_ms, 500) / 1000)
        while time.monotonic() < deadline:
            raw_line = serial_port.readline()
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            self._last_response = line
            if line.startswith("READY:"):
                continue
            if command == "STATUS" and line.startswith("STATUS:"):
                self._last_error = "" if self._connection_state != "hardware_error" else self._last_error
                return line
            if line.startswith("DONE:"):
                self._last_error = ""
                return line
            if line.startswith("ERROR:"):
                self._last_error = line
                raise ArduinoCommandError(line)
        raise TimeoutError(f"Arduino timeout khi gửi lệnh {command}.")

    def _parse_status_line(self, line: str) -> None:
        if not line.startswith("STATUS:"):
            return
        values = {}
        for part in line.removeprefix("STATUS:").split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            values[key.strip().upper()] = value.strip().upper()

        allowed_states = {"CLOSED", "OPEN", "BETWEEN", "CONFLICT"}
        self._door_states = [
            {
                "door": index,
                "state": "CLOSED"
                if index == SUPPLY_DOOR_NUMBER
                else values.get(f"D{index}", "UNKNOWN")
                if values.get(f"D{index}") in allowed_states
                else "UNKNOWN",
            }
            for index in range(1, 4)
        ]
        self._switches = {
            key: values.get(key) == "1"
            for key in ("A0", "A1", "A2", "A3", "A4", "A5")
            if key in values
        }
        tray_text = values.get("T", "UNKNOWN")
        try:
            tray_position = int(tray_text)
        except (TypeError, ValueError):
            tray_position = None
        self._tray_position = tray_position if tray_position in range(1, 9) else None
        self._tray_enabled = values.get("TEN") == "1"
        self._tray_calibrated = values.get("TCAL") == "1" and self._tray_enabled
        self._tray_busy = values.get("TBUSY") == "1"

    def _read_timeout_ms(self, saved: dict) -> int:
        env_timeout = os.environ.get("ARDUINO_TIMEOUT_MS", "").strip()
        if env_timeout:
            return self._coerce_timeout_ms(env_timeout)
        return self._coerce_timeout_ms(saved.get("timeout_ms") or DEFAULT_ARDUINO_TIMEOUT_MS)

    def _coerce_timeout_ms(self, value: object) -> int:
        try:
            timeout_ms = int(value)
        except (TypeError, ValueError):
            timeout_ms = DEFAULT_ARDUINO_TIMEOUT_MS
        return max(timeout_ms, 500)

    def _close_locked(self) -> None:
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None


arduino_manager = ArduinoManager()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


class DispenseCoordinator:
    def __init__(self, manager: ArduinoManager) -> None:
        self.manager = manager
        self._lock = threading.RLock()
        self._watchdog_thread = None

    def start(self) -> None:
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._recover_interrupted_session()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def current_session(self) -> dict | None:
        session = load_runtime_state().get("session")
        return dict(session) if isinstance(session, dict) else None

    def status(self, session_id: str = "") -> dict | None:
        session = self.current_session()
        if not session:
            return None
        if session_id and session.get("id") != session_id:
            return None
        return session

    def has_blocking_session(self) -> bool:
        session = self.current_session()
        return bool(session and session.get("status") in ACTIVE_DISPENSE_STATES)

    def require_no_active_session(self) -> None:
        if self.has_blocking_session():
            raise RobotWorkflowError("ROBOT_BUSY", "Robot đang có một phiên cấp phát cần hoàn tất hoặc xử lý.")

    def hardware_status(self, *, require_calibrated: bool = False, require_closed: bool = False) -> dict:
        status = self.manager.status(refresh=True)
        if not status.get("connected"):
            raise RobotWorkflowError("HARDWARE_TIMEOUT", "Arduino chưa kết nối.", HTTPStatus.BAD_GATEWAY)
        if require_calibrated and not status.get("tray_calibrated"):
            raise RobotWorkflowError("TRAY_NOT_CALIBRATED", "Khay chưa được bác sĩ xác nhận mốc K1.")
        if require_calibrated and not status.get("tray_enabled"):
            raise RobotWorkflowError("TRAY_NOT_CALIBRATED", "Driver khay chưa được khóa bằng ENA.")
        if require_closed:
            door_states = status.get("door_states") or []
            if len(door_states) != 3 or any(item.get("state") != "CLOSED" for item in door_states):
                raise RobotWorkflowError("DOORS_NOT_CLOSED", "Phải đóng cả ba cửa trước khi tiếp tục.")
        return status

    def begin(self, patient_id: str) -> tuple[dict, dict, str]:
        with self._lock:
            self.require_no_active_session()
            state = load_orders_state()
            order = next(
                (item for item in state.get("orders", []) if str(item.get("id") or item.get("patient_id")) == patient_id),
                None,
            )
            if not order:
                raise RobotWorkflowError("ORDER_NOT_FOUND", "Không tìm thấy ID bệnh nhân.", HTTPStatus.NOT_FOUND)
            validated = validate_order_data(order)
            order_status = validated["dispense_status"]
            if not validated["setup_done"] or order_status == "pending_setup":
                raise RobotWorkflowError("ORDER_NOT_READY", "Đơn thuốc chưa được bác sĩ setup xong.")
            if order_status == "dispensed":
                raise RobotWorkflowError("ORDER_ALREADY_DISPENSED", "Đơn thuốc này đã được lấy.")
            if order_status == "interrupted":
                raise RobotWorkflowError("DISPENSE_INTERRUPTED", "Đơn thuốc cần bác sĩ xác minh trước khi tiếp tục.")
            if order_status != "ready":
                raise RobotWorkflowError("ROBOT_BUSY", "Đơn thuốc đang được xử lý.")

            self.hardware_status(require_calibrated=True, require_closed=True)
            session = {
                "id": uuid.uuid4().hex,
                "patient_id": patient_id,
                "slot": validated["slot"],
                "door": validated["door"],
                "status": "opening",
                "opened_at": None,
                "auto_close_at": None,
                "closed_at": None,
                "close_source": None,
                "error": None,
            }
            order["dispense_status"] = "dispensing"
            save_orders_state(state)
            save_runtime_state({"session": session})

            try:
                response = self.manager.send(
                    f"DISPENSE:{validated['slot']}:{validated['door']}", timeout_ms=DISPENSE_COMMAND_TIMEOUT_MS
                )
            except Exception as exc:
                self._interrupt_locked(session, state, order, str(exc))
                raise RobotWorkflowError(
                    "HARDWARE_TIMEOUT", "Không hoàn tất được thao tác mở khay.", HTTPStatus.BAD_GATEWAY
                ) from exc

            opened_at = utc_now()
            session.update(
                {
                    "status": "open",
                    "opened_at": iso_utc(opened_at),
                    "auto_close_at": iso_utc(opened_at + timedelta(seconds=DISPENSE_OPEN_SECONDS)),
                }
            )
            save_runtime_state({"session": session})
            return public_order(order), dict(session), response

    def complete(self, session_id: str, *, source: str) -> tuple[dict, dict, str]:
        with self._lock:
            runtime = load_runtime_state()
            session = runtime.get("session")
            if not isinstance(session, dict) or session.get("id") != session_id:
                raise RobotWorkflowError("SESSION_NOT_FOUND", "Không tìm thấy phiên lấy thuốc.", HTTPStatus.NOT_FOUND)
            if session.get("status") == "completed":
                order = find_order_by_patient_id(session.get("patient_id", ""))
                return public_order(order), dict(session), "DONE:DOOR"
            if session.get("status") not in {"open", "closing"}:
                raise RobotWorkflowError("DISPENSE_INTERRUPTED", "Phiên lấy thuốc cần bác sĩ xử lý.")

            state = load_orders_state()
            order = next((item for item in state.get("orders", []) if item.get("id") == session.get("patient_id")), None)
            if not order:
                raise RobotWorkflowError("ORDER_NOT_FOUND", "Không tìm thấy đơn của phiên.", HTTPStatus.NOT_FOUND)
            session["status"] = "closing"
            save_runtime_state(runtime)
            try:
                response = self.manager.send(f"DOOR:{int(session['door'])}:CLOSE", timeout_ms=20000)
            except Exception as exc:
                self._interrupt_locked(session, state, order, str(exc))
                raise RobotWorkflowError(
                    "DOOR_CLOSE_FAILED", "Không đóng được cửa. Vui lòng gọi nhân viên hỗ trợ.", HTTPStatus.BAD_GATEWAY
                ) from exc

            closed_at = iso_utc()
            session.update(
                {"status": "completed", "closed_at": closed_at, "close_source": source, "error": None}
            )
            order.update(
                {"dispense_status": "dispensed", "dispensed_at": closed_at, "interrupted_at": None}
            )
            save_orders_state(state)
            save_runtime_state(runtime)
            return public_order(order), dict(session), response

    def resolve(self, patient_id: str, action: str) -> dict:
        with self._lock:
            if action not in {"ALLOW_RETRY", "MARK_DISPENSED"}:
                raise RobotWorkflowError("INVALID_ACTION", "Action phải là ALLOW_RETRY hoặc MARK_DISPENSED.", HTTPStatus.BAD_REQUEST)
            self.hardware_status(require_closed=True)
            state = load_orders_state()
            order = next((item for item in state.get("orders", []) if item.get("id") == patient_id), None)
            if not order:
                raise RobotWorkflowError("ORDER_NOT_FOUND", "Không tìm thấy đơn thuốc.", HTTPStatus.NOT_FOUND)
            now = iso_utc()
            if action == "ALLOW_RETRY":
                order.update(
                    {
                        "dispense_status": "ready" if order.get("setup_done") else "pending_setup",
                        "dispensed_at": None,
                        "interrupted_at": None,
                    }
                )
            else:
                order.update({"dispense_status": "dispensed", "dispensed_at": now, "interrupted_at": None})
            runtime = load_runtime_state()
            session = runtime.get("session")
            if isinstance(session, dict) and session.get("patient_id") == patient_id:
                session["status"] = "resolved"
                session["resolution"] = action
                session["resolved_at"] = now
                save_runtime_state(runtime)
            save_orders_state(state)
            return public_order(order)

    def mark_active_interrupted(self, detail: str) -> None:
        with self._lock:
            runtime = load_runtime_state()
            session = runtime.get("session")
            if not isinstance(session, dict) or session.get("status") not in {"opening", "open", "closing"}:
                return
            state = load_orders_state()
            order = next((item for item in state.get("orders", []) if item.get("id") == session.get("patient_id")), None)
            self._interrupt_locked(session, state, order, detail)

    def _interrupt_locked(self, session: dict, state: dict, order: dict | None, detail: str) -> None:
        now = iso_utc()
        session.update({"status": "interrupted", "error": detail, "interrupted_at": now})
        if order:
            order.update({"dispense_status": "interrupted", "interrupted_at": now})
            save_orders_state(state)
        save_runtime_state({"session": session})

    def _recover_interrupted_session(self) -> None:
        session = self.current_session()
        if not session or session.get("status") not in {"opening", "open", "closing"}:
            return
        self.mark_active_interrupted("Server khởi động lại khi phiên chưa hoàn tất.")
        try:
            self.manager.home()
        except Exception:
            pass

    def _watchdog_loop(self) -> None:
        while True:
            self._watchdog_tick()
            time.sleep(0.25)

    def _watchdog_tick(self) -> None:
        session = self.current_session()
        if session and session.get("status") == "open" and session.get("auto_close_at"):
            try:
                deadline = datetime.fromisoformat(session["auto_close_at"])
                if utc_now() >= deadline:
                    self.complete(session["id"], source="timeout")
            except RobotWorkflowError:
                pass
            except Exception:
                self.mark_active_interrupted("Lỗi watchdog khi tự đóng cửa.")


dispense_coordinator = DispenseCoordinator(arduino_manager)


class RobotAssistantHandler(SimpleHTTPRequestHandler):
    server_version = "RobotAssistantHTTP/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
        if urlparse(self.path).path.startswith("/robot/api/medicine/"):
            self.send_header("Cache-Control", "no-store, private, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            self._send_file(WEB_DIR / "index.html")
            return
        if parsed.path.startswith("/robot/static/"):
            relative = parsed.path.removeprefix("/robot/static/")
            self._send_file(self._safe_web_path(relative))
            return
        if parsed.path.startswith("/assets/"):
            self._send_file(self._safe_web_path(parsed.path.removeprefix("/")))
            return
        if parsed.path == "/robot/api/medicine/template":
            self._send_attachment(ensure_template_file(), "mau-tra-cuu-thuoc.xlsx")
            return
        if parsed.path == "/robot/api/medicine/orders":
            try:
                state = load_orders_state()
                self._send_json(
                    {
                        "ok": True,
                        "orders": [public_order(order) for order in state.get("orders", [])],
                        "current_setup_slot": state.get("current_setup_slot", 1),
                        "uploaded_file_name": state.get("uploaded_file_name", ""),
                        "updated_at": state.get("updated_at"),
                    }
                )
            except InvalidOrderDataError as exc:
                self._send_invalid_order_data(exc)
            return
        if parsed.path == "/robot/api/medicine/dispense/status":
            query = parse_qs(parsed.query)
            session_id = (query.get("session_id") or [""])[0]
            session = dispense_coordinator.status(session_id)
            if not session:
                self._send_json(
                    {"ok": False, "code": "SESSION_NOT_FOUND", "detail": "Không tìm thấy phiên lấy thuốc."},
                    status=HTTPStatus.NOT_FOUND,
                )
            else:
                self._send_json({"ok": True, "session": session})
            return
        if parsed.path == "/robot/api/arduino/status":
            query = parse_qs(parsed.query)
            self._send_json(
                {
                    "ok": True,
                    "arduino": arduino_manager.status(
                        ping=query.get("ping") == ["1"],
                        refresh=query.get("refresh") == ["1"],
                    ),
                }
            )
            return

        relative = parsed.path.lstrip("/")
        if relative in {"index.html", "styles.css", "emoji.css", "app.js"}:
            self._send_file(self._safe_web_path(relative))
            return
        self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/robot/api/doctor/login":
            self._handle_doctor_login()
            return
        if parsed.path == "/robot/api/rag/answer":
            self._handle_rag_answer()
            return
        if parsed.path == "/robot/api/pharmacity/search":
            self._handle_pharmacity_search()
            return
        if parsed.path == "/robot/api/pharmacity/answer":
            self._handle_pharmacity_answer()
            return
        if parsed.path == "/robot/api/gemini/ephemeral-token":
            self._handle_gemini_ephemeral_token()
            return
        if parsed.path == "/robot/api/realtime/session":
            self._handle_realtime_session()
            return
        if parsed.path == "/robot/api/voice-metrics":
            self._handle_voice_metrics()
            return
        if parsed.path == "/robot/api/medicine/orders/upload":
            self._handle_orders_upload(parsed)
            return
        if parsed.path == "/robot/api/medicine/setup/check":
            self._handle_setup_check()
            return
        if parsed.path == "/robot/api/medicine/setup/tray":
            self._handle_setup_tray()
            return
        if parsed.path == "/robot/api/medicine/lookup":
            self._handle_medicine_lookup()
            return
        if parsed.path == "/robot/api/medicine/dispense":
            self._handle_medicine_dispense()
            return
        if parsed.path == "/robot/api/medicine/dispense/complete":
            self._handle_medicine_dispense_complete()
            return
        if parsed.path == "/robot/api/medicine/dispense/resolve":
            self._handle_medicine_dispense_resolve()
            return
        if parsed.path == "/robot/api/arduino/settings":
            self._handle_arduino_settings()
            return
        if parsed.path == "/robot/api/arduino/home":
            self._handle_arduino_home()
            return
        if parsed.path == "/robot/api/arduino/door":
            self._handle_arduino_door()
            return
        if parsed.path == "/robot/api/arduino/tray/calibrate":
            self._handle_arduino_tray_calibrate()
            return
        if parsed.path == "/robot/api/arduino/tray/release":
            self._handle_arduino_tray_release()
            return
        self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _safe_web_path(self, relative: str) -> Path:
        candidate = (WEB_DIR / unquote(relative)).resolve()
        web_root = WEB_DIR.resolve()
        if candidate != web_root and web_root not in candidate.parents:
            return WEB_DIR / "__not_found__"
        return candidate

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_attachment(self, path: Path, download_name: str) -> None:
        if not path.is_file():
            self._send_json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(download_name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or 0)
        return self.rfile.read(length) if length else b""

    def _read_json(self) -> dict:
        raw = self._read_body()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

    def _send_invalid_order_data(self, error: Exception) -> None:
        self._send_json(
            {
                "ok": False,
                "code": "INVALID_ORDER_DATA",
                "detail": "Dữ liệu đơn thuốc không đầy đủ hoặc không nhất quán. Vui lòng liên hệ nhân viên y tế.",
                "error": str(error),
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    def _send_workflow_error(self, error: RobotWorkflowError) -> None:
        self._send_json(
            {"ok": False, "code": error.code, "detail": error.detail},
            status=error.status,
        )

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, *, status: HTTPStatus = HTTPStatus.OK, content_type: str = "text/plain") -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_doctor_login(self) -> None:
        """Check doctor credentials on the server; they are read from .env, never shipped to the browser."""
        expected_username = os.environ.get("DOCTOR_USERNAME", "doctor").strip()
        expected_password = os.environ.get("DOCTOR_PASSWORD", "")
        if not expected_password:
            self._send_json(
                {"ok": False, "detail": "Doctor login is not configured. Set DOCTOR_PASSWORD in .env."},
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return
        try:
            payload = self._read_json()
        except ValueError:
            self._send_json({"ok": False, "detail": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        username_ok = hmac.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8"))
        password_ok = hmac.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
        if not (username_ok and password_ok):
            self._send_json({"ok": False, "detail": "Invalid username or password"}, status=HTTPStatus.UNAUTHORIZED)
            return
        self._send_json({"ok": True})

    def _handle_rag_answer(self) -> None:
        try:
            payload = self._read_json()
            query = str(payload.get("query") or "").strip()
            if not query:
                self._send_json({"detail": "Missing query"}, status=HTTPStatus.BAD_REQUEST)
                return
            top_k = int(payload.get("top_k") or 5)
            voice = bool(payload.get("voice", True))
            self._send_json(rag_answer(query, voice=voice, top_k=top_k))
        except Exception as exc:
            self._send_json({"detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_pharmacity_search(self) -> None:
        try:
            payload = self._read_json()
            query = str(payload.get("query") or "").strip()
            if not query:
                self._send_json({"detail": "Missing query"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = search_products(
                query,
                original_query=str(payload.get("original_query") or query),
                target_intent=str(payload.get("target_intent") or "") or None,
            )
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_pharmacity_answer(self) -> None:
        try:
            payload = self._read_json()
            product = payload.get("product")
            if not isinstance(product, dict):
                self._send_json({"detail": "Missing product"}, status=HTTPStatus.BAD_REQUEST)
                return
            original_query = str(payload.get("original_query") or product.get("name") or "").strip()
            target_intent = str(payload.get("target_intent") or "").strip()
            result = answer_product_question(original_query, target_intent, product)
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_realtime_session(self) -> None:
        self._send_json(
            {"detail": "OpenAI realtime is disabled. Use /robot/api/gemini/ephemeral-token for Gemini Live."},
            status=HTTPStatus.GONE,
        )

    def _handle_gemini_ephemeral_token(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            self._send_json({"detail": "Missing GEMINI_API_KEY"}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            return

        model = os.environ.get("GEMINI_LIVE_MODEL", "").strip() or DEFAULT_GEMINI_LIVE_MODEL
        voice = os.environ.get("GEMINI_LIVE_VOICE", "").strip() or "Kore"
        try:
            token_name = create_gemini_ephemeral_token(api_key, model, voice)
        except ImportError:
            self._send_json(
                {"detail": "Missing google-genai. Install dependencies with: pip install -r requirements.txt"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        except Exception:
            self._send_json(
                {"detail": "Gemini ephemeral token request failed. Check GEMINI_API_KEY and model access."},
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        self._send_json(
            {
                "token": token_name,
                "model": model,
                "voice": voice,
                "expires_in_seconds": 1800,
            }
        )

    def _handle_voice_metrics(self) -> None:
        try:
            payload = self._read_json()
            print(f"voice_metric {json.dumps(payload, ensure_ascii=False)}")
        except Exception:
            pass
        self._send_json({"ok": True})

    def _handle_orders_upload(self, parsed) -> None:
        body = self._read_body()
        if not body:
            self._send_json({"ok": False, "detail": "Chưa có file Excel."}, status=HTTPStatus.BAD_REQUEST)
            return

        query = parse_qs(parsed.query)
        upload_name = query.get("filename", ["current_orders.xlsx"])[0] or "current_orders.xlsx"
        suffix = Path(upload_name).suffix.lower()
        if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
            self._send_json(
                {"ok": False, "detail": "Chỉ hỗ trợ upload file Excel .xlsx."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            dispense_coordinator.require_no_active_session()
            dispense_coordinator.hardware_status(require_closed=True)
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
            return

        ensure_data_dir()
        temp_path = Path(tempfile.gettempdir()) / f"robot_orders_upload_{time.time_ns()}.xlsx"
        temp_path.write_bytes(body)
        try:
            orders = parse_excel_orders(temp_path)
        except ValueError as exc:
            errors = [line for line in str(exc).splitlines() if line.strip()]
            self._send_json(
                {"ok": False, "detail": errors[0] if errors else "File Excel không hợp lệ.", "errors": errors},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        CURRENT_ORDERS_XLSX.write_bytes(body)
        state = {
            "orders": orders,
            "current_setup_slot": 1,
            "uploaded_file_name": Path(upload_name).name,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        save_orders_state(state)
        self._send_json(
            {
                "ok": True,
                "message": f"Đã upload {len(orders)} đơn thuốc.",
                "orders": [public_order(order) for order in orders],
                "current_setup_slot": 1,
                "uploaded_file_name": state["uploaded_file_name"],
            }
        )

    def _handle_setup_check(self) -> None:
        try:
            payload = self._read_json()
            position = str(payload.get("position") or "").strip().upper()
            done = bool(payload.get("done"))
            if not POSITION_RE.fullmatch(position):
                self._send_json({"ok": False, "detail": "Vị trí khay không hợp lệ."}, status=HTTPStatus.BAD_REQUEST)
                return
            state = load_orders_state()
            matched = False
            for order in state.get("orders", []):
                if order.get("position") == position:
                    if order.get("dispense_status") in {"dispensing", "dispensed", "interrupted"}:
                        raise RobotWorkflowError(
                            "ORDER_STATE_LOCKED", "Không thể đổi setup của đơn đang xử lý hoặc đã lấy."
                        )
                    order["setup_done"] = done
                    order["dispense_status"] = "ready" if done else "pending_setup"
                    matched = True
                    break
            if not matched:
                self._send_json({"ok": False, "detail": "Không tìm thấy vị trí cần cập nhật."}, status=HTTPStatus.NOT_FOUND)
                return
            save_orders_state(state)
            self._send_json({"ok": True, "position": position, "done": done})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_setup_tray(self) -> None:
        try:
            payload = self._read_json()
            slot = int(payload.get("slot") or payload.get("position") or 0)
            if slot < 1 or slot > 8:
                self._send_json({"ok": False, "detail": "Vị trí khay phải từ 1 đến 8."}, status=HTTPStatus.BAD_REQUEST)
                return
            dispense_coordinator.require_no_active_session()
            dispense_coordinator.hardware_status(require_calibrated=True, require_closed=True)
            response = arduino_manager.send(f"TRAY:{slot}")
            state = load_orders_state()
            state["current_setup_slot"] = slot
            save_orders_state(state)
            self._send_json({"ok": True, "slot": slot, "arduino": response})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_medicine_lookup(self) -> None:
        try:
            payload = self._read_json()
            patient_id = str(payload.get("patient_id") or payload.get("code") or "").strip()
            order = find_order_by_patient_id(patient_id)
            if not order:
                self._send_json(
                    {"ok": False, "detail": "Không tìm thấy ID bệnh nhân trong danh sách đơn thuốc."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            self._send_json({"ok": True, "order": public_order(order)})
        except InvalidOrderDataError as exc:
            self._send_invalid_order_data(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_medicine_dispense(self) -> None:
        try:
            payload = self._read_json()
            patient_id = str(payload.get("patient_id") or payload.get("code") or "").strip()
            order, session, response = dispense_coordinator.begin(patient_id)
            self._send_json({"ok": True, "order": order, "session": session, "arduino": response})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except InvalidOrderDataError as exc:
            self._send_invalid_order_data(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_medicine_dispense_complete(self) -> None:
        try:
            payload = self._read_json()
            session_id = str(payload.get("session_id") or "").strip()
            if not session_id:
                patient_id = str(payload.get("patient_id") or payload.get("code") or "").strip()
                current = dispense_coordinator.current_session()
                if current and current.get("patient_id") == patient_id:
                    session_id = str(current.get("id") or "")
            order, session, response = dispense_coordinator.complete(session_id, source="patient")
            self._send_json({"ok": True, "order": order, "session": session, "arduino": response})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except InvalidOrderDataError as exc:
            self._send_invalid_order_data(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_medicine_dispense_resolve(self) -> None:
        try:
            payload = self._read_json()
            patient_id = str(payload.get("patient_id") or "").strip()
            action = str(payload.get("action") or "").strip().upper()
            order = dispense_coordinator.resolve(patient_id, action)
            self._send_json({"ok": True, "order": order})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except InvalidOrderDataError as exc:
            self._send_invalid_order_data(exc)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_arduino_settings(self) -> None:
        try:
            payload = self._read_json()
            settings = arduino_manager.configure(payload)
            self._send_json({"ok": True, "arduino": arduino_manager.status(), "settings": settings})
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_arduino_home(self) -> None:
        try:
            response = arduino_manager.home()
            dispense_coordinator.mark_active_interrupted("Cửa được đóng bằng lệnh HOME trước khi phiên hoàn tất.")
            self._send_json({"ok": True, "arduino": response, "status": arduino_manager.status()})
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_arduino_door(self) -> None:
        try:
            payload = self._read_json()
            door = int(payload.get("door") or 0)
            action = str(payload.get("action") or "").strip().upper()
            if door not in {1, 2, 3}:
                self._send_json({"ok": False, "detail": "Cửa phải là 1, 2 hoặc 3."}, status=HTTPStatus.BAD_REQUEST)
                return
            if door == SUPPLY_DOOR_NUMBER:
                self._send_json(
                    {"ok": False, "detail": "Cửa vật tư y tế đang tạm khóa và không thể điều khiển."},
                    status=HTTPStatus.CONFLICT,
                )
                return
            if action not in {"OPEN", "CLOSE"}:
                self._send_json({"ok": False, "detail": "Action phải là OPEN hoặc CLOSE."}, status=HTTPStatus.BAD_REQUEST)
                return
            dispense_coordinator.require_no_active_session()
            response = arduino_manager.send(f"DOOR:{door}:{action}")
            try:
                arduino_manager.refresh_status(timeout_ms=5000)
            except Exception:
                pass
            self._send_json(
                {"ok": True, "door": door, "action": action, "arduino": response, "status": arduino_manager.status()}
            )
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except ValueError as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"ok": False, "detail": str(exc)}, status=HTTPStatus.BAD_GATEWAY)

    def _handle_arduino_tray_calibrate(self) -> None:
        try:
            dispense_coordinator.require_no_active_session()
            dispense_coordinator.hardware_status()
            response = arduino_manager.calibrate_tray()
            status = arduino_manager.status()
            self._send_json({"ok": True, "arduino": response, "status": status})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except Exception as exc:
            self._send_json(
                {"ok": False, "code": "HARDWARE_TIMEOUT", "detail": str(exc)},
                status=HTTPStatus.BAD_GATEWAY,
            )

    def _handle_arduino_tray_release(self) -> None:
        try:
            dispense_coordinator.require_no_active_session()
            dispense_coordinator.hardware_status()
            response = arduino_manager.release_tray()
            self._send_json({"ok": True, "arduino": response, "status": arduino_manager.status()})
        except RobotWorkflowError as exc:
            self._send_workflow_error(exc)
        except Exception as exc:
            self._send_json(
                {"ok": False, "code": "HARDWARE_TIMEOUT", "detail": str(exc)},
                status=HTTPStatus.BAD_GATEWAY,
            )


def rag_tool_schema() -> dict:
    return {
        "type": "function",
        "name": "rag_answer",
        "description": (
            "Tra cứu dữ liệu Bệnh viện Hạnh Phúc bằng RAG. Bắt buộc gọi tool này trước khi trả lời "
            "các câu hỏi về địa chỉ, hotline, giờ làm việc, khoa, bác sĩ, lịch khám, gói dịch vụ, "
            "chi phí, tiện ích, chính sách hoặc yêu cầu lấy thuốc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi tiếng Việt nguyên văn của người dùng.",
                }
            },
            "required": ["query"],
        },
    }


def gemini_rag_function_declaration() -> dict:
    return {
        "name": "rag_answer",
        "description": (
            "Tra cứu dữ liệu Bệnh viện Hạnh Phúc bằng RAG. Bắt buộc gọi tool này trước khi trả lời "
            "các câu hỏi về địa chỉ, hotline, giờ làm việc, khoa, bác sĩ, lịch khám, gói dịch vụ, "
            "chi phí, tiện ích, chính sách hoặc yêu cầu lấy thuốc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Nội dung tra cứu bằng tiếng Việt. Nếu người dùng nói tiếng Anh, dịch câu hỏi sang "
                        "tiếng Việt nhưng giữ nguyên tên riêng, số liệu và mã định danh trước khi gọi tool."
                    ),
                }
            },
            "required": ["query"],
        },
    }


def gemini_pharmacity_function_declaration() -> dict:
    return {
        "name": "pharmacity_search",
        "description": (
            "Tra cứu thuốc hoặc sản phẩm thuốc trên Pharmacity. Gọi tool này khi người dùng hỏi "
            "về tên thuốc cụ thể, cách dùng, công dụng, thành phần, lưu ý, chống chỉ định, "
            "tác dụng phụ hoặc giá thuốc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Nội dung tra cứu thuốc bằng tiếng Việt. Nếu người dùng nói tiếng Anh, dịch câu hỏi "
                        "sang tiếng Việt nhưng giữ nguyên tên thuốc, thương hiệu, số liệu và mã định danh "
                        "trước khi gọi tool."
                    ),
                }
            },
            "required": ["query"],
        },
    }


def build_gemini_live_instructions() -> str:
    return (
        "Bạn là KungKung, trợ lý voice song ngữ Việt-Anh cho webapp robot y tế của Bệnh viện Hạnh Phúc. "
        "Ở đầu mỗi cuộc hội thoại, hãy xác định ngôn ngữ từ phát ngôn có ý nghĩa đầu tiên của người dùng "
        "rồi khóa ngôn ngữ trả lời là tiếng Việt hoặc tiếng Anh. "
        "Nếu phát ngôn đầu tiên quá ngắn, chỉ là tên riêng, hoặc trộn tiếng Việt với tiếng Anh, mặc định khóa tiếng Việt. "
        "Sau khi đã khóa, luôn trả lời bằng ngôn ngữ đó dù người dùng dùng ngôn ngữ còn lại; "
        "chỉ đổi khi người dùng yêu cầu rõ ràng và phải giữ nguyên ngữ cảnh hội thoại. "
        "Khi trả lời tiếng Việt, giữ nguyên bằng tiếng Anh các thuật ngữ chuyên môn, tên kỹ thuật, tên sản phẩm, "
        "tên thương hiệu và chữ viết tắt đã được chuẩn hóa. Khi trả lời tiếng Anh, dùng tiếng Anh tự nhiên. "
        "Trả lời ngắn, rõ, thân thiện cho bệnh nhân và người nhà. "
        "Trước khi gọi rag_answer hoặc pharmacity_search cho câu hỏi tiếng Anh, hãy dịch nội dung tra cứu sang tiếng Việt "
        "nhưng giữ nguyên tên riêng, tên thuốc, số liệu và mã định danh; tham số query gửi vào tool phải là tiếng Việt. "
        "Khi người dùng hỏi thông tin bệnh viện, khoa, bác sĩ, lịch khám, gói dịch vụ, tiện ích, "
        "chính sách hoặc yêu cầu lấy thuốc/điều khiển thiết bị, hãy gọi tool rag_answer trước rồi chỉ dựa trên kết quả tool để trả lời. "
        "Không trả lời kiến thức tổng quát ngoài phạm vi Bệnh viện Hạnh Phúc và tra cứu sản phẩm thuốc. "
        "Nếu câu hỏi ngoài phạm vi, hãy nói rõ giới hạn và gợi ý các chủ đề được hỗ trợ, không suy đoán và không nhắc hotline. "
        "Kết quả tool có thể bằng tiếng Việt; hãy chuyển sang ngôn ngữ đang khóa một cách trung thành và không thêm dữ kiện. "
        "Nếu rag_answer trả grounded=false, phải giữ đúng ý nghĩa trường answer; chỉ được dịch sang ngôn ngữ đang khóa, "
        "không bổ sung hoặc diễn giải thành thông tin mới. "
        "Khi người dùng hỏi về thuốc hoặc sản phẩm thuốc cụ thể như tên thuốc, cách dùng, công dụng, thành phần, "
        "lưu ý, chống chỉ định, tác dụng phụ hoặc giá thuốc, hãy gọi tool pharmacity_search. "
        "Không từ chối câu hỏi tra cứu thông tin thuốc có tên sản phẩm; hãy chờ người dùng chọn sản phẩm trên màn hình, "
        "sau đó trả lời ngắn dựa trên dữ liệu Pharmacity đã crawl. "
        "Không chẩn đoán bệnh, không kê đơn, không tự điều chỉnh liều và không xác nhận thuốc phù hợp với triệu chứng cá nhân. "
        "Nếu người dùng hỏi nên uống thuốc gì cho triệu chứng mà không nêu sản phẩm cụ thể, hãy từ chối kê đơn và khuyên hỏi bác sĩ hoặc dược sĩ. "
        "Chỉ nhắc hotline khi tool đã đưa hotline trong trường answer. "
        "Nếu tool trả requires_hardware_confirmation=true, hãy nói người dùng xác nhận trên màn hình; "
        "không tự khẳng định đã lấy thuốc hoặc đã điều khiển thiết bị."
    )


def create_gemini_ephemeral_token(api_key: str, model: str, voice: str) -> str:
    from google import genai
    from google.genai import types

    now = datetime.now(tz=timezone.utc)
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(apiVersion="v1alpha"),
    )
    token = client.auth_tokens.create(
        config=types.CreateAuthTokenConfig(
            uses=1,
            expireTime=now + timedelta(minutes=30),
            newSessionExpireTime=now + timedelta(minutes=1),
            liveConnectConstraints=types.LiveConnectConstraints(
                model=model,
                config=types.LiveConnectConfig(
                    responseModalities=["AUDIO"],
                    temperature=0.2,
                    speechConfig={
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": voice,
                            }
                        }
                    },
                    systemInstruction=build_gemini_live_instructions(),
                    tools=[
                        {
                            "function_declarations": [
                                gemini_rag_function_declaration(),
                                gemini_pharmacity_function_declaration(),
                            ]
                        }
                    ],
                    inputAudioTranscription={},
                    outputAudioTranscription={},
                ),
            ),
            httpOptions=types.HttpOptions(apiVersion="v1alpha"),
        )
    )
    if not token.name:
        raise RuntimeError("Gemini token response did not include token name.")
    return token.name


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    os.chdir(ROOT_DIR)
    arduino_manager.start_background_worker()
    dispense_coordinator.start()
    httpd = ThreadingHTTPServer((host, port), RobotAssistantHandler)
    print(f"Serving Web_emoji at http://{host}:{port}")
    print(f"Arduino port: {arduino_manager.settings()['port'] or 'not configured'}")
    print(f"Gemini Live model: {os.environ.get('GEMINI_LIVE_MODEL', DEFAULT_GEMINI_LIVE_MODEL)}")
    print(f"Gemini Live voice: {os.environ.get('GEMINI_LIVE_VOICE', 'Kore')}")
    print("Set GEMINI_API_KEY before using Gemini Live voice.")
    httpd.serve_forever()


if __name__ == "__main__":
    host, port = main_server_address()
    run(host, port)
