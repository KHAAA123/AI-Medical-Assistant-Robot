#include <AccelStepper.h>
#include <math.h>

// ================= DONG CO BUOC XOAY KHAY =================
const byte DIR_PIN = 2;
const byte STEP_PIN = 3;
const byte STEPPER_ENABLE_PIN = 4;

// Dau common-anode: ENA+ -> 5V, ENA- -> D4. Doi hang nay neu module dao logic.
const byte STEPPER_ENABLE_ACTIVE_LEVEL = HIGH;

const float GEAR_RATIO_X = 2.30;
const long MOTOR_PULSES_PER_REV = 1600;
const float MAX_SPEED = 800.0;
const float ACCELERATION = 400.0;

// Driver common-anode: STEP tac dong muc LOW.
const bool DIR_INVERT = true;
const bool STEP_INVERT = true;

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

long pulsesPerSystemRevolution = 0;
byte currentTray = 1;
byte targetTray = 1;
bool trayIsMoving = false;
bool trayCalibrated = false;
bool trayEnabled = false;

enum TrayOperation {
  TRAY_OPERATION_NONE,
  TRAY_OPERATION_MOVE,
  TRAY_OPERATION_DISPENSE
};

TrayOperation pendingTrayOperation = TRAY_OPERATION_NONE;
byte pendingDispenseDoor = 0;

// ================= DONG CO DC VA CTHT CUA =================
#define CTHT1 A0   // Mo cua 1
#define CTHT2 A1   // Dong cua 1
#define CTHT3 A2   // Mo cua 2
#define CTHT4 A3   // Dong cua 2
#define CTHT5 A4   // Mo cua vat tu y te
#define CTHT6 A5   // Dong cua vat tu y te

#define PRESSED_STATE LOW

#define IN1 5
#define IN2 6
#define IN3 9
#define IN4 10
#define IN5 11
#define IN6 12

#define MOTOR_SPEED 250

const unsigned long DOOR_TIMEOUT_MS = 15000;

enum DoorState {
  DOOR_CLOSED,
  DOOR_OPEN,
  DOOR_BETWEEN,
  DOOR_CONFLICT
};

// ================= BO DEM LENH SERIAL =================
const byte MAX_COMMAND_LENGTH = 63;
String serialCommand;

void enableTrayDriver() {
  digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_LEVEL);
  trayEnabled = true;
}

void disableTrayDriver() {
  digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_LEVEL == HIGH ? LOW : HIGH);
  trayEnabled = false;
}

// ================= HAM DIEU KHIEN CUA =================
void motor1Forward() {
  analogWrite(IN1, MOTOR_SPEED);
  digitalWrite(IN2, LOW);
}

void motor1Reverse() {
  digitalWrite(IN1, LOW);
  analogWrite(IN2, MOTOR_SPEED);
}

void motor1Stop() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

void motor2Forward() {
  analogWrite(IN3, MOTOR_SPEED);
  digitalWrite(IN4, LOW);
}

void motor2Reverse() {
  digitalWrite(IN3, LOW);
  analogWrite(IN4, MOTOR_SPEED);
}

