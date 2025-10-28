#include <HX711.h>
#include <AccelStepper.h>

#define LOADCELL_DOUT_PIN 4
#define LOADCELL_SCK_PIN 5
#define dirPin 2
#define stepPin 3
#define motorInterfaceType 1

HX711 scale;
#define CALIBRATION_FACTOR -1800  // Replace with your calibration factor

AccelStepper stepper = AccelStepper(motorInterfaceType, stepPin, dirPin);
int fsrPin = A0;  // FSR connected to Analog Pin A0
int fsrReading;   // Variable to store FSR reading
int mode = 0;  // Default mode (0: idle, 1: Weight mode, 2: FSR & Motor mode, 3: Stop)

const int stepsPer90Degree = 50;  // Assuming 1.8° per step, 90° = 50 steps

void setup() {
    Serial.begin(9600);
    delay(2000);  // Allow time for serial connection
    Serial.println("READY");  // Tell Python we’re ready
    
    pinMode(LED_BUILTIN, OUTPUT);
    scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    scale.set_offset(158190);  // Use your zero offset value
    scale.set_scale(CALIBRATION_FACTOR);

    stepper.setMaxSpeed(500);     // Increase max speed (try 500-1000)
    stepper.setAcceleration(200); // Higher acceleration for smoother movement
    stepper.setSpeed(200);        // Set constant speed for smooth motion
    stepper.setCurrentPosition(0);  
    Serial.println("Setup complete. Select Mode");
    Serial.println("Pick 1 for Grip Strength Assessment");
    Serial.println("Pick 2 for Joint Stiffness Assessment");
    Serial.println("Pick 3 to Stop");
}

void loop() {
    if (Serial.available() > 0) {  
        char command = Serial.read();  // Read command from Python
        if (command == '1') {
            mode = 1;
            Serial.println("Mode 1 Activated (Weight Measurement)");
        } else if (command == '2') {
            mode = 2;
            Serial.println("Mode 2 Activated (FSR & Motor)");
        } else if (command == '3') {
            mode = 3;  // Stop mode
            Serial.println("Mode 3 Activated (Stopping Motor)");
        }
    }

    if (mode == 1) {  
        float weight = (scale.get_units(5));
        if (weight >= 0){
          Serial.print(weight/10);
          Serial.println(",Weight");  // Output as CSV (value, sensor_type)
          delay(1000);
        }
    } 
    else if (mode == 2) {
        fsrReading = (analogRead(fsrPin));  
        if (fsrReading >= 0){
          Serial.print(fsrReading);
          Serial.println(",FSR");  // Output as CSV (value, sensor_type)
        }
        // Move stepper motor
        if (stepper.distanceToGo() == 0) {
          if (stepper.currentPosition() == 800) {
            stepper.moveTo(-100);
          } 
          else if (stepper.currentPosition() == -200) {
            stepper.moveTo(100);
          } 
          else {
            stepper.moveTo(800);
          }
        }
        stepper.run(); // Keep the motor moving
        delay(50); // Short delay to stabilize readings
    }
    else if (mode == 3) {
      stepper.stop();
      stepper.setCurrentPosition(0);
      stepper.disableOutputs();  // Disable motor power
      Serial.println("Motor stopped. Returning to idle.");
      mode = 0;
    }
  }
