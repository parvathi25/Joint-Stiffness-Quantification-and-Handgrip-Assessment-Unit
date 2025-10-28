import sys
import os
import pandas as pd
import numpy as np

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

def main():
    if len(sys.argv) != 2:
        print("Usage: python analysistest.py <csv_filename>")
        sys.exit(1)

    # Retrieve the filename from the command-line arguments
    file_name = sys.argv[1]

    # Ensure the file is in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, file_name)

    # Check if the file exists
    if not os.path.isfile(file_path):
        print(f"Error: The file '{file_name}' does not exist in the directory '{script_dir}'.")
        sys.exit(1)

    # Proceed with data analysis using 'file_path'
    data = read_data(file_path)

    plateau_cv = calculate_plateau_coefficient(data)
    peak_strength, peak_time = find_peak_grip_strength(data)

    time_for_percentages = find_time_for_percentages(data, [25, 50, 75, 80])

    print(f"Plateau Coefficient of Variation: {plateau_cv:.2f}")
    print(f"Peak Grip Strength: {peak_strength} kg at {peak_time} seconds")

    for perc, time in time_for_percentages.items():
        if time is not None:
            print(f"Time to reach {perc}% of max grip strength: {time:.2f} seconds")
        else:
            print(f"{perc}% of max grip strength was not reached during the recording.")

if __name__ == "__main__":
    main()