void motor2Stop() {
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void motor3Forward() {
  analogWrite(IN5, MOTOR_SPEED);
  digitalWrite(IN6, LOW);
}

void motor3Reverse() {
  digitalWrite(IN5, LOW);
  digitalWrite(IN6, HIGH);
}

void motor3Stop() {
  digitalWrite(IN5, LOW);
  digitalWrite(IN6, LOW);
}

bool isSwitchPressed(int switchPin) {
  return digitalRead(switchPin) == PRESSED_STATE;
}

int openSwitchForDoor(int door) {
  if (door == 1) return CTHT1;
  if (door == 2) return CTHT3;
  if (door == 3) return CTHT5;
  return -1;
}

int closeSwitchForDoor(int door) {
  if (door == 1) return CTHT2;
  if (door == 2) return CTHT4;
  if (door == 3) return CTHT6;
  return -1;
}

DoorState getDoorState(int door) {
  if (door == 3) return DOOR_CLOSED; // Cua vat tu dang tam khoa.
  int openSwitch = openSwitchForDoor(door);
  int closeSwitch = closeSwitchForDoor(door);
  if (openSwitch < 0 || closeSwitch < 0) {
    return DOOR_CONFLICT;
  }

  bool openPressed = isSwitchPressed(openSwitch);
  bool closePressed = isSwitchPressed(closeSwitch);

  if (openPressed && closePressed) return DOOR_CONFLICT;
  if (closePressed) return DOOR_CLOSED;
  if (openPressed) return DOOR_OPEN;
  return DOOR_BETWEEN;
}

const char *doorStateName(DoorState state) {
  if (state == DOOR_CLOSED) return "CLOSED";
  if (state == DOOR_OPEN) return "OPEN";
  if (state == DOOR_BETWEEN) return "BETWEEN";
  return "CONFLICT";
}

bool allDoorsClosed() {
  for (int door = 1; door <= 3; door++) {
    if (getDoorState(door) != DOOR_CLOSED) {
      return false;
    }
  }
  return true;
}

void stopDoor(int door) {
  if (door == 1) motor1Stop();
  if (door == 2) motor2Stop();
  if (door == 3) motor3Stop();
}

void forwardDoor(int door) {
  if (door == 1) motor1Forward();
  if (door == 2) motor2Forward();
  if (door == 3) motor3Forward();
}

void reverseDoor(int door) {
  if (door == 1) motor1Reverse();
  if (door == 2) motor2Reverse();
  if (door == 3) motor3Reverse();
}

bool ensureDoorCanMove(int door) {
  if (door < 1 || door > 3) {
    Serial.println(F("ERROR:door must be 1, 2 or 3"));
    return false;
  }
  if (door == 3) {
    stopDoor(door);
    Serial.println(F("ERROR:supply door temporarily locked"));
    return false;
  }

  DoorState state = getDoorState(door);
  if (state == DOOR_CONFLICT) {
    Serial.print(F("ERROR:door "));
    Serial.print(door);
    Serial.println(F(" switch conflict"));
    stopDoor(door);
    return false;
  }
  return true;
}

void printStatus() {
  Serial.print(F("STATUS:"));
  Serial.print(F("D1="));
  Serial.print(doorStateName(getDoorState(1)));
  Serial.print(F(",D2="));
  Serial.print(doorStateName(getDoorState(2)));
  Serial.print(F(",D3="));
  Serial.print(doorStateName(getDoorState(3)));
  Serial.print(F(",A0="));
  Serial.print(isSwitchPressed(CTHT1) ? 1 : 0);
  Serial.print(F(",A1="));
  Serial.print(isSwitchPressed(CTHT2) ? 1 : 0);
  Serial.print(F(",A2="));
  Serial.print(isSwitchPressed(CTHT3) ? 1 : 0);
  Serial.print(F(",A3="));
  Serial.print(isSwitchPressed(CTHT4) ? 1 : 0);
  Serial.print(F(",A4="));
  Serial.print(isSwitchPressed(CTHT5) ? 1 : 0);
  Serial.print(F(",A5="));
  Serial.print(isSwitchPressed(CTHT6) ? 1 : 0);
  Serial.print(F(",T="));
  if (trayCalibrated) {
    Serial.print(currentTray);
  } else {
    Serial.print(F("UNKNOWN"));
  }
  Serial.print(F(",TCAL="));
  Serial.print(trayCalibrated ? 1 : 0);
  Serial.print(F(",TEN="));
  Serial.print(trayEnabled ? 1 : 0);
  Serial.print(F(",TBUSY="));
  Serial.println(trayIsMoving ? 1 : 0);
}

bool waitForSwitch(int switchPin, int door, const char *errorMessage) {
  unsigned long startedAt = millis();
  while (digitalRead(switchPin) != PRESSED_STATE) {
    if (millis() - startedAt > DOOR_TIMEOUT_MS) {
      stopDoor(door);
      Serial.print(F("ERROR:"));
      Serial.println(errorMessage);
      return false;
    }
  }
  stopDoor(door);
  return true;
}

bool openDoor(int door) {
  if (!ensureDoorCanMove(door)) {
    return false;
  }

  DoorState state = getDoorState(door);
  if (state == DOOR_OPEN) {
    stopDoor(door);
    return true;
  }

  reverseDoor(door);
  if (door == 1) return waitForSwitch(CTHT1, door, "door 1 open timeout");
  if (door == 2) return waitForSwitch(CTHT3, door, "door 2 open timeout");
  return waitForSwitch(CTHT5, door, "door 3 open timeout");
}

bool closeDoor(int door) {
  if (!ensureDoorCanMove(door)) {
    return false;
  }

  DoorState state = getDoorState(door);
  if (state == DOOR_CLOSED) {
    stopDoor(door);
    return true;
  }

  forwardDoor(door);
  if (door == 1) return waitForSwitch(CTHT2, door, "door 1 close timeout");
  if (door == 2) return waitForSwitch(CTHT4, door, "door 2 close timeout");
  return waitForSwitch(CTHT6, door, "door 3 close timeout");
}

bool closeAllDoorsOnStartup() {
  for (int door = 1; door <= 2; door++) {
    if (!closeDoor(door)) {
      return false;
    }
  }
  return true;
}

// ================= HAM DIEU KHIEN KHAY =================
long trayPulsePosition(byte tray) {
  int64_t numerator = (int64_t)(tray - 1) * pulsesPerSystemRevolution;
  return (long)((numerator + 4) / 8);
}

void finishTrayOperation() {
  currentTray = targetTray;
  stepper.setCurrentPosition(trayPulsePosition(currentTray));
  trayIsMoving = false;

  TrayOperation completedOperation = pendingTrayOperation;
  byte dispenseDoor = pendingDispenseDoor;
  pendingTrayOperation = TRAY_OPERATION_NONE;
  pendingDispenseDoor = 0;

  if (completedOperation == TRAY_OPERATION_MOVE) {
    Serial.println(F("DONE:TRAY"));
    return;
  }

  if (completedOperation == TRAY_OPERATION_DISPENSE) {
    if (openDoor(dispenseDoor)) {
      Serial.println(F("DONE:DISPENSE"));
    }
  }
}

bool startTrayOperation(int requestedTray, TrayOperation operation, int dispenseDoor) {
  if (requestedTray < 1 || requestedTray > 8) {
    Serial.println(F("ERROR:slot must be 1-8"));
    return false;
  }

  if (operation == TRAY_OPERATION_DISPENSE && (dispenseDoor < 1 || dispenseDoor > 2)) {
    Serial.println(F("ERROR:supply door temporarily locked"));
    return false;
  }

  if (!trayCalibrated || !trayEnabled) {
    Serial.println(F("ERROR:tray not calibrated or enabled"));
    return false;
  }

  if (!allDoorsClosed()) {
    Serial.println(F("ERROR:doors not closed"));
    return false;
  }

  byte requestedTrayNumber = (byte)requestedTray;
  byte dispenseDoorNumber = (byte)dispenseDoor;
  long currentMark = trayPulsePosition(currentTray);
  long targetMark = trayPulsePosition(requestedTrayNumber);
  long deltaPulses = targetMark - currentMark;

  // Khay chi quay mot chieu; neu dich nam qua moc 0 thi tiep tuc di toi.
  if (deltaPulses <= 0 && requestedTrayNumber != currentTray) {
    deltaPulses += pulsesPerSystemRevolution;
  }

  targetTray = requestedTrayNumber;
  pendingTrayOperation = operation;
  pendingDispenseDoor = dispenseDoorNumber;

  if (requestedTrayNumber == currentTray) {
    finishTrayOperation();
    return true;
  }

  trayIsMoving = true;
  stepper.move(deltaPulses);
  return true;
}

void runTray() {
  if (!trayIsMoving) {
    return;
  }

  stepper.run();
  if (stepper.distanceToGo() == 0) {
    finishTrayOperation();
  }
}

// ================= XU LY LENH SERIAL =================
void handleDoorCommand(const String &command) {
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  if (secondColon < 0) {
    Serial.println(F("ERROR:invalid door command"));
    return;
  }

  int door = command.substring(firstColon + 1, secondColon).toInt();
  if (door == 3) {
    Serial.println(F("ERROR:supply door temporarily locked"));
    return;
  }
  String action = command.substring(secondColon + 1);
  bool ok = false;

  if (action == "OPEN") {
    ok = openDoor(door);
  } else if (action == "CLOSE") {
    ok = closeDoor(door);
  } else {
    Serial.println(F("ERROR:door action must be OPEN or CLOSE"));
    return;
  }

  if (ok) {
    Serial.println(F("DONE:DOOR"));
  }
}

void handleDispenseCommand(const String &command) {
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  if (secondColon < 0) {
    Serial.println(F("ERROR:invalid dispense command"));
    return;
  }

  int slot = command.substring(firstColon + 1, secondColon).toInt();
  int door = command.substring(secondColon + 1).toInt();
  startTrayOperation(slot, TRAY_OPERATION_DISPENSE, door);
}

void handleCommand(String command) {
  if (trayIsMoving) {
    if (command == "PING") {
      Serial.println(F("DONE:PONG"));
    } else if (command == "STATUS") {
      printStatus();
    } else {
      Serial.println(F("ERROR:busy"));
    }
    return;
  }

  if (command == "PING") {
    Serial.println(F("DONE:PONG"));
    return;
  }

  if (command == "STATUS") {
    printStatus();
    return;
  }

  if (command == "HOME") {
    if (closeAllDoorsOnStartup()) {
      Serial.println(F("DONE:HOME"));
    }
    return;
  }

  if (command == "CALIBRATE:1") {
    stepper.setCurrentPosition(0);
    currentTray = 1;
    targetTray = 1;
    pendingTrayOperation = TRAY_OPERATION_NONE;
    pendingDispenseDoor = 0;
    enableTrayDriver();
    delay(100);
    trayCalibrated = true;
    Serial.println(F("DONE:CALIBRATE"));
    return;
  }

  if (command.startsWith("CALIBRATE:")) {
    Serial.println(F("ERROR:calibration slot must be 1"));
    return;
  }

  if (command == "TRAY:RELEASE") {
    stepper.stop();
    pendingTrayOperation = TRAY_OPERATION_NONE;
    pendingDispenseDoor = 0;
    trayCalibrated = false;
    disableTrayDriver();
    Serial.println(F("DONE:TRAY_RELEASE"));
    return;
  }

  if (command.startsWith("TRAY:")) {
    int slot = command.substring(5).toInt();
    startTrayOperation(slot, TRAY_OPERATION_MOVE, 0);
    return;
  }

  if (command.startsWith("DOOR:")) {
    handleDoorCommand(command);
    return;
  }

  if (command.startsWith("DISPENSE:")) {
    handleDispenseCommand(command);
    return;
  }

  // Lenh test nhanh: so 1-8 hoac K1-K8.
  if (command.length() == 1 && command.charAt(0) >= '1' && command.charAt(0) <= '8') {
    startTrayOperation(command.charAt(0) - '0', TRAY_OPERATION_MOVE, 0);
    return;
  }

  if (command.length() == 2 && command.charAt(0) == 'K' &&
      command.charAt(1) >= '1' && command.charAt(1) <= '8') {
    startTrayOperation(command.charAt(1) - '0', TRAY_OPERATION_MOVE, 0);
    return;
  }

  if (command == "O1") {
    if (openDoor(1)) Serial.println(F("DONE:DOOR"));
    return;
  }
  if (command == "C1") {
    if (closeDoor(1)) Serial.println(F("DONE:DOOR"));
    return;
  }
  if (command == "O2") {
    if (openDoor(2)) Serial.println(F("DONE:DOOR"));
    return;
  }
  if (command == "C2") {
    if (closeDoor(2)) Serial.println(F("DONE:DOOR"));
    return;
  }
  if (command == "O3") {
    if (openDoor(3)) Serial.println(F("DONE:DOOR"));
    return;
  }
  if (command == "C3") {
    if (closeDoor(3)) Serial.println(F("DONE:DOOR"));
    return;
  }

  Serial.println(F("ERROR:invalid command"));
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      serialCommand.trim();
      serialCommand.toUpperCase();
      if (serialCommand.length() > 0) {
        handleCommand(serialCommand);
      }
      serialCommand = "";
      continue;
    }

    if (serialCommand.length() >= MAX_COMMAND_LENGTH) {
      serialCommand = "";
      Serial.println(F("ERROR:command too long"));
      continue;
    }

    serialCommand += c;
  }
}

