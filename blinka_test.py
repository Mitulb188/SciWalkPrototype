import board
import digitalio

# This line will raise an exception if Blinka isn't detecting the board.
try:
    pin = digitalio.DigitalInOut(board.D4)
    print("Blinka is working!")
    print("Board detected as:", board.board_id)
except Exception as e:
    print("Blinka failed to detect the board.")
    print("Error:", e)
