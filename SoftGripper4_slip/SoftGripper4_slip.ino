#include "myFunctions.h"
#include <ESP32Servo.h>

// Pin Definitions
const int SERVO_PIN = 18;       // PWM Signal to motor (yellow cable)
const int BUTTON_PIN = 23;      // Close/Open Gripper. Button to ground (pullup resistor)
const int RED_LED = 2;          // ON when gripper is not grasping
const int GREEN_LED = 4;        // ON when gripper is grasping
const int SENSOR_1 = 34;        // Pressure sensor
const int SENSOR_2 = 35;        // Pressure sensor

// Object definitions
Servo myServo;                  // Servo Motor that controls the gripper

// Constants
const int MIN_US         = 500;   // Minimum pulse width (us)
const int MAX_US         = 2400;  // Maximum pulse width (us)
const int OPEN_ANGLE     = 0;     // 0 deg = fully open
const int CLOSE_ANGLE    = 54;    // 53 deg = fully closed
const int BACKOFF_DEG    = 3;     // Backoff after hard close (unused in incremental mode)
const int MOVE_MS        = 450;   // Legacy delay constant (kept for compatibility)
const int GRASP_DETECT_THRESH = 1200; // ADC threshold to flag isGrasped (green LED on, keep closing)
const int GRASP_STOP_THRESH   = 3000; // ADC threshold to stop closing (firm grasp confirmed)
const int SLIP_THRESH         = 2500; // ADC threshold below which a slip is detected during hold

const int   STEP_DEG  = 1;        // Degrees to advance per step during incremental close
const unsigned long STEP_MS = 5;  // Time between steps (ms)
const unsigned long HOLD_MS = 20; // Sensor polling interval while holding (ms)

// Gripper state
bool isClosed   = false;  // True once gripper has stopped closing (grasped or fully shut)
bool isGrasped  = false;  // True if object was detected during close
bool isClosing  = false;  // True while incremental close is in progress
bool isHolding  = false;  // True while monitoring for slip after a firm grasp
int  currentAngle = OPEN_ANGLE; // Tracks live servo position

// Button state (persistent — must survive across loop() calls)
bool lastButtonReading = HIGH;
bool buttonState       = HIGH;
bool lastSteadyState   = HIGH;  

unsigned long lastDebounceTime = 0;
const unsigned long debounceMs = 40;

// Incremental close timing
unsigned long lastStepTime   = 0;
unsigned long graspStartTime = 0;  // Reference time for CSV timestamps
unsigned long holdLastTime   = 0;  // Last sensor poll time during hold

// ─── Helper ────────────────────────────────────────────────────────────────

void startClosing() {
  isClosing      = true;
  isClosed       = false;
  isGrasped      = false;
  isHolding      = false;
  lastStepTime   = millis();
  graspStartTime = millis();
  Serial.println("---");  // Trial separator for multi-trial CSV files
  Serial.println("time_ms,angle,S1,S2,max,is_grasped,event");
}

// Resume closing from currentAngle after a slip — no CSV header reset
void startRecovering() {
  isClosing  = true;
  isClosed   = false;
  isHolding  = false;
  lastStepTime = millis();
  Serial.println("# SLIP detected — recovering...");
}

// ─── Setup ─────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, MIN_US, MAX_US);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(RED_LED,    OUTPUT);
  pinMode(GREEN_LED,  OUTPUT);

  openGripper();          // Always start open
  currentAngle = OPEN_ANGLE;

  Serial.println("Ready. Button: close/open. Serial: 1=open, 2=close.");
}

// ─── Loop ──────────────────────────────────────────────────────────────────

