# VoiceScript: speech-to-physical-text for a 3-axis & 2-axis pen plotter / 3D printer / laser cutter / anything that reads g-code
# Press Control+C to shut off the machine at any time.
# DOES NOT WORK WITHOUT talk_to_plot_ui(V2)!!!!!!!!!!
import glob
import time
import HersheyFonts
import serial
import speech_recognition as sr
import threading
import json
import os
import cv2
import numpy as np

cancel_requested = threading.Event()
from PIL import Image

# Use "MARLIN" for 3D printers, use "GRBL" for a laser cutter/hobby CNC. GRBl one is like V1 anyways
FIRMWARE = "MARLIN"

#Marlin printers use either 115200 or 250000 baud
BAUD_RATE = 115200

DRAW_FEED_RATE = 2800 #fastest without smudging (I think)
TRAVEL_FEED_RATE = 6500
Z_FEED_RATE = 600
FONT_SIZE = 13.0

# Writing area, adjust
START_X = 15.0
START_Y = 60.0
MAX_X = 200.0
MAX_Y = START_Y
MIN_Y = 0.0
LINE_SPACING = 20.0

#smaller Z lowers it
PEN_DOWN_Z = 0.7
PEN_UP_Z = 3.5

WORD_SPACING = FONT_SIZE * 0.3
WORD_END_PADDING = FONT_SIZE * 0.2
COMMAND_TIMEOUT = 100.0

last_connection_error = None


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
            print(f"Discovered machine port: {ports[0]}")
            return ports[0]

    print("No hardware detected. Checked the available USB serial ports.")
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
                return False

        time.sleep(0.005)

    return False


def initialize_machine():
    global last_connection_error
    last_connection_error = None
    port_path = auto_discover_machine_port()

    if not port_path:
        last_connection_error = (
            "No hardware detected. Check the USB cable and power, then try again."
        )
        return None

    dev = None
    try:
        print(f"Attempting to connect to {port_path} at {BAUD_RATE} baud...")
        dev = serial.Serial(
            port_path,
            BAUD_RATE,
            timeout=1,
            write_timeout=1,
        )
        time.sleep(2)

        dev.write(b"\n\n")
        time.sleep(0.5)
        dev.reset_input_buffer()

        if FIRMWARE.upper() == "MARLIN":
            startup_commands = ["G28"]
        elif FIRMWARE.upper() == "GRBL":
            startup_commands = ["$X", "$H"]
        else:
            raise ValueError('FIRMWARE must be either "MARLIN" or "GRBL".')

        for cmd in startup_commands:
            if not send_gcode_line(dev, cmd):
                last_connection_error = (
                    f"The machine was found at {port_path}, but did not respond "
                    f"to startup command {cmd}. Check firmware and baud rate."
                )
                print(last_connection_error)
                dev.close()
                return None

        for cmd in [
            "G21",
            "G90",
            f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}",
        ]:
            if not send_gcode_line(dev, cmd):
                last_connection_error = (
                    f"The machine was found at {port_path}, but rejected setup command {cmd}."
                )
                print(last_connection_error)
                dev.close()
                return None

        print("Machine connected and initialized.")
        return dev

    except Exception as e:
        last_connection_error = f"Could not connect to {port_path}: {e}"
        print(last_connection_error)
        if dev is not None:
            try:
                dev.close()
            except Exception:
                pass
        return None


def add_pen_up(commands):
    commands.append(f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}")


def add_pen_down(commands):
    commands.append(f"G1 Z{PEN_DOWN_Z:.2f} F{Z_FEED_RATE}")

def get_home_command():
    return "G28" if FIRMWARE.upper() == "MARLIN" else "$H"

def get_word_strokes(font, word):
    return [list(stroke) for stroke in font.strokes_for_text(word) if len(stroke) >= 2]


def get_word_width(strokes):
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


def listen_for_text():
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.0

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)

    return recognizer.recognize_google(audio).capitalize()


