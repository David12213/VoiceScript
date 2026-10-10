
# VoiceScript: speech-to-physical-text for a 3-axis & 2-axis pen plotter / 3D printer / laser cutter / anything that reads g-code
# Press Control+C to shut off the machine at any time.

import glob
import time
import HersheyFonts
import serial
import speech_recognition as sr
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os

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
MIN_Y = 0.0
LINE_SPACING = 20.0

#smaller Z lowers it
PEN_DOWN_Z = 0.7
PEN_UP_Z = 3.5

WORD_SPACING = FONT_SIZE * 0.3
WORD_END_PADDING = FONT_SIZE * 0.2
COMMAND_TIMEOUT = 100.0


def auto_discover_machine_port():
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
                return False

        time.sleep(0.005)

    return False


def initialize_machine():
    port_path = auto_discover_machine_port()

    if not port_path:
        return None

    try:
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

        return dev

    except Exception as e:
        pass
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


def listen_for_text():
    """Listen once and return the recognized words without moving the machine."""
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.0

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)

    return recognizer.recognize_google(audio).capitalize()


def write_text(dev, text, status_callback=None):
    """Write previously confirmed text to the machine."""
    try:
        if status_callback:
            status_callback("Writing...")

        # Check cancellation before sending setup commands.
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

        home_command = "G28" if FIRMWARE.upper() == "MARLIN" else "$H"
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

#UI
machine_device = None
is_busy = False
pending_text = None
cancel_requested = threading.Event()

SETTINGS_FILE = "voicescript_settings.json"


def get_settings():
    return {
        "FIRMWARE": firmware_var.get(),
        "BAUD_RATE": int(baud_var.get()),

        "DRAW_FEED_RATE": float(draw_speed_var.get()),
        "TRAVEL_FEED_RATE": float(travel_speed_var.get()),
        "Z_FEED_RATE": float(z_speed_var.get()),

        "FONT_SIZE": float(font_size_var.get()),

        "START_X": float(start_x_var.get()),
        "START_Y": float(start_y_var.get()),
        "MAX_X": float(max_x_var.get()),
        "MIN_Y": float(min_y_var.get()),
        "LINE_SPACING": float(line_spacing_var.get()),

        "PEN_DOWN_Z": float(pen_down_var.get()),
        "PEN_UP_Z": float(pen_up_var.get()),

        "WORD_SPACING": float(word_spacing_var.get()),
        "WORD_END_PADDING": float(word_padding_var.get()),
    }


def apply_settings():
    global FIRMWARE
    global BAUD_RATE
    global DRAW_FEED_RATE
    global TRAVEL_FEED_RATE
    global Z_FEED_RATE
    global FONT_SIZE
    global START_X
    global START_Y
    global MAX_X
    global MIN_Y
    global LINE_SPACING
    global PEN_DOWN_Z
    global PEN_UP_Z
    global WORD_SPACING
    global WORD_END_PADDING

    try:
        settings = get_settings()

        FIRMWARE = settings["FIRMWARE"]
        BAUD_RATE = settings["BAUD_RATE"]

        DRAW_FEED_RATE = settings["DRAW_FEED_RATE"]
        TRAVEL_FEED_RATE = settings["TRAVEL_FEED_RATE"]
        Z_FEED_RATE = settings["Z_FEED_RATE"]

        FONT_SIZE = settings["FONT_SIZE"]

        START_X = settings["START_X"]
        START_Y = settings["START_Y"]
        MAX_X = settings["MAX_X"]
        MIN_Y = settings["MIN_Y"]
        LINE_SPACING = settings["LINE_SPACING"]

        PEN_DOWN_Z = settings["PEN_DOWN_Z"]
        PEN_UP_Z = settings["PEN_UP_Z"]

        WORD_SPACING = settings["WORD_SPACING"]
        WORD_END_PADDING = settings["WORD_END_PADDING"]

        status_var.set("Settings applied")
        status_label.config(foreground="#198754")

    except ValueError:
        messagebox.showerror(
            "Invalid setting",
            "Please make sure every setting has a valid number."
        )