void loop() {

  // ── 1. Button edge detection ──────────────────────────────────────────
  readButton(BUTTON_PIN, lastButtonReading, lastDebounceTime, buttonState, debounceMs);

  if (buttonState == LOW && lastSteadyState == HIGH) {
    // Falling edge: button just pressed
    if (!isClosed && !isClosing) {
      startClosing();                 // Gripper is open → begin close sequence
    } else {
      // Gripper is closing, holding, or already closed → open immediately
      isClosing  = false;
      isClosed   = false;
      isGrasped  = false;
      isHolding  = false;
      openGripper();
      currentAngle = OPEN_ANGLE;
    }
  }
  lastSteadyState = buttonState;

  // ── 2. Incremental close logic ────────────────────────────────────────
  if (isClosing && (millis() - lastStepTime >= STEP_MS)) {
    lastStepTime = millis();

    // Read sensors directly (suppress per-sensor prints during logging)
    int sensor1    = analogRead(SENSOR_1);
    int sensor2    = analogRead(SENSOR_2);
    int maxReading = max(sensor1, sensor2);

    // Update isGrasped as soon as we cross the detect threshold
    if (maxReading >= GRASP_DETECT_THRESH) {
      isGrasped = true;
    }

    // CSV row: time_ms, angle, S1, S2, max, is_grasped, event
    Serial.print(millis() - graspStartTime); Serial.print(",");
    Serial.print(currentAngle);              Serial.print(",");
    Serial.print(sensor1);                   Serial.print(",");
    Serial.print(sensor2);                   Serial.print(",");
    Serial.print(maxReading);                Serial.print(",");
    Serial.print(isGrasped ? 1 : 0);        Serial.print(",");

    if (maxReading >= GRASP_STOP_THRESH) {
      isClosing  = false;
      isClosed   = true;
      isHolding  = true;
      holdLastTime = millis();
      Serial.println("FIRM_GRASP");
      Serial.print("# FIRM GRASP at angle: ");
      Serial.println(currentAngle);

    } else if (currentAngle >= CLOSE_ANGLE) {
      isClosing = false;
      isClosed  = true;
      // Only hold-monitor if we at least detected something
      isHolding = isGrasped;
      if (isHolding) holdLastTime = millis();
      if (isGrasped) {
        Serial.println("SOFT_GRASP");
        Serial.println("# MAX ANGLE reached — object detected (soft grasp).");
      } else {
        Serial.println("NO_OBJECT");
        Serial.println("# MAX ANGLE reached — no object detected.");
      }

    } else {
      // Advance one step
      Serial.println("CLOSING");
      currentAngle += STEP_DEG;
      myServo.write(currentAngle);
    }
  }

  // ── 3. Hold monitoring — slip detection ──────────────────────────────
  if (isHolding && (millis() - holdLastTime >= HOLD_MS)) {
    holdLastTime = millis();

    int sensor1    = analogRead(SENSOR_1);
    int sensor2    = analogRead(SENSOR_2);
    int maxReading = max(sensor1, sensor2);

    // Log hold readings to CSV with HOLD event tag
    Serial.print(millis() - graspStartTime); Serial.print(",");
    Serial.print(currentAngle);              Serial.print(",");
    Serial.print(sensor1);                   Serial.print(",");
    Serial.print(sensor2);                   Serial.print(",");
    Serial.print(maxReading);                Serial.print(",");
    Serial.print(isGrasped ? 1 : 0);        Serial.print(",");

    if (maxReading < SLIP_THRESH) {
      // Slip detected — re-enter closing from current angle
      isGrasped = false;
      Serial.println("SLIP");
      if (currentAngle < CLOSE_ANGLE) {
        startRecovering();
      } else {
        // Already at max angle, cannot squeeze further
        isHolding = false;
        isClosed  = true;
        Serial.println("# SLIP at max angle — cannot recover.");
      }
    } else {
      Serial.println("HOLD");
    }
  }


  if (isGrasped) {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED,   LOW);
  } else {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED,   HIGH);
  }

  // ── 4. Serial commands ────────────────────────────────────────────────
  if (Serial.available()) {
    int cmd = Serial.parseInt();
    while (Serial.available()) Serial.read();

    if (cmd == 1) {
      isClosing  = false;
      isClosed   = false;
      isGrasped  = false;
      isHolding  = false;
      openGripper();
      currentAngle = OPEN_ANGLE;
    } else if (cmd == 2) {
      startClosing();
    }
  }
}
