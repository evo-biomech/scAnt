#include <SpeedyStepper.h>
#include <Bounce2.h>

int fan = 10;
String command_Y;
Bounce debouncer = Bounce(); // prevents detecting held buttons

const unsigned int MAX_COMMAND_LENGTH = 100;
#define SPTR_SIZE   20
char   *sPtr [SPTR_SIZE];
signed long number;
// int delay 300;
int long length = 300;


SpeedyStepper stepper_X;
SpeedyStepper stepper_Y;
SpeedyStepper stepper_Z;

const int X_STEP_PIN = 7;
const int X_DIR_PIN = 6;
const int ENDSTOP_X = 19;

const int Y_STEP_PIN = 5;
const int Y_DIR_PIN = 4;

const int Z_STEP_PIN = 3;
const int Z_DIR_PIN = 2;
const int ENDSTOP_Z = 18;

const int ENABLE_PIN = 8;
const int M1_PIN = 12;
const int M2_PIN = 11;
// const int M3_PIN = 10;

const int LIGHT_PIN = 10;

signed long pos;
signed long offset_x = 0;
signed long offset_y = 0;
signed long offset_z = 0;

signed long glob_x  = 0;
signed long glob_y  = 0;
signed long glob_z  = 0;



int separate (String str, char **p, int size)
{
    int  n;
    char s [100];

    strcpy (s, str.c_str ());

    *p++ = strtok (s, " ");
    for (n = 1; NULL != (*p++ = strtok (NULL, " ")); n++)
        if (size == n)
            break;

    return n;
}


void setup() {
  // put your setup code here, to run once:
    // start communication
  Serial.begin(9600);

  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH);

  pinMode(M1_PIN, OUTPUT);
  digitalWrite(M1_PIN, LOW);

  pinMode(M2_PIN, OUTPUT);
  digitalWrite(M2_PIN, LOW);

  // pinMode(M3_PIN, OUTPUT);
  // digitalWrite(M3_PIN, LOW);

  pinMode(LIGHT_PIN, OUTPUT);
  digitalWrite(LIGHT_PIN, LOW);

  pinMode(ENDSTOP_X, INPUT_PULLUP);
  debouncer.attach(ENDSTOP_X);
  debouncer.interval(0.2);
  pinMode(ENDSTOP_Z, INPUT_PULLUP);
  debouncer.attach(ENDSTOP_Z);
  debouncer.interval(0.2);

  stepper_X.connectToPins(X_STEP_PIN, X_DIR_PIN);

  stepper_Y.connectToPins(Y_STEP_PIN, Y_DIR_PIN);

  stepper_Z.connectToPins(Z_STEP_PIN, Z_DIR_PIN);

  delay(500);
}

