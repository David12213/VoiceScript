#The first official version of my working code for my plotter!
#Press control + c to shut off machine at any given time
import time
import glob
import serial
import speech_recognition as sr
import HersheyFonts

BAUD_RATE = 115200       
FEED_RATE = 1200         

FONT_SIZE = 18.0 # size of the text
START_X = 0.0 #Where Machine moves to when first starting
START_Y =120.0 #Where machine moves to (Starts at the very top)

def auto_discover_grbl_port():
    print("Looking for machine...")
    patterns = [
        '/dev/cu.usbserial*', '/dev/cu.usbmodem*', '/dev/cu.wchusbserial*', 
        '/dev/ttyUSB*', '/dev/ttyACM*'
    ]
    
    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            print(f"Discovered and binding to active physical port: {ports[0]}")
            return ports[0]
            
    return None

def initialize_machine():
    port_path = auto_discover_grbl_port()
    
    if not port_path:
        print("\nNo USB detected hardware detected.")
        return None

    try:
        print(f"Attempting to connect to: {port_path} at {BAUD_RATE} baud...")
        dev = serial.Serial(port_path, BAUD_RATE, timeout=1, write_timeout=1)
        time.sleep(2)  
        
        for cmd in ["\n\n", "$X", "$H", "G28"]:
            dev.write(f"{cmd}\n".encode())
            time.sleep(0.5)
        
        while dev.in_waiting > 0:
            dev.readline()
        
        print("Success!")
        return dev
    except Exception as e:
        print(f"\nCOMMUNICATION CRASH: Failed to open serial thread: {e}")
        return None

def send_gcode_line(dev, command):
    cmd = command.strip()
    if not dev or not cmd:
        return True
        
    dev.write(f"{cmd}\n".encode('utf-8'))
    
    while True:
        if dev.in_waiting > 0:
            response = dev.readline().decode('utf-8', errors='ignore').strip().lower()
            if 'ok' in response:
                return True
            if 'error' in response:
                print(f" [!] REJECTED: {cmd} - {response}")
                return False
        time.sleep(0.005)

def speech_text_to_grbl_gcode(text):

    gcode_commands = ["G21", "G90"]
    
    font = HersheyFonts.HersheyFonts()
    font.load_default_font("cursive")
    font.normalize_rendering(FONT_SIZE) 
    
    MAX_X = 148.0 
    LINE_SPACING = 20.0
    
    current_x = START_X
    current_y = START_Y
    
    for word in text.split():
        strokes = list(font.lines_for_text(word))
        if not strokes:
            continue
            
        word_width = max([max(x1, x2) for (x1, y1), (x2, y2) in strokes]) + (FONT_SIZE * 0.2)
        
        if current_x + word_width > MAX_X and current_x != START_X:
            gcode_commands.append("WAIT:Lift pen out. [Press Enter to move to next line]")
            current_y -= LINE_SPACING
            current_x = START_X
            gcode_commands.append(f"G0 X{current_x:.2f} Y{current_y:.2f}")
            
            gcode_commands.append("SLEEP:1.5")
            
            gcode_commands.append("WAIT:Lower pen back in. [Press Enter to continue writing]")
            
        for (x1, y1), (x2, y2) in strokes:
            start_x = current_x + x1
            start_y = current_y + y1
            end_x = current_x + x2
            end_y = current_y + y2
            
            gcode_commands.append(f"G0 X{start_x:.2f} Y{start_y:.2f}")
            gcode_commands.append(f"G1 X{end_x:.2f} Y{end_y:.2f} F{FEED_RATE}")
            
        current_x += word_width + (FONT_SIZE * 0.4)
        
    gcode_commands.append("G4 P2.0")
    
    return gcode_commands


def listen_and_write(dev):
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.0
    with sr.Microphone() as source:
    
        print("\nCalibrating audio environment... (Quiet please)")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Ready, say your phrase now.")
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)
            
            text = recognizer.recognize_google(audio).capitalize()
            print(f"Recognized Message: \"{text}\"")
            
            print("Moving to starting position...")
            send_gcode_line(dev, "G21")
            send_gcode_line(dev, "G90")
            send_gcode_line(dev, f"G0 X{START_X:.2f} Y{START_Y:.2f}")
            time.sleep(1.0)
            input("\nPut the pen in now. [Press Enter to confirm and begin drawing]")
            
            commands = speech_text_to_grbl_gcode(text)
            
            print(f"Sending code ({len(commands)} actions) to machine...")
            for cmd in commands:
                
                if cmd.startswith("WAIT:"):
                    msg = cmd.split(":", 1)[1]
                    input(f"\n{msg}")
                elif cmd.startswith("SLEEP:"):
                    time.sleep(float(cmd.split(":", 1)[1]))
                else:
                    send_gcode_line(dev, cmd)

            time.sleep(1.0)
            print("Drawing complete.")
            input("Please take the pen out. [Press Enter to Home]")
            send_gcode_line(dev, "$H")
        
        except sr.WaitTimeoutError:
            print("[x] No audio/words detected.")
        except sr.UnknownValueError:
            print("[x] Cant interpret spoken words.")
        except sr.RequestError as e:
            print(f"[x] API Gateway Exception: {e}")

if __name__ == "__main__":
    machine_device = initialize_machine()
    
    if machine_device:
        try:
            while True:
                input("\n[Press Enter to record] (Ctrl+C to Exit)...")
                listen_and_write(machine_device)
        except KeyboardInterrupt:
            print("\nShutting down.")
            machine_device.close()