#include <AccelStepper.h>
#include <math.h>

// ---------------- CHÂN KẾT NỐI ----------------
const byte DIR_PIN  = 2;
const byte STEP_PIN = 3;

// ---------------- THÔNG SỐ CƠ KHÍ ----------------
// Thay 10.0 bằng tỉ số truyền X thực tế của bạn.
// Ví dụ cơ cấu 10:1 thì đặt 10.0.
const float GEAR_RATIO_X = 2.30;

// Driver đang đặt 1/8 bước = 1600 xung/vòng motor.
const long MOTOR_PULSES_PER_REV = 1600;

// Thông số chạy thử an toàn với nguồn 12V.
// Có thể tăng dần sau khi hệ thống chạy ổn định.
const float MAX_SPEED    = 800.0;  // xung/giây
const float ACCELERATION = 400.0;  // xung/giây^2

// Common-anode làm tín hiệu STEP tác động mức LOW.
const bool DIR_INVERT  = true;
const bool STEP_INVERT = true;

// Chế độ STEP/DIR.
AccelStepper stepper(
  AccelStepper::DRIVER,
  STEP_PIN,
  DIR_PIN
);

long pulsesPerSystemRevolution;

byte currentTray = 1;
byte targetTray  = 1;
bool isMoving    = false;

// Vị trí xung của từng khay trong một vòng.
// Khay 1 = 0; khay 2 = 1/8 vòng; ... khay 8 = 7/8 vòng.
long trayPulsePosition(byte tray)
{
  int64_t numerator =
      (int64_t)(tray - 1) * pulsesPerSystemRevolution;

  // Làm tròn về xung gần nhất.
  return (long)((numerator + 4) / 8);
}

void moveToTray(byte requestedTray)
{
  if (requestedTray < 1 || requestedTray > 8) {
    Serial.println(F("ERROR: Chỉ chấp nhận K1 đến K8"));
    return;
  }

  // Trong phiên bản này, không nhận lệnh mới khi đang chạy.
  if (isMoving) {
    Serial.println(F("BUSY: Hệ thống đang di chuyển"));
    return;
  }

  if (requestedTray == currentTray) {
    Serial.print(F("Đã ở khay "));
    Serial.println(currentTray);
    return;
  }

  long currentMark = trayPulsePosition(currentTray);
  long targetMark  = trayPulsePosition(requestedTray);

  // Chỉ quay một chiều cố định.
  long deltaPulses = targetMark - currentMark;

  // Nếu vị trí đích nằm phía trước điểm 0,
  // đi tiếp qua khay 1 thay vì đảo chiều.
  if (deltaPulses <= 0) {
    deltaPulses += pulsesPerSystemRevolution;
  }

  targetTray = requestedTray;
  isMoving = true;

  // Di chuyển tương đối theo chiều dương duy nhất.
  stepper.move(deltaPulses);

  Serial.print(F("Di chuyển từ K"));
  Serial.print(currentTray);
  Serial.print(F(" đến K"));
  Serial.print(targetTray);
  Serial.print(F(", số xung = "));
  Serial.println(deltaPulses);
}

void readSerialCommand()
{
  static bool receivedK = false;

  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == 'k' || c == 'K') {
      receivedK = true;
    }
    else if (receivedK && c >= '1' && c <= '8') {
      moveToTray(c - '0');
      receivedK = false;
    }
    else if (c == '\r' || c == '\n' || c == ' ') {
      // Bỏ qua ký tự xuống dòng và khoảng trắng.
    }
    else {
      receivedK = false;
    }
  }
}

void setup()
{
  Serial.begin(9600);

  // 1600 xung/vòng motor × tỉ số truyền X.
  pulsesPerSystemRevolution =
      lround((float)MOTOR_PULSES_PER_REV * GEAR_RATIO_X);

  if (pulsesPerSystemRevolution <= 0) {
    Serial.println(F("ERROR: GEAR_RATIO_X không hợp lệ"));
    while (true) {
      // Dừng chương trình.
    }
  }

  stepper.setPinsInverted(
    DIR_INVERT,
    STEP_INVERT,
    false
  );

  // Xung đủ dài cho ngõ vào cách ly quang của driver.
  stepper.setMinPulseWidth(20);
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(ACCELERATION);

  // Khi bật nguồn, vị trí hiện tại được coi là khay 1.
  stepper.setCurrentPosition(0);
  currentTray = 1;
  targetTray  = 1;

  Serial.println(F("SYSTEM READY"));
  Serial.println(F("Hãy chắc chắn bàn đang ở khay 1."));
  Serial.println(F("Nhập K1 ... K8 để chọn khay."));
  Serial.print(F("Xung cho một vòng hệ thống: "));
  Serial.println(pulsesPerSystemRevolution);
}

void loop()
{
  readSerialCommand();

  // Phải gọi liên tục để tạo xung và tăng/giảm tốc.
  stepper.run();

  if (isMoving && stepper.distanceToGo() == 0) {
    currentTray = targetTray;
    isMoving = false;

    Serial.print(F("DONE: Đã đến khay "));
    Serial.println(currentTray);
  }
}