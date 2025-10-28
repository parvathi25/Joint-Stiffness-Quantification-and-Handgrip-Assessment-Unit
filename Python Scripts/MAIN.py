import sys
import os
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import serial
import threading
import time
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

# ----- Serial Setup -----
SERIAL_PORT = "COM3"  # Update as needed
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

# ----- Data Storage for Plotting -----
sensor_data = {
    "FSR": [],
    "Weight": []
}

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
                    with open(app.csv_filename, mode="a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([ts_str, value, sensor_type])

                    if sensor_type in sensor_data:
                        sensor_data[sensor_type].append((now - start_time, value))

                except ValueError:
                    print("Invalid data received:", line)
        time.sleep(0.1)

serial_thread = threading.Thread(target=serial_reader, daemon=True)
serial_thread.start()

# ----- Analysis Functions -----
def read_data(file_path: str):
    """
    Read the grip strength data from a CSV file.
    Expected columns: 'Timestamp', 'Value', 'Sensor'.
    """
    data = pd.read_csv(file_path, parse_dates=['Timestamp'])
    # Filter data for only weight sensor values
    data = data[data['Sensor'] == 'Weight']
    # Reset index for convenience
    data.reset_index(drop=True, inplace=True)
    # Convert Timestamp to elapsed time in seconds
    data['Time'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
    data.rename(columns={'Value': 'Grip_Strength'}, inplace=True)
    return data[['Time', 'Grip_Strength']]

def calculate_plateau_coefficient(data):
    max_hgs = data['Grip_Strength'].max()
    threshold = 0.9 * max_hgs
    plateau_region = data[data['Grip_Strength'] >= threshold]

    if plateau_region.empty:
        return None  # No plateau region found

    plateau_mean = plateau_region['Grip_Strength'].mean()
    plateau_std = plateau_region['Grip_Strength'].std()

    coefficient_of_variation = (plateau_std * 100) / plateau_mean
    return coefficient_of_variation

def find_peak_grip_strength(data):
    peak_hgs = data['Grip_Strength'].max()
    peak_time = data.loc[data['Grip_Strength'].idxmax(), 'Time']
    return peak_hgs, peak_time

def find_time_for_percentages(data, percentages):
    results = {}
    max_hgs, peak_time = find_peak_grip_strength(data)

    # Consider only the data points after the peak is reached
    post_peak_data = data[data['Time'] >= peak_time]

    for percentage in percentages:
        target = max_hgs * (percentage / 100)
        subset = post_peak_data[post_peak_data['Grip_Strength'] <= target]

        if not subset.empty:
            results[percentage] = subset.iloc[0]['Time'] - peak_time
        else:
            results[percentage] = None

    return results

# ----- GUI Application -----
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Arduino Control & Data Logging")
        self.geometry("900x700")
        
        self.csv_filename = None
        self.prompt_for_filename()
        if not self.csv_filename:
            print("No file selected. Exiting.")
            ser.close()
            self.destroy()
            return

        # CSV Setup
        with open(self.csv_filename, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Value", "Sensor"])
        
        # Control Frame: Buttons for mode selection
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.btn_mode1 = ttk.Button(control_frame, text="Grip Strength", command=lambda: self.send_command("1"))
        self.btn_mode1.pack(side=tk.LEFT, padx=5)
        
        self.btn_mode2 = ttk.Button(control_frame, text="Joint Stiffness", command=lambda: self.send_command("2"))
        self.btn_mode2.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=lambda: self.send_command("3"))
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        # Analysis Button
        self.btn_analysis = ttk.Button(control_frame, text="Analysis", command=self.run_analysis)
        self.btn_analysis.pack(side=tk.LEFT, padx=5)
        
        # Matplotlib Figure with Two Subplots
        self.fig, (self.ax_fsr, self.ax_weight) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        self.fig.tight_layout(pad=3.0)
        
        self.ax_fsr.set_title("FSR Force-Time")
        self.ax_fsr.set_ylabel("FSR Reading")
        
        self.ax_weight.set_title("Weight-Time")
        self.ax_weight.set_ylabel("Weight (units?)")
        self.ax_weight.set_xlabel("Time (s)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Start animation to update plot every 1 second
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=1000)

        # Analysis Output Frame
        analysis_frame = ttk.LabelFrame(self, text="Analysis Output")
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.analysis_output = scrolledtext.ScrolledText(analysis_frame, wrap=tk.WORD, height=10)
        self.analysis_output.pack(fill=tk.BOTH, expand=True)

        # Redirect stdout to the analysis_output Text widget
        sys.stdout = TextRedirector(self.analysis_output)

    def prompt_for_filename(self):
        self.csv_filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV File As"
        )

    def send_command(self, cmd):
        try:
            ser.write(cmd.encode())
            print(f"Sent command: {cmd}")
            if cmd == "3":  # If Mode 3 (Stop) is pressed, exit the program.
                time.sleep(0.5)
                self.destroy()  # Closes the GUI and ends the mainloop.
        except Exception as e:
            print("Error sending command:", e)

    def run_analysis(self):
        try:
            data = read_data(self.csv_filename)
            peak_hgs, peak_time = find_peak_grip_strength(data)
            plateau_coefficient = calculate_plateau_coefficient(data)
            percentages = [80, 75, 50, 25]
            time_to_percentages = find_time_for_percentages(data, percentages)

            print("\nAnalysis Results:")
            print(f"Peak Grip Strength: {peak_hgs:.2f} units at {peak_time:.2f} seconds")
            if plateau_coefficient is not None:
                print(f"Plateau Coefficient of Variation: {plateau_coefficient:.2f}%")
            else:
                print("No plateau region detected.")
            for perc, t in time_to_percentages.items():
                if t is not None:
                    print(f"Time to {perc}% of Peak: {t:.2f} seconds")
                else:
                    print(f"Time to {perc}% of Peak: Not reached")

        except Exception as e:
            print(f"Error running analysis: {e}")

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

# Redirector Class for Text Widget
class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)  # Auto-scroll to the bottom

    def flush(self):
        pass

# Initialize and run the application
app = App()
app.mainloop()

# Close the serial port when the GUI closes
ser.close()