def write_text(dev, text, status_callback= None):
    try:
        if status_callback:
            status_callback("Writing...")

        setup_commands = [
            "G21",
            "G90",
            f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}",
            f"G0 X{START_X:.2f} Y{START_Y:.2f} F{TRAVEL_FEED_RATE}",
        ]

        for cmd in setup_commands:
            if cancel_requested.is_set():
                return False

            if not send_gcode_line(dev, cmd):
                if status_callback and not cancel_requested.is_set():
                    status_callback("Machine rejected a setup command.")
                return False

        time.sleep(1.0)

        if cancel_requested.is_set():
            return False

        commands = speech_text_to_grbl_gcode(text)
        for cmd in commands:
            if cancel_requested.is_set():
                return False

            if not send_gcode_line(dev, cmd):
                if cancel_requested.is_set():
                    return False

                if status_callback:
                    status_callback("Machine rejected a command.")
                return False

        if cancel_requested.is_set():
            return False

        time.sleep(1.0)

        if cancel_requested.is_set():
            return False

        home_command =get_home_command()
        if not send_gcode_line(dev, home_command):
            if status_callback:
                status_callback("Writing finished, but homing failed.")
            return False

        return True

    except ValueError as e:
        if status_callback and not cancel_requested.is_set():
            status_callback(f"Layout error: {e}")
        return False
    except Exception as e:
        if status_callback and not cancel_requested.is_set():
            status_callback(f"Writing error: {e}")
        return False

#image stuff 

selected_image_path = None
image_gcode_commands = []


def get_image_edges(
    image_path,
    error_message="Could not open this image.",
    edge_strength=50,
):
    try:
        edge_strength = int(edge_strength)
    except (TypeError, ValueError) as exc:
        raise ValueError("Edge strength must be a whole number from 0 to 100.") from exc
    if not 0 <= edge_strength <= 100:
        raise ValueError("Edge strength must be between 0 and 100.")

    image = cv2.imread(os.fspath(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(error_message)

    image_height_px, image_width_px = image.shape
    max_dimension = 1200
    scale = min(1.0, max_dimension / max(image_height_px, image_width_px))
    if scale < 1.0:
        image = cv2.resize(
            image,
            (int(image_width_px * scale), int(image_height_px * scale)),
            interpolation=cv2.INTER_AREA,
        )

    denoised = cv2.medianBlur(image, 5)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)

    median = float(np.median(contrast))
    strength = edge_strength / 100.0
    lower_ratio = 0.66 - (0.46 * strength)
    upper_ratio = 1.65 - (0.55 * strength)
    lower_threshold = int(np.clip(median * lower_ratio, 0, 254))
    upper_threshold = int(np.clip(median * upper_ratio, lower_threshold + 1, 255))

    edges = cv2.Canny(contrast, lower_threshold, upper_threshold)
    return edges


def image_size_to_fit(image_path):
    try:
        with Image.open(image_path) as image:
            image_width_px, image_height_px = image.size
    except Exception as exc:
        raise ValueError(f"Could not open this image: {exc}") from exc

    available_width = MAX_X - START_X
    available_height = MAX_Y - MIN_Y
    if available_width <= 0 or available_height <= 0:
        raise ValueError("Machine dimensions leave no usable plotting area.")
    scale = min(available_width / image_width_px, available_height / image_height_px)
    return round(image_width_px * scale, 2), round(image_height_px * scale, 2)


def set_machine_dimensions(width_mm, y_length_mm):
    global MAX_X, MAX_Y, MIN_Y
    width_mm, y_length_mm = float(width_mm), float(y_length_mm)
    if width_mm <= START_X:
        raise ValueError("Machine width must be greater than the starting X position.")
    if y_length_mm <= 0:
        raise ValueError("Machine Y-axis length must be greater than zero.")
    MAX_X = width_mm
    MIN_Y = 0.0
    MAX_Y = y_length_mm
    return {"MAX_X": MAX_X, "MIN_Y": MIN_Y, "MAX_Y": MAX_Y, "width": MAX_X, "y_length": MAX_Y - MIN_Y}

def generate_image_gcode(
    image_path,
    drawing_width=None,
    drawing_height=None,
    edge_strength=50,
    min_contour_length_mm=0.8,
    simplification_tolerance_mm=0.12,
):

    if drawing_width is None or drawing_height is None:
        drawing_width, drawing_height = image_size_to_fit(image_path)
    drawing_width, drawing_height = float(drawing_width), float(drawing_height)
    if drawing_width <= 0 or drawing_height <= 0:
        raise ValueError("Drawing width and height must be positive")

    if START_X + drawing_width > MAX_X:
        raise ValueError("Image is too wide for the configured X area.")

    if drawing_height > MAX_Y - MIN_Y:
        raise ValueError("Image is too tall for the configured Y area.")

    edges = get_image_edges(image_path, edge_strength=edge_strength)
    image_height_px, image_width_px = edges.shape
    mm_per_pixel_x = drawing_width / image_width_px
    mm_per_pixel_y = drawing_height / image_height_px
    average_mm_per_pixel = (mm_per_pixel_x + mm_per_pixel_y) / 2
    minimum_perimeter_px = min_contour_length_mm / average_mm_per_pixel
    simplify_epsilon_px = simplification_tolerance_mm / average_mm_per_pixel

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    commands = ["G21", "G90"]

    def to_machine_xy(px, py):
        x = START_X + (px / image_width_px) * drawing_width
        y = MAX_Y - (py / image_height_px) * drawing_height
        return x, y

    add_pen_up(commands)

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)

        if perimeter < minimum_perimeter_px:
            continue

        approx = cv2.approxPolyDP(
            contour,
            epsilon=simplify_epsilon_px,
            closed=True,
        )

        points = approx.reshape(-1, 2)

        if len(points) < 2:
            continue

        first_x, first_y = to_machine_xy(
            points[0][0],
            points[0][1]
        )

        add_pen_up(commands)
        commands.append(
            f"G0 X{first_x:.2f} Y{first_y:.2f} "
            f"F{TRAVEL_FEED_RATE}"
        )

        add_pen_down(commands)

        for px, py in points[1:]:
            x, y = to_machine_xy(px, py)

            commands.append(
                f"G1 X{x:.2f} Y{y:.2f} "
                f"F{DRAW_FEED_RATE}"
            )

        commands.append(
            f"G1 X{first_x:.2f} Y{first_y:.2f} "
            f"F{DRAW_FEED_RATE}"
        )

        add_pen_up(commands)

    add_pen_up(commands)

    if FIRMWARE.upper() == "MARLIN":
        commands.append("M400")
    else:
        commands.append("G4 P2.0")

    if len(commands) <= 5:
        raise ValueError(
            "No usable outlines found. Try another photo."
        )

    return commands

