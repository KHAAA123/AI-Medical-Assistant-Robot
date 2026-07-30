import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from contextlib import contextmanager
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openpyxl import Workbook

import server
from pharmacity_chatbot import server as pharmacity_server


VALID_ORDER = {
    "id": "BN001",
    "patient_id": "BN001",
    "position": "K1_2",
    "tray": 1,
    "slot": 2,
    "door": 1,
    "name": "Nguyễn Văn A",
    "bed": "B01",
    "prescription": "Thuốc A",
    "instructions": "Uống sau ăn",
    "setup_done": True,
}


def make_orders_workbook(rows, headers=None) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or server.REQUIRED_ORDER_COLUMNS)
    for row in rows:
        sheet.append(row)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        workbook.save(temp_path)
        return temp_path.read_bytes()
    finally:
        workbook.close()
        temp_path.unlink(missing_ok=True)


@contextmanager
def running_server(handler):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def read_response(request):
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    body = response.read()
    return response, json.loads(body.decode("utf-8")) if body else {}


class OrderContractTests(unittest.TestCase):
    def test_valid_order_is_normalized(self):
        result = server.validate_order_data(VALID_ORDER)
        self.assertEqual(result["id"], "BN001")
        self.assertEqual(result["position"], "K1_2")

    def test_missing_or_inconsistent_order_fields_are_rejected(self):
        invalid_orders = (
            {**VALID_ORDER, "prescription": ""},
            {**VALID_ORDER, "slot": 3},
            {**VALID_ORDER, "door": 3},
            {**VALID_ORDER, "patient_id": "BN999"},
        )
        for order in invalid_orders:
            with self.subTest(order=order):
                with self.assertRaises(server.InvalidOrderDataError):
                    server.validate_order_data(order)

    def test_door_is_independent_from_k_prefix(self):
        result = server.validate_order_data({**VALID_ORDER, "door": 2})
        self.assertEqual(result["tray"], 1)
        self.assertEqual(result["door"], 2)

    def test_excel_requires_door_column_and_accepts_independent_door(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(server.REQUIRED_ORDER_COLUMNS)
            sheet.append(["K1_2", 2, "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"])
            workbook.save(path)
            orders = server.parse_excel_orders(path)
        self.assertEqual(orders[0]["door"], 2)
        self.assertEqual(orders[0]["dispense_status"], "pending_setup")

    def test_excel_missing_door_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.xlsx"
            headers = [column for column in server.REQUIRED_ORDER_COLUMNS if column != "Cửa"]
            path.write_bytes(
                make_orders_workbook(
                    [["K1_2", "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"]],
                    headers=headers,
                )
            )
            with self.assertRaises(ValueError) as caught:
                server.parse_excel_orders(path)
        self.assertIn("Thiếu cột bắt buộc: Cửa", str(caught.exception))

    def test_excel_rejects_invalid_door_duplicate_id_and_duplicate_position(self):
        scenarios = (
            (
                [["K1_2", 3, "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"]],
                "Cửa phải là 1 hoặc 2",
            ),
            (
                [
                    ["K1_2", 1, "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"],
                    ["K1_3", 2, "BN001", "Nguyễn Văn B", "B02", "Thuốc B", "Uống sáng"],
                ],
                "ID bệnh nhân 'BN001' bị trùng",
            ),
            (
                [
                    ["K1_2", 1, "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"],
                    ["K1_2", 2, "BN002", "Nguyễn Văn B", "B02", "Thuốc B", "Uống sáng"],
                ],
                "vị trí khay 'K1_2' bị trùng",
            ),
        )
        for rows, expected_error in scenarios:
            with self.subTest(expected_error=expected_error), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "orders.xlsx"
                path.write_bytes(make_orders_workbook(rows))
                with self.assertRaises(ValueError) as caught:
                    server.parse_excel_orders(path)
            self.assertIn(expected_error, str(caught.exception))

    def test_invalid_persisted_order_never_calls_arduino(self):
        invalid_order = {**VALID_ORDER, "prescription": ""}
        state = {
            "orders": [invalid_order],
            "setup_done": {"K1_2": True},
            "current_setup_slot": 1,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            orders_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server.arduino_manager, "send"
            ) as send:
                with running_server(server.RobotAssistantHandler) as base_url:
                    request = Request(
                        f"{base_url}/robot/api/medicine/dispense",
                        data=json.dumps({"patient_id": "BN001"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    response, payload = read_response(request)
        self.assertEqual(response.status, 500)
        self.assertEqual(payload["code"], "INVALID_ORDER_DATA")
        send.assert_not_called()

    def test_arduino_home_endpoint_uses_home_command(self):
        with mock.patch.object(server.arduino_manager, "home", return_value="DONE:HOME") as home, mock.patch.object(
            server.arduino_manager,
            "status",
            return_value={
                "configured": True,
                "connected": True,
                "connection_state": "connected",
                "door_states": [
                    {"door": 1, "state": "CLOSED"},
                    {"door": 2, "state": "CLOSED"},
                    {"door": 3, "state": "CLOSED"},
                ],
                "switches": {"A1": True, "A3": True, "A5": True},
            },
        ):
            with running_server(server.RobotAssistantHandler) as base_url:
                request = Request(
                    f"{base_url}/robot/api/arduino/home",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response, payload = read_response(request)

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["arduino"], "DONE:HOME")
        self.assertEqual(payload["status"]["door_states"][0]["state"], "CLOSED")
        home.assert_called_once_with()

    def test_supply_door_endpoint_is_locked_without_sending_serial_command(self):
        with mock.patch.object(server.arduino_manager, "send") as send:
            with running_server(server.RobotAssistantHandler) as base_url:
                request = Request(
                    f"{base_url}/robot/api/arduino/door",
                    data=json.dumps({"door": 3, "action": "OPEN"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    urlopen(request)
                except HTTPError as exc:
                    response = exc
                    payload = json.loads(exc.read().decode("utf-8"))

        self.assertEqual(response.status, 409)
        self.assertFalse(payload["ok"])
        self.assertIn("tạm khóa", payload["detail"])
        send.assert_not_called()

    def test_arduino_tray_calibrate_endpoint_returns_refreshed_status(self):
        calibrated_status = {
            "configured": True,
            "connected": True,
            "connection_state": "connected",
            "door_states": [
                {"door": 1, "state": "OPEN"},
                {"door": 2, "state": "CLOSED"},
                {"door": 3, "state": "CLOSED"},
            ],
            "tray_position": 1,
            "tray_calibrated": True,
            "tray_enabled": True,
            "tray_busy": False,
        }
        with mock.patch.object(server.dispense_coordinator, "require_no_active_session") as require_idle, mock.patch.object(
            server.dispense_coordinator, "hardware_status", return_value={
                "connected": True,
                "door_states": [{"door": 1, "state": "OPEN"}],
            }
        ) as hardware_status, mock.patch.object(
            server.arduino_manager, "calibrate_tray", return_value="DONE:CALIBRATE"
        ) as calibrate_tray, mock.patch.object(
            server.arduino_manager, "status", return_value=calibrated_status
        ) as status:
            with running_server(server.RobotAssistantHandler) as base_url:
                request = Request(
                    f"{base_url}/robot/api/arduino/tray/calibrate",
                    data=json.dumps({"slot": 1}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response, payload = read_response(request)

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["arduino"], "DONE:CALIBRATE")
        self.assertEqual(payload["status"]["tray_position"], 1)
        self.assertTrue(payload["status"]["tray_calibrated"])
        require_idle.assert_called_once_with()
        hardware_status.assert_called_once_with()
        calibrate_tray.assert_called_once_with()
        status.assert_called_once_with()

    def test_arduino_tray_release_endpoint_checks_safety_and_refreshes_status(self):
        released_status = {
            "connected": True,
            "door_states": [
                {"door": 1, "state": "OPEN"},
                {"door": 2, "state": "BETWEEN"},
                {"door": 3, "state": "CLOSED"},
            ],
            "tray_position": None,
            "tray_calibrated": False,
            "tray_enabled": False,
            "tray_busy": False,
        }
        with mock.patch.object(server.dispense_coordinator, "require_no_active_session") as require_idle, mock.patch.object(
            server.dispense_coordinator, "hardware_status", return_value={
                "connected": True,
                "door_states": released_status["door_states"],
            }
        ) as hardware_status, mock.patch.object(
            server.arduino_manager, "release_tray", return_value="DONE:TRAY_RELEASE"
        ) as release_tray, mock.patch.object(
            server.arduino_manager, "status", return_value=released_status
        ):
            with running_server(server.RobotAssistantHandler) as base_url:
                request = Request(
                    f"{base_url}/robot/api/arduino/tray/release",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response, payload = read_response(request)

        self.assertEqual(response.status, 200)
        self.assertFalse(payload["status"]["tray_enabled"])
        require_idle.assert_called_once_with()
        hardware_status.assert_called_once_with()
        release_tray.assert_called_once_with()

    def test_arduino_tray_calibrate_endpoint_is_blocked_by_active_session(self):
        busy_error = server.RobotWorkflowError("ROBOT_BUSY", "Robot đang có phiên cấp phát.")
        with mock.patch.object(
            server.dispense_coordinator, "require_no_active_session", side_effect=busy_error
        ) as require_idle, mock.patch.object(
            server.dispense_coordinator, "hardware_status"
        ) as hardware_status, mock.patch.object(server.arduino_manager, "calibrate_tray") as calibrate_tray:
            with running_server(server.RobotAssistantHandler) as base_url:
                request = Request(
                    f"{base_url}/robot/api/arduino/tray/calibrate",
                    data=json.dumps({"slot": 1}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response, payload = read_response(request)

        self.assertEqual(response.status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "ROBOT_BUSY")
        require_idle.assert_called_once_with()
        hardware_status.assert_not_called()
        calibrate_tray.assert_not_called()

    def test_orders_upload_is_blocked_when_session_or_doors_are_not_safe(self):
        class BlockingCoordinator:
            def __init__(self, error):
                self.error = error

            def require_no_active_session(self):
                if self.error == "session":
                    raise server.RobotWorkflowError("ROBOT_BUSY", "busy")

            def hardware_status(self, *, require_closed=False, require_calibrated=False):
                if self.error == "doors":
                    raise server.RobotWorkflowError("DOORS_NOT_CLOSED", "doors")
                return {"connected": True}

        upload_body = make_orders_workbook(
            [["K1_2", 1, "BN001", "Nguyễn Văn A", "B01", "Thuốc A", "Uống sau ăn"]]
        )
        for blocker, expected_code in (("session", "ROBOT_BUSY"), ("doors", "DOORS_NOT_CLOSED")):
            with self.subTest(blocker=blocker), tempfile.TemporaryDirectory() as temp_dir:
                with mock.patch.object(server, "dispense_coordinator", BlockingCoordinator(blocker)), mock.patch.object(
                    server, "MEDICINE_ORDERS_JSON", Path(temp_dir) / "orders.json"
                ), mock.patch.object(server, "CURRENT_ORDERS_XLSX", Path(temp_dir) / "current.xlsx"):
                    with running_server(server.RobotAssistantHandler) as base_url:
                        request = Request(
                            f"{base_url}/robot/api/medicine/orders/upload?filename=orders.xlsx",
                            data=upload_body,
                            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                            method="POST",
                        )
                        response, payload = read_response(request)

            self.assertEqual(response.status, 409)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["code"], expected_code)

    def test_dispense_api_returns_structured_workflow_errors(self):
        class ErrorCoordinator:
            def __init__(self, code):
                self.code = code

            def begin(self, patient_id):
                status = HTTPStatus.BAD_GATEWAY if self.code == "HARDWARE_TIMEOUT" else HTTPStatus.CONFLICT
                raise server.RobotWorkflowError(self.code, f"detail for {self.code}", status)

        expected_status = {
            "ORDER_NOT_READY": 409,
            "ORDER_ALREADY_DISPENSED": 409,
            "TRAY_NOT_CALIBRATED": 409,
            "ROBOT_BUSY": 409,
            "DOORS_NOT_CLOSED": 409,
            "DISPENSE_INTERRUPTED": 409,
            "HARDWARE_TIMEOUT": 502,
        }
        for code, status in expected_status.items():
            with self.subTest(code=code), mock.patch.object(server, "dispense_coordinator", ErrorCoordinator(code)):
                with running_server(server.RobotAssistantHandler) as base_url:
                    request = Request(
                        f"{base_url}/robot/api/medicine/dispense",
                        data=json.dumps({"patient_id": "BN001"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    response, payload = read_response(request)

            self.assertEqual(response.status, status, f"{code}: {payload}")
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["code"], code)


class ConfigurationAndHeaderTests(unittest.TestCase):
    def test_gemini_live_instructions_define_bilingual_session_lock(self):
        instructions = server.build_gemini_live_instructions()

        self.assertIn("trợ lý voice song ngữ Việt-Anh", instructions)
        self.assertIn("phát ngôn có ý nghĩa đầu tiên", instructions)
        self.assertIn("mặc định khóa tiếng Việt", instructions)
        self.assertIn("chỉ đổi khi người dùng yêu cầu rõ ràng", instructions)
        self.assertIn("tham số query gửi vào tool phải là tiếng Việt", instructions)
        self.assertIn("chỉ được dịch sang ngôn ngữ đang khóa", instructions)

    def test_gemini_live_tool_queries_require_vietnamese_lookup_text(self):
        rag_description = server.gemini_rag_function_declaration()["parameters"]["properties"]["query"][
            "description"
        ]
        pharmacity_description = server.gemini_pharmacity_function_declaration()["parameters"]["properties"][
            "query"
        ]["description"]

        self.assertIn("dịch câu hỏi sang tiếng Việt", rag_description)
        self.assertIn("giữ nguyên tên riêng", rag_description)
        self.assertIn("dịch câu hỏi sang tiếng Việt", pharmacity_description)
        self.assertIn("giữ nguyên tên thuốc", pharmacity_description)

    def test_frontend_voice_greeting_precedes_connection_and_gates_microphone(self):
        app_source = (server.WEB_DIR / "app.js").read_text(encoding="utf-8")
        open_voice_body = app_source.split("async function openVoiceMode()", 1)[1].split(
            "function closeVoiceMode()", 1
        )[0]

        self.assertLess(open_voice_body.index("startVoiceGreeting();"), open_voice_body.index("startGeminiLiveVoice()"))
        self.assertIn('const VOICE_GREETING_AUDIO_URL = "/assets/audio/greeting-vi-en.mp3";', app_source)
        self.assertIn("!state.geminiLiveReady || !state.voiceGreetingFinished", app_source)
        self.assertNotIn("maybePlayVoiceGreeting", app_source)
        self.assertNotIn("VOICE_GREETING_TEXT", app_source)

    def test_env_file_does_not_override_process_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("ROBOT_APP_PORT=8123\nNEW_TEST_SETTING=from-file\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"ROBOT_APP_PORT": "9000"}, clear=False):
                os.environ.pop("NEW_TEST_SETTING", None)
                server.load_env_file(env_path)
                self.assertEqual(os.environ["ROBOT_APP_PORT"], "9000")
                self.assertEqual(os.environ["NEW_TEST_SETTING"], "from-file")
                os.environ.pop("NEW_TEST_SETTING", None)

    def test_legacy_process_port_beats_namespaced_env_file_value(self):
        env = dict(os.environ)
        env.pop("ROBOT_APP_PORT", None)
        env["PORT"] = "9123"
        result = subprocess.run(
            [sys.executable, "-c", "import server; print(server.main_server_address()[1])"],
            cwd=Path(__file__).resolve().parent,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "9123")

    def test_main_server_security_and_sensitive_cache_headers(self):
        with running_server(server.RobotAssistantHandler) as base_url:
            root_response = urlopen(f"{base_url}/", timeout=5)
            request = Request(
                f"{base_url}/robot/api/medicine/lookup",
                data=json.dumps({"patient_id": "missing"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            medicine_response, _payload = read_response(request)

        self.assertIn("default-src 'self'", root_response.headers["Content-Security-Policy"])
        self.assertEqual(root_response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(root_response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", medicine_response.headers["Cache-Control"])
        self.assertEqual(medicine_response.headers["Pragma"], "no-cache")

    def test_pharmacity_server_security_headers(self):
        with running_server(pharmacity_server.PharmacityChatbotHandler) as base_url:
            response = urlopen(f"{base_url}/", timeout=5)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")


class FakeArduinoSerial:
    instances = []

    def __init__(self, port, baud_rate, *, timeout=None, write_timeout=None):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.is_open = True
        self.writes = []
        self.lines = [b"READY:BOOTING\n", b"READY\n"]
        FakeArduinoSerial.instances.append(self)

    def readline(self):
        if self.lines:
            return self.lines.pop(0)
        time.sleep(0.01)
        return b""

    def write(self, data):
        command = data.decode("utf-8").strip()
        self.writes.append(command)
        if command == "HOME":
            self.lines.append(b"DONE:HOME\n")
        elif command == "CALIBRATE:1":
            self.lines.append(b"DONE:CALIBRATE\n")
        elif command == "STATUS":
            if "CALIBRATE:1" in self.writes:
                self.lines.append(b"STATUS:D1=CLOSED,D2=CLOSED,D3=CLOSED,A0=0,A1=1,A2=0,A3=1,A4=0,A5=1,T=1,TCAL=1,TEN=1,TBUSY=0\n")
            else:
                self.lines.append(b"STATUS:D1=CLOSED,D2=OPEN,D3=BETWEEN,A0=0,A1=1,A2=1,A3=0,A4=0,A5=0,T=UNKNOWN,TCAL=0,TEN=0,TBUSY=0\n")
        elif command == "TRAY:RELEASE":
            self.lines.append(b"DONE:TRAY_RELEASE\n")
        elif command in {"DOOR:1:CLOSE", "DOOR:2:CLOSE"}:
            self.lines.append(b"DONE:DOOR\n")
        elif command == "DOOR:1:OPEN":
            self.lines.extend([b"READY\n", b"DONE:DOOR\n"])
        elif command == "PING":
            self.lines.append(b"DONE:PONG\n")
        else:
            self.lines.append(b"ERROR:unknown command\n")

    def flush(self):
        pass

    def reset_input_buffer(self):
        pass

    def close(self):
        self.is_open = False


class ArduinoManagerTests(unittest.TestCase):
    def setUp(self):
        FakeArduinoSerial.instances.clear()

    def test_env_port_overrides_saved_settings_and_baud_is_fixed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "arduino_settings.json"
            settings_path.write_text(
                json.dumps({"port": "COM2", "baud_rate": 96000, "timeout_ms": 3000}),
                encoding="utf-8",
            )
            with mock.patch.object(server, "ARDUINO_SETTINGS_JSON", settings_path), mock.patch.dict(
                os.environ,
                {"ARDUINO_PORT": "COM9", "ARDUINO_TIMEOUT_MS": "31000"},
                clear=False,
            ):
                manager = server.ArduinoManager()
                settings = manager.settings()

        self.assertEqual(settings["port"], "COM9")
        self.assertEqual(settings["baud_rate"], 9600)
        self.assertEqual(settings["timeout_ms"], 31000)
        self.assertEqual(settings["settings_source"], "env")

    def test_home_parses_status_after_boot(self):
        fake_serial_module = SimpleNamespace(Serial=FakeArduinoSerial)
        with mock.patch.dict(sys.modules, {"serial": fake_serial_module}), mock.patch.dict(
            os.environ,
            {"ARDUINO_PORT": "COM7", "ARDUINO_TIMEOUT_MS": "30000"},
            clear=False,
        ):
            manager = server.ArduinoManager()
            response = manager.home()
            status = manager.status()

        fake = FakeArduinoSerial.instances[0]
        self.assertEqual(fake.port, "COM7")
        self.assertEqual(fake.baud_rate, 9600)
        self.assertEqual(response, "DONE:HOME")
        self.assertEqual(fake.writes[:3], ["DOOR:1:CLOSE", "DOOR:2:CLOSE", "STATUS"])
        self.assertTrue(status["connected"])
        self.assertEqual(status["door_states"][0]["state"], "CLOSED")
        self.assertEqual(status["door_states"][1]["state"], "OPEN")
        self.assertTrue(status["switches"]["A1"])
        self.assertIsNone(status["tray_position"])
        self.assertFalse(status["tray_calibrated"])
        self.assertFalse(status["tray_enabled"])

    def test_supply_door_status_is_always_simulated_closed(self):
        manager = server.ArduinoManager()
        for raw_state in ("OPEN", "BETWEEN", "CONFLICT", ""):
            suffix = f"D3={raw_state}," if raw_state else ""
            manager._parse_status_line(
                f"STATUS:D1=OPEN,D2=BETWEEN,{suffix}A4=1,A5=0,T=1,TCAL=1,TEN=1,TBUSY=0"
            )
            status = manager.status()
            self.assertEqual(status["door_states"][0]["state"], "OPEN")
            self.assertEqual(status["door_states"][1]["state"], "BETWEEN")
            self.assertEqual(status["door_states"][2]["state"], "CLOSED")
            self.assertTrue(status["switches"]["A4"])
            self.assertFalse(status["switches"]["A5"])

    def test_calibration_is_not_ready_when_enable_signal_is_off(self):
        manager = server.ArduinoManager()
        manager._parse_status_line("STATUS:D1=CLOSED,D2=CLOSED,D3=CLOSED,T=1,TCAL=1,TEN=0,TBUSY=0")
        status = manager.status()
        self.assertFalse(status["tray_calibrated"])
        self.assertFalse(status["tray_enabled"])

    def test_calibrate_tray_sends_command_and_refreshes_status(self):
        fake_serial_module = SimpleNamespace(Serial=FakeArduinoSerial)
        with mock.patch.dict(sys.modules, {"serial": fake_serial_module}), mock.patch.dict(
            os.environ,
            {"ARDUINO_PORT": "COM7", "ARDUINO_TIMEOUT_MS": "30000"},
            clear=False,
        ):
            manager = server.ArduinoManager()
            response = manager.calibrate_tray()
            status = manager.status()

        fake = FakeArduinoSerial.instances[0]
        self.assertEqual(response, "DONE:CALIBRATE")
        self.assertEqual(fake.writes[:2], ["CALIBRATE:1", "STATUS"])
        self.assertEqual(status["tray_position"], 1)
        self.assertTrue(status["tray_calibrated"])
        self.assertTrue(all(item["state"] == "CLOSED" for item in status["door_states"]))


class FakeCoordinatorManager:
    def __init__(self, *, connected=True, calibrated=True, doors_closed=True, fail_close=False):
        self.commands = []
        self.connected = connected
        self.calibrated = calibrated
        self.doors_closed = doors_closed
        self.fail_close = fail_close

    def status(self, *, refresh=False):
        door_state = "CLOSED" if self.doors_closed else "OPEN"
        return {
            "connected": self.connected,
            "tray_calibrated": self.calibrated,
            "tray_enabled": self.calibrated,
            "door_states": [
                {"door": 1, "state": door_state},
                {"door": 2, "state": "CLOSED"},
                {"door": 3, "state": "CLOSED"},
            ],
        }

    def send(self, command, *, timeout_ms=None):
        self.commands.append(command)
        if command.startswith("DISPENSE:"):
            return "DONE:DISPENSE"
        if command.startswith("DOOR:") and self.fail_close:
            raise TimeoutError("close timeout")
        return "DONE:DOOR"

    def home(self):
        self.commands.append("HOME")
        return "DONE:HOME"


class DispenseCoordinatorTests(unittest.TestCase):
    def write_orders_state(self, path, orders):
        path.write_text(json.dumps({"orders": orders}, ensure_ascii=False), encoding="utf-8")

    def test_single_session_manual_close_and_repeat_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            runtime_path = Path(temp_dir) / "runtime.json"
            self.write_orders_state(orders_path, [{**VALID_ORDER, "door": 2, "dispense_status": "ready"}])
            manager = FakeCoordinatorManager()
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server, "ROBOT_RUNTIME_JSON", runtime_path
            ):
                coordinator = server.DispenseCoordinator(manager)
                order, session, _response = coordinator.begin("BN001")
                self.assertEqual(order["door"], 2)
                self.assertEqual(session["status"], "open")
                self.assertEqual(manager.commands[0], "DISPENSE:2:2")
                opened_at = server.datetime.fromisoformat(session["opened_at"])
                auto_close_at = server.datetime.fromisoformat(session["auto_close_at"])
                self.assertEqual((auto_close_at - opened_at).total_seconds(), 30)

                closed_order, closed_session, _response = coordinator.complete(session["id"], source="patient")
                self.assertEqual(closed_order["dispense_status"], "dispensed")
                self.assertEqual(closed_session["close_source"], "patient")
                repeated_order, repeated_session, repeated_response = coordinator.complete(session["id"], source="timeout")
                self.assertEqual(repeated_order["dispense_status"], "dispensed")
                self.assertEqual(repeated_session["close_source"], "patient")
                self.assertEqual(repeated_response, "DONE:DOOR")
                with self.assertRaises(server.RobotWorkflowError) as caught:
                    coordinator.begin("BN001")
                self.assertEqual(caught.exception.code, "ORDER_ALREADY_DISPENSED")

    def test_order_must_be_setup_before_dispense(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            runtime_path = Path(temp_dir) / "runtime.json"
            self.write_orders_state(orders_path, [{**VALID_ORDER, "setup_done": False, "dispense_status": "pending_setup"}])
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server, "ROBOT_RUNTIME_JSON", runtime_path
            ):
                coordinator = server.DispenseCoordinator(FakeCoordinatorManager())
                with self.assertRaises(server.RobotWorkflowError) as caught:
                    coordinator.begin("BN001")
                self.assertEqual(caught.exception.code, "ORDER_NOT_READY")

    def test_hardware_gates_cover_calibration_connection_and_door_state(self):
        scenarios = (
            (FakeCoordinatorManager(calibrated=False), "TRAY_NOT_CALIBRATED"),
            (FakeCoordinatorManager(connected=False), "HARDWARE_TIMEOUT"),
            (FakeCoordinatorManager(doors_closed=False), "DOORS_NOT_CLOSED"),
        )
        for manager, expected_code in scenarios:
            with self.subTest(expected_code=expected_code), tempfile.TemporaryDirectory() as temp_dir:
                orders_path = Path(temp_dir) / "orders.json"
                runtime_path = Path(temp_dir) / "runtime.json"
                self.write_orders_state(orders_path, [{**VALID_ORDER, "dispense_status": "ready"}])
                with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                    server, "ROBOT_RUNTIME_JSON", runtime_path
                ):
                    coordinator = server.DispenseCoordinator(manager)
                    with self.assertRaises(server.RobotWorkflowError) as caught:
                        coordinator.begin("BN001")
            self.assertEqual(caught.exception.code, expected_code)

    def test_watchdog_auto_close_marks_order_dispensed_after_deadline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            runtime_path = Path(temp_dir) / "runtime.json"
            self.write_orders_state(orders_path, [{**VALID_ORDER, "dispense_status": "ready"}])
            manager = FakeCoordinatorManager()
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server, "ROBOT_RUNTIME_JSON", runtime_path
            ), mock.patch.object(server, "DISPENSE_OPEN_SECONDS", -1):
                coordinator = server.DispenseCoordinator(manager)
                _order, session, _response = coordinator.begin("BN001")
                coordinator._watchdog_tick()
                final_session = coordinator.status(session["id"])
                final_order = server.find_order_by_patient_id("BN001")

        self.assertEqual(final_session["status"], "completed")
        self.assertEqual(final_session["close_source"], "timeout")
        self.assertEqual(final_order["dispense_status"], "dispensed")
        self.assertIn("DOOR:1:CLOSE", manager.commands)

    def test_restart_marks_active_session_interrupted_and_homes_robot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            runtime_path = Path(temp_dir) / "runtime.json"
            self.write_orders_state(orders_path, [{**VALID_ORDER, "dispense_status": "dispensing"}])
            runtime_path.write_text(
                json.dumps(
                    {
                        "session": {
                            "id": "session-1",
                            "patient_id": "BN001",
                            "slot": 2,
                            "door": 1,
                            "status": "open",
                            "opened_at": server.iso_utc(),
                            "auto_close_at": server.iso_utc(server.utc_now() + server.timedelta(seconds=30)),
                        }
                    }
                ),
                encoding="utf-8",
            )
            manager = FakeCoordinatorManager()
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server, "ROBOT_RUNTIME_JSON", runtime_path
            ):
                coordinator = server.DispenseCoordinator(manager)
                coordinator._recover_interrupted_session()
                session = coordinator.status("session-1")
                order = server.find_order_by_patient_id("BN001")

        self.assertEqual(session["status"], "interrupted")
        self.assertEqual(order["dispense_status"], "interrupted")
        self.assertIn("HOME", manager.commands)

    def test_close_failure_marks_interrupted_and_does_not_mark_dispensed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            orders_path = Path(temp_dir) / "orders.json"
            runtime_path = Path(temp_dir) / "runtime.json"
            self.write_orders_state(orders_path, [{**VALID_ORDER, "dispense_status": "ready"}])
            manager = FakeCoordinatorManager(fail_close=True)
            with mock.patch.object(server, "MEDICINE_ORDERS_JSON", orders_path), mock.patch.object(
                server, "ROBOT_RUNTIME_JSON", runtime_path
            ):
                coordinator = server.DispenseCoordinator(manager)
                _order, session, _response = coordinator.begin("BN001")
                with self.assertRaises(server.RobotWorkflowError) as caught:
                    coordinator.complete(session["id"], source="patient")
                interrupted_session = coordinator.status(session["id"])
                interrupted_order = server.find_order_by_patient_id("BN001")

        self.assertEqual(caught.exception.code, "DOOR_CLOSE_FAILED")
        self.assertEqual(interrupted_session["status"], "interrupted")
        self.assertEqual(interrupted_order["dispense_status"], "interrupted")
        self.assertIsNone(interrupted_order["dispensed_at"])

    def test_ready_line_is_not_treated_as_door_response(self):
        fake_serial_module = SimpleNamespace(Serial=FakeArduinoSerial)
        with mock.patch.dict(sys.modules, {"serial": fake_serial_module}), mock.patch.dict(
            os.environ,
            {"ARDUINO_PORT": "COM8", "ARDUINO_TIMEOUT_MS": "30000"},
            clear=False,
        ):
            manager = server.ArduinoManager()
            response = manager.send("DOOR:1:OPEN")

        self.assertEqual(response, "DONE:DOOR")
        self.assertIn("DOOR:1:OPEN", FakeArduinoSerial.instances[-1].writes)


if __name__ == "__main__":
    unittest.main()
