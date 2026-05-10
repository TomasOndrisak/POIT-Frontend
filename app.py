import eventlet
eventlet.monkey_patch()

import logging
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import serial
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SERIAL_PORT = 'COM3'  # treba nastavit spravny com port
BAUD_RATE = 9600
arduino = None

last_data = {
    "Ciel": 0, "Voda": 0, "Okolie": 0, "PID_PWM": 0, 
    "Pumpa": 0, "Ohrev": 0, "PTerm": 0, "Mod": 0
}

def connect_arduino():
    global arduino
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        logging.info(f"Úspešne pripojené k Arduinu na porte {SERIAL_PORT}")
    except Exception as e:
        logging.error(f"Nepodarilo sa otvoriť port {SERIAL_PORT}. Detail: {e}")

def read_from_arduino():
    global last_data
    while True:
        if arduino and arduino.is_open:
            try:
                line = arduino.readline().decode('utf-8').strip()
                if line and "Ciel:" in line:
                    parts = line.split()
                    data = {}
                    for part in parts:
                        if ":" in part:
                            key, val = part.split(':')
                            data[key] = float(val)
                    
                    last_data = data
                    socketio.emit('serial_data', data)
            except Exception as e:
                pass
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify(last_data)

@socketio.on('update_setting')
def handle_setting(data):
    if arduino and arduino.is_open:
        cmd = f"{data['type']}{data['value']}\n"
        arduino.write(cmd.encode())
        logging.info(f"Odoslaný príkaz nastavenia: {cmd.strip()}")

@socketio.on('update_pid')
def handle_pid(data):
    if arduino and arduino.is_open:
        cmd = f"K{data['p']},{data['i']},{data['d']}\n"
        arduino.write(cmd.encode())
        logging.info(f"Odoslaný príkaz ladenia PID: {cmd.strip()}")

if __name__ == '__main__':
    connect_arduino()
    threading.Thread(target=read_from_arduino, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)