// ================= KHOI DONG VA VONG LAP =================
void setup() {
  digitalWrite(STEPPER_ENABLE_PIN, STEPPER_ENABLE_ACTIVE_LEVEL == HIGH ? LOW : HIGH);
  pinMode(STEPPER_ENABLE_PIN, OUTPUT);
  disableTrayDriver();

  pinMode(CTHT1, INPUT_PULLUP);
  pinMode(CTHT2, INPUT_PULLUP);
  pinMode(CTHT3, INPUT_PULLUP);
  pinMode(CTHT4, INPUT_PULLUP);
  pinMode(CTHT5, INPUT_PULLUP);
  pinMode(CTHT6, INPUT_PULLUP);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(IN5, OUTPUT);
  pinMode(IN6, OUTPUT);

  motor1Stop();
  motor2Stop();
  motor3Stop();

  stepper.setPinsInverted(DIR_INVERT, STEP_INVERT, false);
  stepper.setMinPulseWidth(20);
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setAcceleration(ACCELERATION);

  pulsesPerSystemRevolution = lround((float)MOTOR_PULSES_PER_REV * GEAR_RATIO_X);
  stepper.setCurrentPosition(0);
  currentTray = 1;
  targetTray = 1;
  trayCalibrated = false;
  trayEnabled = false;

  serialCommand.reserve(MAX_COMMAND_LENGTH);
  Serial.begin(9600);
  Serial.println(F("READY:BOOTING"));

  if (pulsesPerSystemRevolution <= 0) {
    Serial.println(F("ERROR:invalid gear ratio"));
    Serial.println(F("READY:ERROR"));
    while (true) {
      // Cau hinh co khi khong hop le, khong cho phep motor hoat dong.
    }
  }

  if (closeAllDoorsOnStartup()) {
    Serial.println(F("READY"));
  } else {
    Serial.println(F("READY:ERROR"));
  }
}

void loop() {
  readSerialCommands();
  runTray();
}
