# VoiceScript: speech-to-physical-text for a 3-axis & 2-axis pen plotter / 3D printer / laser cutter / anything that reads g-code
# Press Control+C to shut off the machine at any time.

import glob
import time
import HersheyFonts
import serial
import speech_recognition as sr

# Use "MARLIN" for 3D printers, use "GRBL" for a laser cutter/hobby CNC. GRBl one is like V1 anyways
FIRMWARE = "MARLIN"

#Marlin printers use either 115200 or 250000 baud
BAUD_RATE = 115200

DRAW_FEED_RATE = 2800 #fastest without smudging (I think)
TRAVEL_FEED_RATE = 6500
Z_FEED_RATE = 600
FONT_SIZE = 18.0

# Writing area, adjust
START_X = 15.0
START_Y = 60.0
MAX_X = 200.0
MIN_Y = 0.0
LINE_SPACING = 20.0

#smaller Z lowers it
PEN_DOWN_Z = 0.7
PEN_UP_Z = 3.5

WORD_SPACING = FONT_SIZE * 0.3
WORD_END_PADDING = FONT_SIZE * 0.2
COMMAND_TIMEOUT = 100.0


def auto_discover_machine_port():
    print("Looking for machine...")
    patterns = [
        "/dev/cu.usbserial*",
        "/dev/cu.usbmodem*",
        "/dev/cu.wchusbserial*",
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
    ]

    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            print(f"Discovered and binding to active physical port: {ports[0]}")
            return ports[0]
        #This either works or doesnt work, idk how to fix so hope it works

    return None


def send_gcode_line(dev, command, timeout=COMMAND_TIMEOUT):
    cmd = command.strip()
    if not dev or not cmd:
        return True

    dev.write(f"{cmd}\n".encode("utf-8"))
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if dev.in_waiting > 0:
            response = (
                dev.readline()
                .decode("utf-8", errors="ignore")
                .strip()
                .lower()
            )

            if response.startswith("ok"):
                return True
            if response.startswith("error") or response.startswith("alarm"):
                print(f" [!] REJECTED: {cmd} - {response}")
                return False

        time.sleep(0.005)

    print(f" [!] TIMEOUT: Machine did not acknowledge: {cmd}")
    return False


def initialize_machine():
    port_path = auto_discover_machine_port()

    if not port_path:
        print("\nNo USB-connected hardware detected.")
        return None

    try:
        print(f"Attempting to connect to: {port_path} at {BAUD_RATE} baud...")
        dev = serial.Serial(
            port_path,
            BAUD_RATE,
            timeout=1,
            write_timeout=1,
        )
        time.sleep(2)

        #discard strtup messages on 3d printer
        dev.write(b"\n\n")
        time.sleep(0.5)
        dev.reset_input_buffer()

        if FIRMWARE.upper() == "MARLIN":
            startup_commands = ["G28"]
        elif FIRMWARE.upper() == "GRBL":
            startup_commands = ["$X", "$H"]
        else:
            raise ValueError('FIRMWARE must be either "MARLIN" or "GRBL".')

        print("Homing machine. Keep the pen clear of the paper...")
        for cmd in startup_commands:
            if not send_gcode_line(dev, cmd):
                dev.close()
                return None

        for cmd in [
            "G21",  
            "G90",  
            f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}",
        ]:
            if not send_gcode_line(dev, cmd):
                dev.close()
                return None

        print("Success!")
        return dev

    except Exception as e:
        print(f"\nCOMMUNICATION CRASH: Failed to initialize machine: {e}")
        return None


def add_pen_up(commands):
    commands.append(f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}")


def add_pen_down(commands):
    commands.append(f"G1 Z{PEN_DOWN_Z:.2f} F{Z_FEED_RATE}")


def get_word_strokes(font, word):
    """Return the word as separate continuous pen strokes."""
    return [list(stroke) for stroke in font.strokes_for_text(word) if len(stroke) >= 2]


