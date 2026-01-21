
# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import math
import board
import busio

import adafruit_amg88xx

i2c = busio.I2C(board.SCL, board.SDA)
amg = adafruit_amg88xx.AMG88XX(i2c)

while True:
    row_sum = 0
    for row in amg.pixels:
        # Pad to 1 decimal place
        print([f"{temp:.1f}" for temp in row])
        row_sum = row_sum + sum(row)
        print("")
    print("Avg temp:" , float(row_sum/64))
    print("\n")
    time.sleep(1)
