#include "myFunctions.h"

void calibrate() {
  Serial.println("Calibrating Gripper ...");
}

void openGripper() {
  myServo.write(OPEN_ANGLE);
  isClosed = false;
  Serial.println("# OPEN");
}

void closeGripper() {
  myServo.write(CLOSE_ANGLE);
  delay(MOVE_MS);

  int relaxed = CLOSE_ANGLE - BACKOFF_DEG;
  if (relaxed < 0) relaxed = 0;
  myServo.write(relaxed);

  isClosed = true;
  Serial.println("# CLOSE (with back-off)");
}

void readButton(int pin, bool &lastReading, unsigned long &lastTime, bool &state, unsigned long debounce) {
    bool reading = digitalRead(pin);
    if (reading != lastReading) {
        lastTime = millis();
    }
    if ((millis() - lastTime) > debounce) {
        if (reading != state) {
            state = reading;
        }
    }
    lastReading = reading;
}

int readSensor(int pin, String label) {
  int val = analogRead(pin);  
  Serial.print(label);
  Serial.print(":");
  Serial.println(val);
  
  return val;
}