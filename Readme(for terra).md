# UI and Image outline generator for Voicescript 
> For project reviewers of Terra: This readme is specifically for Terra. Everything I mention here was added for Terra. This project originally began in Stardance (everything I did for Stardance is apart of the original README.md). The UI + the code for image generation ( the talk_to_plot_ui.py file) has NOT been submitted to Stardance, Instead I am submitting this for Terra. I promise I'm not double dipping. Essentially, The code that I tracked and submitted to terra is everything in the [talk_to_plot_ui.py](https://github.com/David12213/VoiceScript/blob/dc171e4cdc6c00d23495feb74db87279fd737f9d/talk_to_plot_ui.py) file. Everything else is from the past and ISN'T part of my submission. 

## A working UI that makes my VoiceScript Project much more accessible, as well as an image to g code function that creates an outline of an inputted photo. Coded purely in Python, and UI was made with Tkinter.

<img width="1439" height="869" alt="Screenshot 2026-10-11 at 5 41 09 PM" src="https://github.com/user-attachments/assets/8dee17b6-be69-4ffa-b7c0-856b70ad849f" />
<img width="1443" height="368" alt="Screenshot 2026-10-11 at 5 41 24 PM" src="https://github.com/user-attachments/assets/27018ff2-790c-438e-919d-290b5773d349" />

# How to use it:
1. Run the [talk_to_plot_ui.py](https://github.com/David12213/VoiceScript/blob/dc171e4cdc6c00d23495feb74db87279fd737f9d/talk_to_plot_ui.py) file
2. Look at the UI, play around, and try saving & loading settings
3. Upload a photo and see the outline created by the program
4. (optional) If you have a 3d printer or laser cutter, connect it to your device and click the print button to watch it be drawn out (tape a pen to the head).
> All the coding I did for this project was for the UI, so the printing is optional, although thats how it's meant to tie into this whole repo. The UI itself is usable by anyone.

I created this UI to make it more usable to anyone who uses my code, as going back to manually change values gets annoying and repetitive. This UI includes:
- Settings to change the x and y dimensions according to the dimensions of your machine
- The ability to change font size
- The ability to choose drawing speed and baud rate
- a chance to change between GRBL (Laser Cutters) or MARLIN (3D Printers)
- The ability to save and load your own settings
- A button to record, and a button to re-record
- An emergency cancel button (which I should've added sooner)
  
Additionally, I added a function where you can input an image and receive an outline of it in Gcode, allowing you to also print it. Essentially, you can upload a photo of something, the program will show you the outline it created, and you can then send it to your connected machine. The photo below shows an example with a photo of a f-35 blueprint I found online.
<img width="1470" height="700" alt="Screenshot 2026-10-12 at 12 25 09 AM" src="https://github.com/user-attachments/assets/69c442c3-6bdd-4937-a22c-c833c6e4e170" />

> Note: This is a very soft launch. The scroll doesn't fully work on the UI and will not scale landscape photos accurately certain times.

# Requirements: 
Python 3.12.10 (I use 3.15 but I test with 3.12.10 and it works)
The following Python Libraries:
- HersheyFonts
- pyserial
- SpeechRecognition
- PyAudio (Speech Recognition uses it)
- tkinter (if not pre-installed)
- opencv-python
- Pillow
> Note: Not all these libraries are used for the UI, some are for the rest of the project. However, all of these libraries are needed for it to work as intended since the UI is based off of my project (aka the rest of the repository).