void loop() {

  // put your main code here, to run repeatedly:
  while (Serial.available())
  {

    //hold new command from Blender Python
    static char command[MAX_COMMAND_LENGTH];
    static unsigned int command_pos = 0;


    //read next available bytes from Serial
    char inByte = Serial.read();

    // avoids reading negative values 
    if (inByte > 0)
    {
        // check if byte is NOT a terminating character
      if (inByte != '\n' && (command_pos < MAX_COMMAND_LENGTH - 1))
      {
        //add bytes to string
        command[command_pos] = inByte;
        command_pos++;
      }
      else
      {
        //add null character to string, print the command, and reset command_pos
        //only print non-empty lines
        if (command_pos > 0)
        {
          Serial.print("Received new command: ");
          Serial.println(command);

                  
          //using atoi() we can convert null-terminated strings into integers
          //output integer
          int N = separate (command, sPtr, SPTR_SIZE);

          if (strcmp(sPtr [0], "test") ==0)
          {
            Serial.println("So you have chosen death...");

            // move forward and back
            stepper_X.setupMoveInSteps(200*8);
            stepper_Y.setupMoveInSteps(200*8);
            while(!(stepper_X.motionComplete() && stepper_Y.motionComplete()))
            {
              stepper_X.processMovement(); // this call moves the motor
              stepper_Y.processMovement(); // this call moves the motor
            }
        


          }
          
          // else if (strcmp(sPtr [0], "SET_DELAY") == 0)
          // {
          //   delay = atoi(sPtr[1]);
          //   Serial.print("Flash delay set to ");
          //   Serial.println(delay);
          // }
          
          else if (strcmp(sPtr [0], "SET_LENGTH") == 0)
          {
            length = atoi(sPtr[1]);
            Serial.print("Flash delay set to ");
            Serial.println(length);
          }
  
          else if (strcmp(sPtr [0], "FLASH_LIGHT") == 0)
          {
            digitalWrite(LIGHT_PIN, HIGH);
            delay(length);
            digitalWrite(LIGHT_PIN, LOW);
          }
          
          else if (strcmp(sPtr[0], "STEPMODE") == 0)
          {
            int step_mode = atoi(sPtr[1]);

            // if (step_mode == 1)
            // {
            //   digitalWrite(M1_PIN, LOW);
            //   digitalWrite(M2_PIN, LOW);
            //   // digitalWrite(M3_PIN, LOW);
            // }
            if (step_mode == 2)
            {
              digitalWrite(M1_PIN, HIGH);
              digitalWrite(M2_PIN, LOW);
              // digitalWrite(M3_PIN, LOW);
            }
            else if (step_mode == 4)
            {
              digitalWrite(M1_PIN, LOW);
              digitalWrite(M2_PIN, HIGH);
              // digitalWrite(M3_PIN, LOW);
            }
            else if (step_mode == 8)
            {
              digitalWrite(M1_PIN, LOW);
              digitalWrite(M2_PIN, LOW);
              // digitalWrite(M3_PIN, LOW);
            }
            else if (step_mode == 16)
            {
              digitalWrite(M1_PIN, HIGH);
              digitalWrite(M2_PIN, HIGH);
              // digitalWrite(M3_PIN, HIGH);
            }
            else 
            {
              digitalWrite(M1_PIN, LOW);
              digitalWrite(M2_PIN, LOW);
              // digitalWrite(M3_PIN, LOW);
            }

            stepper_X.setSpeedInStepsPerSecond(80*step_mode);
            stepper_X.setAccelerationInStepsPerSecondPerSecond(10*step_mode);
          
            stepper_Y.setSpeedInStepsPerSecond(100*step_mode);
            stepper_Y.setAccelerationInStepsPerSecondPerSecond(20*step_mode);

            stepper_Z.setSpeedInStepsPerSecond(6000*step_mode);
            stepper_Z.setAccelerationInStepsPerSecondPerSecond(50*step_mode);
          }
          
          else if (strcmp(sPtr[0], "HOME") == 0)
          {

            if (strcmp(sPtr[1], "X") == 0 )
            {
                stepper_X.setupMoveInSteps(-11000);
                while(!(digitalRead(ENDSTOP_X) == LOW))
                {
                  stepper_X.processMovement(); // this call moves the motor
                }

              stepper_X.setupStop();
              
              offset_x = stepper_X.getCurrentPositionInSteps() + 100;

              glob_x = 0;

              //update target position to avoid continue running 
              stepper_X.setupMoveInSteps(offset_x);
              while(!(stepper_X.motionComplete()))
              {
                stepper_X.processMovement(); // this call moves the motor
              }

              Serial.println("Welcome home, X");

              delay(500);
            }
            else if (strcmp(sPtr[1], "Z") == 0 )
            {
              stepper_Z.setupMoveInSteps(-11000);
              while(!(digitalRead(ENDSTOP_Z) == LOW))
              {
                stepper_Z.processMovement(); // this call moves the motor
              }

              stepper_Z.setupStop();
              
              offset_z = stepper_Z.getCurrentPositionInSteps() + 100;

              glob_z = 0;

              //update target position to avoid continue running 
              stepper_Z.setupMoveInSteps(offset_z);
              while(!(stepper_Z.motionComplete()))
              {
                stepper_Z.processMovement(); // this call moves the motor
              }
    
              Serial.println("Welcome home, Z");

              delay(500);
            }

          }
          else if (strcmp(sPtr[0], "RESET_Y") == 0)
          {
            offset_y = glob_y;
            glob_y = 0;
          }

          else if (strcmp(sPtr [0], "MOVE") == 0)
          {
            pos = strtoul(sPtr[2], NULL, 0);

            if (strcmp(sPtr[1], "X") == 0)
            {
              stepper_X.setupMoveInSteps(offset_x + pos);
              while(!(stepper_X.motionComplete()))
              {
                stepper_X.processMovement(); // this call moves the motor
              }
              glob_x = pos;
            }
            else if(strcmp(sPtr[1], "Y") == 0)
            {
              stepper_Y.setupMoveInSteps(offset_y + pos);
              while(!(stepper_Y.motionComplete()))
              {
                stepper_Y.processMovement(); // this call moves the motor
              }
              glob_y = offset_y + pos;
            }        
            else if (strcmp(sPtr[1], "Z") == 0)
            {
              stepper_Z.setupMoveInSteps(offset_z + pos);
              while(!(stepper_Z.motionComplete()))
              {
                stepper_Z.processMovement(); // this call moves the motor
              }
              glob_z = pos;
            }      

          }
          else if (strcmp(sPtr [0], "DEENERGISE") == 0)
          {
            digitalWrite(ENABLE_PIN, HIGH);
          }
          else if (strcmp(sPtr [0], "ENERGISE") == 0)
          {
            digitalWrite(ENABLE_PIN, LOW);
          }
          else if (strcmp(sPtr[0], "GETPOS") == 0)
          {
             if (strcmp(sPtr[1], "X") == 0)
             {
              Serial.println(stepper_X.getCurrentPositionInSteps() + offset_x);
             }
             else if (strcmp(sPtr[1], "Y") == 0)
             {
              Serial.println(stepper_Y.getCurrentPositionInSteps() + offset_y);
             }
             else if (strcmp(sPtr[1], "Z") == 0)
             {
              Serial.println(stepper_Z.getCurrentPositionInSteps() - offset_z);
             }
          }
          else
          {
            Serial.println("Yeah, that does not sound like a valid command, bro.");
          }
        }
        command_pos = 0;
      }
    }
  }
}
