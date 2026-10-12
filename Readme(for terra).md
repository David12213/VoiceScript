# UI and Image outline generator for Voicescript 
> For project reviewers of Terra: This readme is specifically for Terra. Everything I mention here was added for Terra. This project originally began in Stardance (everything I did for Stardance is apart of the original README.md). The UI + the code for image generation (SO basically the talk_to_plot.ui,py file) has NOT been submitted to Stardance, Instead I am submitting this for Terra. I promise im not double dipping. 

## A working UI that makes my VoiceScript Project much more accesible, as well as a image to g code function that creates a outline of a inputted photo. 

<img width="1439" height="869" alt="Screenshot 2026-10-11 at 5 41 09 PM" src="https://github.com/user-attachments/assets/8dee17b6-be69-4ffa-b7c0-856b70ad849f" />
<img width="1443" height="368" alt="Screenshot 2026-10-11 at 5 41 24 PM" src="https://github.com/user-attachments/assets/27018ff2-790c-438e-919d-290b5773d349" />

I created this UI to make it more usable to anyone who uses my code, as going back to manually change values gets annoying and repetitive. This UI includes:
- Settings to change the x and y dimensions according to the dimensions of your machine
- The ability to change font size
- The ability to choose drawing speed and baud rate
- a chance to change between GRBL (Laser Cutters) or MARLIN (3D Printers)
- The ability to save and load your own settings
- A button to record, and a button to re-record
- An emergency cancel button (which I should've added sooner)
Additionally, I added a function where you can input an image and receive an outline of it in Gcode, allowing you to also print it. Essentially, you can upload a photo of something, the program will show you the outline it created, and you can then send it to your connected machine. The photo below shows an example with a photo of my cat.
