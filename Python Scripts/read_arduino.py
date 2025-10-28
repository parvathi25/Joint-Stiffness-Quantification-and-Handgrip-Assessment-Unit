import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import asksaveasfilename
import serial
import threading
import time
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

# ----- Serial Setup -----
SERIAL_PORT = "COM3"      # Update as needed
BAUD_RATE = 9600
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # Allow Arduino to initialize
ser.reset_input_buffer()  # Clear any junk data

print("Waiting for Arduino to be ready...")
while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors="ignore").strip()
        if "READY" in line:
            print("Arduino is ready!")
            break

# ----- Prompt User for CSV Filename -----
# Initialize a hidden Tkinter root for the file dialog.
root = tk.Tk()
root.withdraw()  # Hide the root window

def get_csv_filename():
    # Prompt user to select a file name and location
    file_path = asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save CSV File As"
    )
    return file_path

CSV_FILENAME = get_csv_filename()
if not CSV_FILENAME:
    print("No file selected. Exiting.")
    ser.close()
    exit()

# ----- CSV Setup -----
with open(CSV_FILENAME, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Value", "Sensor"])

# ----- Data Storage for Plotting -----
# We'll keep separate lists for FSR and Weight data.
sensor_data = {
    "FSR": [],
    "Weight": []
}

# Store the time when the first data point arrives, so we can plot relative time (0s start).
start_time = None

# ----- Serial Reading Thread -----
def serial_reader():
    global start_time
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors="ignore").strip()
            if "," in line:
                try:
                    value_str, sensor_type = line.split(",")
                    value = float(value_str)
                    now = time.time()
                    
                    if start_time is None:
                        start_time = now

                    ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    with open(CSV_FILENAME, mode="a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([ts_str, value, sensor_type])

                    if sensor_type in sensor_data:
                        sensor_data[sensor_type].append((now - start_time, value))

                except ValueError:
                    print("Invalid data received:", line)
        time.sleep(0.1)

serial_thread = threading.Thread(target=serial_reader, daemon=True)
serial_thread.start()

# ----- GUI Application -----
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Arduino Control & Data Logging")
        self.geometry("900x700")
        
        # Control Frame: Buttons for mode selection
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.btn_mode1 = ttk.Button(control_frame, text="Grip Strength", command=lambda: self.send_command("1"))
        self.btn_mode1.pack(side=tk.LEFT, padx=5)
        
        self.btn_mode2 = ttk.Button(control_frame, text="Joint Stiffness", command=lambda: self.send_command("2"))
        self.btn_mode2.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=lambda: self.send_command("3"))
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        # Matplotlib Figure with Two Subplots
        self.fig, (self.ax_fsr, self.ax_weight) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        self.fig.tight_layout(pad=3.0)
        
        self.ax_fsr.set_title("FSR Force-Time")
        self.ax_fsr.set_ylabel("FSR Reading")
        
        self.ax_weight.set_title("Load Cell Weight-Time")
        self.ax_weight.set_ylabel("Weight (units?)")
        self.ax_weight.set_xlabel("Time (s)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Start animation to update plot every 1 second
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=1000)
        
    def send_command(self, cmd):
        try:
            ser.write(cmd.encode())
            print(f"Sent command: {cmd}")
            if cmd == "3":  # If Mode 3 (Stop) is pressed, exit the program.
                time.sleep(0.5)
                self.destroy()  # Closes the GUI and ends the mainloop.
        except Exception as e:
            print("Error sending command:", e)
    
    def update_plot(self, frame):
        # Clear each subplot
        self.ax_fsr.clear()
        self.ax_weight.clear()
        
        # Redraw titles, labels
        self.ax_fsr.set_title("FSR Force-Time")
        self.ax_fsr.set_ylabel("FSR Reading")
        self.ax_fsr.set_xlabel("Time (s)")
        
        self.ax_weight.set_title("Load Cell Weight-Time")
        self.ax_weight.set_ylabel("Weight")
        self.ax_weight.set_xlabel("Time (s)")
        
        # Plot FSR data if available
        if sensor_data["FSR"]:
            times, forces = zip(*sensor_data["FSR"])
            self.ax_fsr.plot(times, forces, marker=".", linestyle="-", markersize=3, linewidth=1)
        
        # Plot Weight data if available
        if sensor_data["Weight"]:
            times, weights = zip(*sensor_data["Weight"])
            self.ax_weight.plot(times, weights, marker=".", linestyle="-", markersize=3, linewidth=1)
        
        self.canvas.draw()

# Create and start the GUI application.
app = App()
app.mainloop()

# Close the serial port when the GUI closes.
ser.close()