def save_settings():
    try:
        apply_settings()

        settings = get_settings()

        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)

        status_var.set("Settings saved")
        status_label.config(foreground="#198754")

    except Exception as e:
        messagebox.showerror("Save Error", str(e))


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        messagebox.showinfo(
            "No saved settings",
            "No settings file was found."
        )
        return

    try:
        with open(SETTINGS_FILE, "r") as file:
            settings = json.load(file)

        firmware_var.set(settings["FIRMWARE"])
        baud_var.set(str(settings["BAUD_RATE"]))

        draw_speed_var.set(str(settings["DRAW_FEED_RATE"]))
        travel_speed_var.set(str(settings["TRAVEL_FEED_RATE"]))
        z_speed_var.set(str(settings["Z_FEED_RATE"]))

        font_size_var.set(str(settings["FONT_SIZE"]))

        start_x_var.set(str(settings["START_X"]))
        start_y_var.set(str(settings["START_Y"]))
        max_x_var.set(str(settings["MAX_X"]))
        min_y_var.set(str(settings["MIN_Y"]))
        line_spacing_var.set(str(settings["LINE_SPACING"]))

        pen_down_var.set(str(settings["PEN_DOWN_Z"]))
        pen_up_var.set(str(settings["PEN_UP_Z"]))

        word_spacing_var.set(str(settings["WORD_SPACING"]))
        word_padding_var.set(str(settings["WORD_END_PADDING"]))

        apply_settings()

        status_var.set("Settings loaded")
        status_label.config(foreground="#198754")

    except Exception as e:
        messagebox.showerror("Load Error", str(e))


def connect_machine():
    global machine_device

    if machine_device:
        messagebox.showinfo("VoiceScript", "Machine is already connected.")
        return

    apply_settings()

    status_var.set("Searching for machine...")
    status_label.config(foreground="#d97706")

    def connect():
        global machine_device

        machine_device = initialize_machine()

        if machine_device:
            root.after(
                0,
                lambda: (
                    status_var.set("Connected"),
                    status_label.config(foreground="#198754"),
                    connect_button.config(state="disabled"),
                    speak_button.config(state="normal"),
                    home_button.config(state="normal"),
                )
            )
        else:
            root.after(
                0,
                lambda: (
                    status_var.set("Machine not found"),
                    status_label.config(foreground="#dc3545"),
                )
            )

    threading.Thread(target=connect, daemon=True).start()


def speak():
    global is_busy, pending_text

    if not machine_device:
        messagebox.showwarning(
            "Not connected",
            "Connect VoiceScript to the machine first."
        )
        return

    if is_busy:
        return

    if pending_text is not None:
        text_to_write = pending_text
        pending_text = None
        cancel_requested.clear()
        is_busy = True
        speak_button.config(state="disabled", text="Writing...")
        stop_button.config(state="normal")
        retalk_button.config(state="disabled")
        status_var.set("Writing...")
        status_label.config(foreground="#d97706")

        def update_activity(message):
            root.after(
                0,
                lambda: (
                    status_var.set(message),
                    status_label.config(foreground="#d97706"),
                )
            )

        def run_write():
            global is_busy
            write_text(machine_device, text_to_write, update_activity)
            is_busy = False
            root.after(0, finish_writing)

        threading.Thread(target=run_write, daemon=True).start()
        return

    apply_settings()
    is_busy = True
    speak_button.config(state="disabled", text="Listening...")
    stop_button.config(state="disabled")
    status_var.set("Listening...")
    status_label.config(foreground="#d97706")
    recognized_text_var.set("")

    def run_listen():
        global is_busy
        try:
            text = listen_for_text()
            root.after(0, lambda recognized=text: show_recognized_text(recognized))
        except sr.WaitTimeoutError:
            root.after(0, lambda: show_listen_error("No speech detected. Please try again."))
        except sr.UnknownValueError:
            root.after(0, lambda: show_listen_error("Couldn't understand the speech. Please try again."))
        except sr.RequestError as e:
            root.after(0, lambda error=str(e): show_listen_error(f"Speech recognition error: {error}"))
        except Exception as e:
            root.after(0, lambda error=str(e): show_listen_error(f"Listening error: {error}"))
        finally:
            is_busy = False

    threading.Thread(target=run_listen, daemon=True).start()


