/* -*- mode: c; c-file-style: "gnu" -*- */
/*
 * The code is free and can be used for any purpose including commercial
 * purposes.  Packt Publishing and the authors can not be held liable for
 * any use or result of the book's text or code.  Further copyright &
 * license info is found in the book's Copyright page.  The book can be
 * obtained from
 * "https://www.packtpub.com/hardware-and-creative/beaglebone-secret-agents".
*/
/**
 * @file   keypad.cc
 * @author Joshua Datko <jbdatko@gmail.com>
 * @date   Sat Jun  7 09:40:03 2014
 *
 * @brief  Provides a six pin keypad code when prompted over I2C
 *
 *
 */
#include <Keypad.h>
#include <Wire.h>

const byte ROWS = 4;
const byte COLS = 3;
char keys[ROWS][COLS] =
  {
    {'1','2','3'},
    {'4','5','6'},
    {'7','8','9'},
    {'*','0','#'}
  };

/* Connect as follows:
   This is the following keypad:
   https://www.sparkfun.com/products/8653

   Keypad Pin -> Arduino Digital
   3 -> 2
   1 -> 3
   5 -> 4

   2 -> 5
   7 -> 6
   6 -> 7
   4 -> 8
*/

/* connect to the row pinouts of the keypad */
byte rowPins[ROWS] = {5, 6, 7, 8};
/* connect to the column pinouts of the keypad */
byte colPins[COLS] = {2, 3, 4};

/* Declare program constants */
const int LED = 13;
Keypad keypad = Keypad( makeKeymap (keys), rowPins, colPins, ROWS, COLS );
const int I2C_ADDR = 0x42;
/* This is a stupid combination; one an idiot would have on his
   luggage - Spaceballs, 1987*/
char passcode[] = {'1', '2', '3', '4', '5'};
/* flag to trigger when to go collect the code or not */
bool collect_code = false;

/**
 * Obligatory Arduino setup function
 *
 */
void setup ()
{
  pinMode (LED, OUTPUT);

  digitalWrite (LED, LOW);
  Wire.begin (I2C_ADDR);
  Wire.onRequest (provide_code);
  Wire.onReceive (receiveEvent3);
}

/**
 * Briefly flash the LED
 *
 */
void flash()
{

  digitalWrite (LED, LOW);
  delay (100);
  digitalWrite (LED, HIGH);
}

/**
 * Collect the keypad code into the buffer. This function blocks on
 * each key.
 *
 * @param buf The buffer to fill
 * @param len The length of the buffer to fill
 *
 * @return true if filled, otherwise false
 */
bool get_code (char * buf, const int len)
{

  bool result = false;

  if (NULL != buf)
    {
      for (int x = 0; x < len; x++)
        {
          buf[x] = keypad.waitForKey();
          flash ();
        }
      result = true;
    }

  return result;
}


void loop()
{
  delay (100);

  if (collect_code)
    {
      digitalWrite (LED, HIGH);
      get_code (passcode, sizeof(passcode));
      digitalWrite (LED, LOW);
      collect_code = false;
    }


}

void provide_code ()
{
  Wire.write ((uint8_t *)passcode, sizeof(passcode));
}

void receiveEvent3(int bytes)
{

  /* Pull the data off, but we don't care what it is */
  while(0 < Wire.available())
    {
      char c = Wire.read();
    }

  collect_code = true;

}
