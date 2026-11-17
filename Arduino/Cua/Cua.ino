// ================= PHẦN ĐỘNG CƠ BƯỚC =================
#define dirPin 2
#define stepPin 3

const int stepsPerRevolution = 1600;
const float stepPerDegree = stepsPerRevolution / 360.0;
long currentPositionSteps = 0;

// ================= PHẦN ĐỘNG CƠ DC (CỬA) =================
#define CTHT1 A0   // Mở cửa 1
#define CTHT2 A1   // Đóng cửa 1
#define CTHT3 A2   // Mở cửa 2
#define CTHT4 A3   // Đóng cửa 2
#define CTHT5 A4   // Mở cửa vật tư y tế
#define CTHT6 A5   // Đóng cửa vật tư y tế

#define PRESSED_STATE LOW

#define IN1 5
#define IN2 6
#define IN3 9
#define IN4 10
#define IN5 11
#define IN6 12

#define MOTOR_SPEED 50

const unsigned long DOOR_TIMEOUT_MS = 15000;

enum DoorState {
  DOOR_CLOSED,
  DOOR_OPEN,
  DOOR_BETWEEN,
  DOOR_CONFLICT
};

// ================= HÀM ĐIỀU KHIỂN STEP =================
void oneStep() {
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(500);
  digitalWrite(stepPin, LOW);
  delayMicroseconds(500);
}

void moveSteps(long stepsToMove) {
  if (stepsToMove == 0) return;

  if (stepsToMove > 0) {
    digitalWrite(dirPin, HIGH);
  } else {
    digitalWrite(dirPin, LOW);
  }

  long absSteps = abs(stepsToMove);
  for (long i = 0; i < absSteps; i++) {
    oneStep();
  }
}

bool moveTrayToSlot(int slot) {
  if (slot < 1 || slot > 8) {
    Serial.println("ERROR:slot must be 1-8");
    return false;
  }

  float targetAngle = slot * 103;
  long targetSteps = round(targetAngle * stepPerDegree);
  long stepsToMove = targetSteps - currentPositionSteps;
  moveSteps(stepsToMove);
  currentPositionSteps = targetSteps;
  return true;
}

// ================= HÀM ĐIỀU KHIỂN DC BẰNG PWM TRỰC TIẾP =================
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
    Serial.println("ERROR:door must be 1, 2 or 3");
    return false;
  }
  if (door == 3) {
    stopDoor(door);
    Serial.println("ERROR:supply door temporarily locked");
    return false;
  }

  DoorState state = getDoorState(door);
  if (state == DOOR_CONFLICT) {
    Serial.print("ERROR:door ");
    Serial.print(door);
    Serial.println(" switch conflict");
    stopDoor(door);
    return false;
  }
  return true;
}

void printStatus() {
  Serial.print("STATUS:");
  Serial.print("D1=");
  Serial.print(doorStateName(getDoorState(1)));
  Serial.print(",D2=");
  Serial.print(doorStateName(getDoorState(2)));
  Serial.print(",D3=");
  Serial.print(doorStateName(getDoorState(3)));
  Serial.print(",A0=");
  Serial.print(isSwitchPressed(CTHT1) ? 1 : 0);
  Serial.print(",A1=");
  Serial.print(isSwitchPressed(CTHT2) ? 1 : 0);
  Serial.print(",A2=");
  Serial.print(isSwitchPressed(CTHT3) ? 1 : 0);
  Serial.print(",A3=");
  Serial.print(isSwitchPressed(CTHT4) ? 1 : 0);
  Serial.print(",A4=");
  Serial.print(isSwitchPressed(CTHT5) ? 1 : 0);
  Serial.print(",A5=");
  Serial.println(isSwitchPressed(CTHT6) ? 1 : 0);
}

bool waitForSwitch(int switchPin, int door, const char *errorMessage) {
  unsigned long startedAt = millis();
  while (digitalRead(switchPin) != PRESSED_STATE) {
    if (millis() - startedAt > DOOR_TIMEOUT_MS) {
      stopDoor(door);
      Serial.print("ERROR:");
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

void setup() {
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);

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

  Serial.begin(9600);
  Serial.setTimeout(80);

  Serial.println("READY:BOOTING");
  if (closeAllDoorsOnStartup()) {
    Serial.println("READY");
  } else {
    Serial.println("READY:ERROR");
  }
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();
  if (command.length() == 0) {
    return;
  }

  handleCommand(command);
  delay(10);
  while (Serial.available()) Serial.read();
}

void handleCommand(String command) {
  if (command == "PING") {
    Serial.println("DONE:PONG");
    return;
  }

  if (command == "STATUS") {
    printStatus();
    return;
  }

  if (command == "HOME") {
    if (closeAllDoorsOnStartup()) {
      Serial.println("DONE:HOME");
    }
    return;
  }

  if (command.startsWith("TRAY:")) {
    int slot = command.substring(5).toInt();
    if (moveTrayToSlot(slot)) {
      Serial.println("DONE:TRAY");
    }
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

  // Hỗ trợ nhanh lệnh cũ khi test trực tiếp qua Serial Monitor.
  int legacySlot = command.toInt();
  if (legacySlot >= 1 && legacySlot <= 8) {
    if (moveTrayToSlot(legacySlot)) {
      Serial.println("DONE:TRAY");
    }
    return;
  }

  if (command == "O1") {
    if (openDoor(1)) Serial.println("DONE:DOOR");
    return;
  }
  if (command == "C1") {
    if (closeDoor(1)) Serial.println("DONE:DOOR");
    return;
  }
  if (command == "O2") {
    if (openDoor(2)) Serial.println("DONE:DOOR");
    return;
  }
  if (command == "C2") {
    if (closeDoor(2)) Serial.println("DONE:DOOR");
    return;
  }
  if (command == "O3") {
    if (openDoor(3)) Serial.println("DONE:DOOR");
    return;
  }
  if (command == "C3") {
    if (closeDoor(3)) Serial.println("DONE:DOOR");
    return;
  }

  Serial.println("ERROR:invalid command");
}

void handleDoorCommand(String command) {
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  if (secondColon < 0) {
    Serial.println("ERROR:invalid door command");
    return;
  }

  int door = command.substring(firstColon + 1, secondColon).toInt();
  if (door == 3) {
    Serial.println("ERROR:supply door temporarily locked");
    return;
  }
  String action = command.substring(secondColon + 1);
  bool ok = false;

  if (action == "OPEN") {
    ok = openDoor(door);
  } else if (action == "CLOSE") {
    ok = closeDoor(door);
  } else {
    Serial.println("ERROR:door action must be OPEN or CLOSE");
    return;
  }

  if (ok) {
    Serial.println("DONE:DOOR");
  }
}

void handleDispenseCommand(String command) {
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  if (secondColon < 0) {
    Serial.println("ERROR:invalid dispense command");
    return;
  }

  int slot = command.substring(firstColon + 1, secondColon).toInt();
  int door = command.substring(secondColon + 1).toInt();

  if (door == 3) {
    Serial.println("ERROR:supply door temporarily locked");
    return;
  }

  if (!moveTrayToSlot(slot)) {
    return;
  }
  if (!openDoor(door)) {
    return;
  }

  Serial.println("DONE:DISPENSE");
}