def retalk():
    global pending_text

    if is_busy:
        return

    # Discard the previous recognized words
    pending_text = None
    recognized_text_var.set("")

    # Start a new recording
    retalk_button.config(state="disabled")
    speak_button.config(state="normal", text="Speak & Review")

    speak()


def stop_machine():
    global pending_text

    cancel_requested.set()
    pending_text = None

    if machine_device and machine_device.is_open:
        try:
            if FIRMWARE.upper() == "MARLIN":
                machine_device.write(b"M410\n")
                machine_device.flush()
            elif FIRMWARE.upper() == "GRBL":
                machine_device.write(b"!")
                machine_device.flush()
        except Exception:
            pass

    speak_button.config(state="disabled", text="Stopping...")
    stop_button.config(state="disabled")
    status_var.set("STOP requested — check the machine.")
    status_label.config(foreground="#dc3545")


def show_recognized_text(text):
    global pending_text
    pending_text = text
    recognized_text_var.set(text)
    speak_button.config(state="normal", text="Confirm & Write")
    retalk_button.config(state="normal")
    stop_button.config(state="disabled")
    status_var.set("Check the words above, then click Confirm & Write.")
    status_label.config(foreground="#198754")


def show_listen_error(message):
    global pending_text
    pending_text = None
    recognized_text_var.set("")
    speak_button.config(state="normal", text="Speak & Review")
    retalk_button.config(state="disabled")
    stop_button.config(state="disabled")
    status_var.set(message)
    status_label.config(foreground="#dc3545")


def finish_writing():
    speak_button.config(state="normal", text="Speak & Review")
    retalk_button.config(state="disabled")
    stop_button.config(state="disabled")

    if cancel_requested.is_set():
        status_var.set("Writing cancelled — check the machine before restarting.")
        status_label.config(foreground="#dc3545")
    else:
        status_var.set("Ready — click Speak & Review to begin again.")
        status_label.config(foreground="#198754")


def home_machine():
    if not machine_device:
        return

    def home():
        if FIRMWARE.upper() == "MARLIN":
            send_gcode_line(machine_device, "G28")
        else:
            send_gcode_line(machine_device, "$H")

        root.after(
            0,
            lambda: status_var.set("Machine homed")
        )

    threading.Thread(target=home, daemon=True).start()


def test_pen_up():
    if not machine_device:
        messagebox.showwarning("Not connected", "Connect the machine first.")
        return

    apply_settings()

    def move():
        send_gcode_line(
            machine_device,
            f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}"
        )

        root.after(
            0,
            lambda: status_var.set("Pen raised")
        )

    threading.Thread(target=move, daemon=True).start()


def test_pen_down():
    if not machine_device:
        messagebox.showwarning("Not connected", "Connect the machine first.")
        return

    apply_settings()

    def move():
        send_gcode_line(
            machine_device,
            f"G1 Z{PEN_DOWN_Z:.2f} F{Z_FEED_RATE}"
        )

        root.after(
            0,
            lambda: status_var.set("Pen lowered")
        )

    threading.Thread(target=move, daemon=True).start()


def close_program():
    global machine_device

    if machine_device:
        try:
            send_gcode_line(
                machine_device,
                f"G0 Z{PEN_UP_Z:.2f} F{Z_FEED_RATE}"
            )
            machine_device.close()
        except:
            pass

    root.destroy()


#UI setup
root = tk.Tk()
root.configure(bg="#2E2E2E")

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "TFrame",
    background="#474747"
)

style.configure(
    "TLabel",
    background="#2E2E2E",
    foreground="#F0F0F0"
)

style.configure(
    "TButton",
    background="#2E2E2E",
    foreground="#F0F0F0"
)