DEFAULT_SETTINGS = {
    "FIRMWARE": FIRMWARE,
    "BAUD_RATE": BAUD_RATE,
    "DRAW_FEED_RATE": DRAW_FEED_RATE,
    "TRAVEL_FEED_RATE": TRAVEL_FEED_RATE,
    "Z_FEED_RATE": Z_FEED_RATE,
    "FONT_SIZE": FONT_SIZE,
    "START_X": START_X,
    "START_Y": START_Y,
    "MAX_X": MAX_X,
    "MAX_Y": MAX_Y,
    "MIN_Y": MIN_Y,
    "LINE_SPACING": LINE_SPACING,
    "PEN_DOWN_Z": PEN_DOWN_Z,
    "PEN_UP_Z": PEN_UP_Z,
    "WORD_SPACING": WORD_SPACING,
    "WORD_END_PADDING": WORD_END_PADDING,
}


def apply_settings(settings):
    global FIRMWARE, BAUD_RATE, DRAW_FEED_RATE, TRAVEL_FEED_RATE, Z_FEED_RATE
    global FONT_SIZE, START_X, START_Y, MAX_X, MAX_Y, MIN_Y, LINE_SPACING
    global PEN_DOWN_Z, PEN_UP_Z, WORD_SPACING, WORD_END_PADDING

    values = dict(DEFAULT_SETTINGS)
    values["MAX_Y"] = MAX_Y
    values.update(settings)
    numeric_keys = set(DEFAULT_SETTINGS) - {"FIRMWARE", "BAUD_RATE"}
    for key in numeric_keys:
        values[key] = float(values[key])
    values["BAUD_RATE"] = int(values["BAUD_RATE"])
    values["FIRMWARE"] = str(values["FIRMWARE"]).upper()
    if values["FIRMWARE"] not in {"MARLIN", "GRBL"}:
        raise ValueError('FIRMWARE must be either "MARLIN" or "GRBL".')

    for key, value in values.items():
        globals()[key] = value
    return get_settings()


