from machine import Pin, I2C, SPI
import time
import ustruct
import math
import socket
import network

# ====== ADXL345 Accelerometer Setup ======
# Constants
ADXL345_ADDRESS = 0x53
ADXL345_POWER_CTL = 0x2D
ADXL345_DATA_FORMAT = 0x31
ADXL345_DATAX0 = 0x32

# Configure accelerometer range (±2g)
RANGE = 2  # ±2g
SCALE_FACTOR = RANGE * 2 / 512  # Conversion factor (assuming 10-bit ADC)

# Initialize I2C for ADXL345
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)

def write_register(addr, reg, value):
    """Write a value to a register."""
    i2c.writeto_mem(addr, reg, bytes([value]))

def read_register(addr, reg, nbytes):
    """Read bytes from a register."""
    return i2c.readfrom_mem(addr, reg, nbytes)

def initialize_adxl345():
    """Initialize the ADXL345 accelerometer."""
    write_register(ADXL345_ADDRESS, ADXL345_POWER_CTL, 0x08)  # Measurement mode
    write_register(ADXL345_ADDRESS, ADXL345_DATA_FORMAT, 0x08)  # Full resolution ±2g

def read_acceleration():
    """Read x, y, z acceleration from ADXL345."""
    data = read_register(ADXL345_ADDRESS, ADXL345_DATAX0, 6)
    x, y, z = ustruct.unpack('<hhh', data)
    return x * SCALE_FACTOR, y * SCALE_FACTOR, z * SCALE_FACTOR

def calculate_magnitude(x, y, z):
    """Calculate the magnitude of the acceleration vector."""
    return math.sqrt(x**2 + y**2 + z**2)

# ====== MCP3008 ADC Setup ======
spi = SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT)

def readadc(adcnum):
    """Reads data from a specified MCP3008 channel (0-7)."""
    if adcnum < 0 or adcnum > 7:
        return -1
    
    cmd = 0b11 << 6 | (adcnum & 0x07) << 3
    buf = bytearray(3)
    buf[0] = cmd
    cs.low()
    spi.write_readinto(buf, buf)
    cs.high()
    
    data = ((buf[1] & 0x0F) << 8) | buf[2]
    return data >> 2  # Return 10-bit value shifted to 8-bit

# ====== WiFi and Socket Setup ======
ssid = ""
password = ''
server_ip = ''
server_port = 65432

# Connect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
while not wlan.isconnected():
    print('Waiting for connection...')
    time.sleep(1)
print('Connected to WiFi')

# Connect to server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((server_ip, server_port))
print(f"Connected to server {server_ip}:{server_port}")

# ====== Main Loop ======
# Pedometer variables
step_count = 0
threshold = 1.2
step_detected = False

# ADC variables
delay = 2  # Delay between readings

# Initialize ADXL345
initialize_adxl345()

try:
    while True:
        # Read acceleration and calculate magnitude
        ax, ay, az = read_acceleration()
        magnitude = calculate_magnitude(ax, ay, az)
        
        # Detect steps
        if magnitude > threshold and not step_detected:
            step_detected = True
            step_count += 1
            print(f"Step detected! Total steps: {step_count}")
        elif magnitude < threshold:
            step_detected = False

        # Read MCP3008 channels
        adc_values = {}
        for channel in range(8):
            adc_values[f"Channel {channel}"] = readadc(channel)

        # Combine step count and ADC values into a message
        adc_message = ', '.join([f"{key}: {value}" for key, value in adc_values.items()])
        message = f"Steps: {step_count}, {adc_message}"
        print(f"Sending message: {message}")

        # Send the message to the server
        sock.sendall(message.encode('utf-8'))

        # Wait before the next iteration
        time.sleep(delay)

except KeyboardInterrupt:
    print("Program stopped by user.")

finally:
    sock.close()
    print("Socket closed")