style.configure(
    "TEntry",
    fieldbackground="#2E2E2E",
    foreground="#F0F0F0"
)

style.configure(
    "Title.TLabel",
    font=("Helvetica", 24, "bold")
)

style.configure(
    "Subtitle.TLabel",
    font=("Helvetica", 11)
)

style.configure(
    "Section.TLabelframe.Label",
    font=("Helvetica", 11, "bold")
)

style.configure(
    "Big.TButton",
    font=("Helvetica", 12, "bold"),
    padding=10
)

firmware_var = tk.StringVar(value=FIRMWARE)
baud_var = tk.StringVar(value=str(BAUD_RATE))

draw_speed_var = tk.StringVar(value=str(DRAW_FEED_RATE))
travel_speed_var = tk.StringVar(value=str(TRAVEL_FEED_RATE))
z_speed_var = tk.StringVar(value=str(Z_FEED_RATE))

font_size_var = tk.StringVar(value=str(FONT_SIZE))

start_x_var = tk.StringVar(value=str(START_X))
start_y_var = tk.StringVar(value=str(START_Y))
max_x_var = tk.StringVar(value=str(MAX_X))
min_y_var = tk.StringVar(value=str(MIN_Y))
line_spacing_var = tk.StringVar(value=str(LINE_SPACING))

pen_down_var = tk.StringVar(value=str(PEN_DOWN_Z))
pen_up_var = tk.StringVar(value=str(PEN_UP_Z))

word_spacing_var = tk.StringVar(value=str(WORD_SPACING))
word_padding_var = tk.StringVar(value=str(WORD_END_PADDING))

status_var = tk.StringVar(value="Not connected")

title = ttk.Label(
    root,
    text="VoiceScript",
    style="Title.TLabel"
)
title.pack(pady=(18, 2))

subtitle = ttk.Label(
    root,
    text="Write what you speak!",
    style="Subtitle.TLabel"
)
subtitle.pack(pady=(0, 15))

connection_frame = ttk.LabelFrame(
    root,
    text="Machine (Marlin for 3D printer, GRBL for laser cutter)",
    padding=12
)
connection_frame.pack(
    fill="x",
    padx=25,
    pady=5
)

ttk.Label(
    connection_frame,
    text="Firmware:"
).grid(row=0, column=0, sticky="w", padx=5, pady=5)

firmware_menu = ttk.Combobox(
    connection_frame,
    textvariable=firmware_var,
    values=["MARLIN", "GRBL"],
    state="readonly",
    width=15
)
firmware_menu.grid(row=0, column=1, sticky="w", padx=5, pady=5)

ttk.Label(
    connection_frame,
    text="Baud rate: (Different based on 3d printer)"
).grid(row=0, column=2, sticky="w", padx=(25, 5), pady=5)

baud_menu = ttk.Combobox(
    connection_frame,
    textvariable=baud_var,
    values=["115200", "250000"],
    state="readonly",
    width=12
)
baud_menu.grid(row=0, column=3, sticky="w", padx=5, pady=5)

connect_button = ttk.Button(
    connection_frame,
    text="CONNECT",
    command=connect_machine,
    style="Big.TButton"
)
connect_button.grid(
    row=1,
    column=0,
    columnspan=4,
    sticky="ew",
    padx=5,
    pady=(10, 3)
)

writing_frame = ttk.LabelFrame(
    root,
    text="Writing & Spacing (Adjust to your machine)",
    padding=12
)
writing_frame.pack(
    fill="x",
    padx=25,
    pady=5
)

# reuse label
def add_setting(parent, label, variable, row, column, entry_width=12):
    ttk.Label(
        parent,
        text=label + ":"
    ).grid(
        row=row,
        column=column,
        sticky="w",
        padx=5,
        pady=5
    )

    ttk.Entry(
        parent,
        textvariable=variable,
        width=entry_width
    ).grid(
        row=row,
        column=column + 1,
        sticky="w",
        padx=5,
        pady=5
    )


