#ifndef MYFUNCTIONS_H
#define MYFUNCTIONS_H

#include <Arduino.h>
#include <ESP32Servo.h>

void calibrate();
void openGripper();
void closeGripper();
void readButton(int pin, bool &lastReading, unsigned long &lastTime, bool &state, unsigned long debounce);
int readSensor(int pin, String label);

extern Servo myServo;

extern const int OPEN_ANGLE;
extern const int CLOSE_ANGLE;
extern const int BACKOFF_DEG;
extern const int MOVE_MS;

extern bool isClosed;

#endif