def get_settings():
    return {key: globals()[key] for key in DEFAULT_SETTINGS}


class VoiceScriptController:

    def __init__(self, settings_path=None):
        self.device = None
        self.last_connection_error = None
        self.settings_path = settings_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "voicescript_settings.json"
        )
        self.cancel_event = cancel_requested
        self.selected_image_path = None
        self.image_gcode_commands = []

    @property
    def connected(self):
        return bool(self.device and getattr(self.device, "is_open", True))

    def connect(self, firmware=None, baud_rate=None):
        config = get_settings()
        if firmware is not None:
            config["FIRMWARE"] = firmware
        if baud_rate is not None:
            config["BAUD_RATE"] = baud_rate
        apply_settings(config)
        if self.connected:
            return self.device
        self.device = initialize_machine()
        self.last_connection_error = last_connection_error
        return self.device

    def listen(self):
        return listen_for_text()

    def write_text(self, text, status_callback=None):
        if not self.connected:
            raise RuntimeError("Connect to a machine before writing text.")
        self.cancel_event.clear()
        return write_text(self.device, text, status_callback)

    def fit_image_size(self, image_path):
        return image_size_to_fit(os.fspath(image_path))

    def make_image_gcode(
        self,
        image_path,
        drawing_width=None,
        drawing_height=None,
        edge_strength=50,
    ):
        self.selected_image_path = os.fspath(image_path)
        self.image_gcode_commands = generate_image_gcode(
            self.selected_image_path,
            drawing_width,
            drawing_height,
            edge_strength=edge_strength,
        )
        return list(self.image_gcode_commands)

    def image_outline_preview(self, image_path, max_size=(700, 440)):
        edges = get_image_edges(os.fspath(image_path), "Could not open the image for preview.")
        preview = Image.fromarray(255 - edges)
        preview.thumbnail(max_size)
        return preview

    def print_image(self, image_path=None, drawing_width=None, drawing_height=None,
                    status_callback=None):
        if not self.connected:
            raise RuntimeError("Connect to a machine before printing an image.")
        if image_path is not None:
            commands = self.make_image_gcode(image_path, drawing_width, drawing_height)
        else:
            commands = list(self.image_gcode_commands)
        if not commands:
            raise ValueError("Choose an image and generate its G-code first.")

        self.cancel_event.clear()
        def status(message):
            if status_callback:
                status_callback(message)
        status("Printing image…")
        setup = ["G21", "G90", f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}"]
        for command in setup + commands:
            if self.cancel_event.is_set():
                status("Image printing cancelled — check the machine.")
                return False
            if not send_gcode_line(self.device, command):
                status("Machine rejected an image plotting command.")
                return False
        if self.cancel_event.is_set():
            status("Image printing cancelled — check the machine.")
            return False
        if not send_gcode_line(self.device, get_home_command()):
            status("Image printing finished, but homing failed.")
            return False
        status("Image printing finished")
        return True

    def home(self):
        if not self.connected:
            raise RuntimeError("Connect to the machine before homing.")
        return send_gcode_line(self.device, get_home_command())

    def pen_up(self):
        if not self.connected:
            raise RuntimeError("Connect to the machine before moving the pen.")
        return send_gcode_line(self.device, f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}")

    def pen_down(self):
        if not self.connected:
            raise RuntimeError("Connect to the machine before moving the pen.")
        return send_gcode_line(self.device, f"G1 Z{PEN_DOWN_Z:.2f} F{Z_FEED_RATE}")

    def stop(self):
        self.cancel_event.set()
        if self.connected:
            try:
                if FIRMWARE.upper() == "MARLIN":
                    self.device.write(b"M410\n")
                else:
                    self.device.write(b"!")
                self.device.flush()
            except Exception:
                pass

    def save_settings(self):
        with open(self.settings_path, "w", encoding="utf-8") as file:
            json.dump(get_settings(), file, indent=4)

    def load_settings(self):
        with open(self.settings_path, "r", encoding="utf-8") as file:
            return apply_settings(json.load(file))

    def close(self):
        if self.device:
            try:
                if getattr(self.device, "is_open", True):
                    send_gcode_line(self.device, f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}")
                    self.device.close()
            finally:
                self.device = None