writing_settings = [
    ("Font size", font_size_var),
    ("Start X", start_x_var),
    ("Start Y", start_y_var),
    ("Maximum X", max_x_var),
    ("Minimum Y", min_y_var),
    ("Line spacing", line_spacing_var),
]

for i, (label, variable) in enumerate(writing_settings):
    row = i // 2
    column = (i % 2) * 2
    add_setting(writing_frame, label, variable, row, column)

speed_frame = ttk.LabelFrame(
    root,
    text="Speed",
    padding=12
)
speed_frame.pack(
    fill="x",
    padx=25,
    pady=5
)

speed_settings = [
    ("Drawing speed", draw_speed_var),
    ("Travel speed", travel_speed_var),
    ("Z speed", z_speed_var),
]

for i, (label, variable) in enumerate(speed_settings):
    add_setting(speed_frame, label, variable, 0, i * 2, entry_width=10)

pen_frame = ttk.LabelFrame(
    root,
    text="Pen",
    padding=12
)
pen_frame.pack(
    fill="x",
    padx=25,
    pady=5
)

add_setting(pen_frame, "Pen down Z", pen_down_var, 0, 0)
add_setting(pen_frame, "Pen up Z", pen_up_var, 0, 2)

control_frame = ttk.Frame(root)
control_frame.pack(
    fill="x",
    padx=25,
    pady=12
)

home_button = ttk.Button(
    control_frame,
    text="HOME",
    command=home_machine,
    state="disabled"
)
home_button.grid(row=0, column=0, padx=5, sticky="ew")

test_up_button = ttk.Button(
    control_frame,
    text="PEN UP",
    command=test_pen_up
)
test_up_button.grid(row=0, column=1, padx=5, sticky="ew")

test_down_button = ttk.Button(
    control_frame,
    text="PEN DOWN",
    command=test_pen_down
)
test_down_button.grid(row=0, column=2, padx=5, sticky="ew")

for i in range(3):
    control_frame.columnconfigure(i, weight=1)


speak_button = ttk.Button(
    root,
    text="Speak & Review",
    command=speak,
    state="disabled",
    style="Big.TButton"
)
speak_button.pack(
    fill="x",
    padx=25,
    pady=(2, 10)
)


retalk_button = ttk.Button(
    root,
    text="Retalk / Try Again",
    command=retalk,
    state="disabled",
    style="Big.TButton"
)
retalk_button.pack(
    fill="x",
    padx=25,
    pady=(0, 10)
)


stop_button = ttk.Button(
    root,
    text="STOP / CANCEL",
    command=stop_machine,
    state="disabled",
    style="Big.TButton"
)
stop_button.pack(
    fill="x",
    padx=25,
    pady=(0, 10)
)

recognized_frame = ttk.LabelFrame(
    root,
    text="Recognized words — review before writing",
    padding=12
)
recognized_frame.pack(
    fill="x",
    padx=25,
    pady=(4, 8)
)

recognized_text_var = tk.StringVar(value="Your recognized words will appear here.")

recognized_text_label = ttk.Label(
    recognized_frame,
    textvariable=recognized_text_var,
    wraplength=700,
    justify="left",
    anchor="w"
)
recognized_text_label.pack(fill="x")

settings_frame = ttk.Frame(root)
settings_frame.pack(
    fill="x",
    padx=25,
    pady=3
)

ttk.Button(
    settings_frame,
    text="Apply Settings",
    command=apply_settings
).grid(row=0, column=0, padx=5, sticky="ew")

ttk.Button(
    settings_frame,
    text="Save Settings",
    command=save_settings
).grid(row=0, column=1, padx=5, sticky="ew")

ttk.Button(
    settings_frame,
    text="Load Settings",
    command=load_settings
).grid(row=0, column=2, padx=5, sticky="ew")

for i in range(3):
    settings_frame.columnconfigure(i, weight=1)

status_label = ttk.Label(
    root,
    textvariable=status_var,
    font=("Helvetica", 11, "bold")
)
status_label.pack(
    pady=(12, 5)
)

root.protocol("WM_DELETE_WINDOW", close_program)

root.mainloop()