def get_word_width(strokes):
    """Measure a rendered word using all points in all of its strokes."""
    points = [point for stroke in strokes for point in stroke]
    if not points:
        return 0.0

    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    return (max_x - min_x) + WORD_END_PADDING


def speech_text_to_grbl_gcode(text):
    gcode_commands = ["G21", "G90"]
    add_pen_up(gcode_commands)

    font = HersheyFonts.HersheyFonts()
    font.load_default_font("futural")
    font.normalize_rendering(FONT_SIZE)

    current_x = START_X
    current_y = START_Y

    for word in text.split():
        strokes = get_word_strokes(font, word)
        if not strokes:
            continue

        all_points = [point for stroke in strokes for point in stroke]
        word_min_x = min(x for x, _ in all_points)
        word_width = get_word_width(strokes)

        #go to next lije of word is too long
        if current_x + word_width > MAX_X and current_x != START_X:
            add_pen_up(gcode_commands)
            current_y -= LINE_SPACING
            current_x = START_X

            if current_y < MIN_Y:
                raise ValueError(
                    "The text is too big for the writing area. "
                    "Increase START_Y, reduce FONT_SIZE, or reduce LINE_SPACING."
                )

            gcode_commands.append(
                f"G0 X{current_x:.2f} Y{current_y:.2f} F{TRAVEL_FEED_RATE}"
            )

        #stop machine from constantly lifting
        for stroke in strokes:
            first_x, first_y = stroke[0]
            start_x = current_x + (first_x - word_min_x)
            start_y = current_y + first_y

            add_pen_up(gcode_commands)
            gcode_commands.append(
                f"G0 X{start_x:.2f} Y{start_y:.2f} F{TRAVEL_FEED_RATE}"
            )
            add_pen_down(gcode_commands)

            for x, y in stroke[1:]:
                draw_x = current_x + (x - word_min_x)
                draw_y = current_y + y
                gcode_commands.append(
                    f"G1 X{draw_x:.2f} Y{draw_y:.2f} F{DRAW_FEED_RATE}"
                )

            add_pen_up(gcode_commands)

        current_x += word_width + WORD_SPACING

    add_pen_up(gcode_commands)
    if FIRMWARE.upper() == "MARLIN":
        gcode_commands.append("M400")  
    else:
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
            print(f'Recognized Message: "{text}"')

            print("Moving to starting position with the pen raised...")
            send_gcode_line(dev, "G21")
            send_gcode_line(dev, "G90")
            send_gcode_line(dev, f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}")
            send_gcode_line(
                dev,
                f"G0 X{START_X:.2f} Y{START_Y:.2f} F{TRAVEL_FEED_RATE}",
            )
            time.sleep(1.0)
            input(
                "\nConfirm the pen is mounted and raised above the paper. "
                "[Press Enter to begin drawing]"
            )

            commands = speech_text_to_grbl_gcode(text)

            print(f"Sending code ({len(commands)} actions) to machine...")
            for cmd in commands:
                if not send_gcode_line(dev, cmd):
                    print("Drawing stopped because the machine rejected a command.")
                    return

            time.sleep(1.0)
            print("Drawing complete.")
            input("[Press Enter to Home]")

            if FIRMWARE.upper() == "MARLIN":
                home_command = "G28"
            else:
                home_command = "$H"

            send_gcode_line(dev, home_command)

        except sr.WaitTimeoutError:
            print("[x] No audio/words detected.")
        except sr.UnknownValueError:
            print("[x] Can't interpret spoken words.")
        except sr.RequestError as e:
            print(f"[x] API Gateway Exception: {e}")
        except ValueError as e:
            print(f"[x] Layout error: {e}")


if __name__ == "__main__":
    machine_device = initialize_machine()

    if machine_device:
        try:
            while True:
                input("\n[Press Enter to record] (Ctrl+C to Exit)...")
                listen_and_write(machine_device)
        except KeyboardInterrupt:
            print("\nShutting down.")
            send_gcode_line(
                machine_device,
                f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}",
            )
            machine_device.close()
