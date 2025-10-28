import sys
import os
import pandas as pd
import numpy as np

def read_data(file_path: str, sensor_type: str):
    """
    Read the data from a CSV file based on the sensor type.
    Expected columns: 'Timestamp', 'Value', 'Sensor'.
    """
    data = pd.read_csv(file_path, parse_dates=['Timestamp'])
    # Filter data for the specified sensor type
    data = data[data['Sensor'] == sensor_type]
    # Reset index for convenience
    data.reset_index(drop=True, inplace=True)
    # Convert Timestamp to elapsed time in seconds
    data['Time'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()
    # Rename 'Value' column based on sensor type
    if sensor_type == 'Weight':
        data.rename(columns={'Value': 'Grip_Strength'}, inplace=True)
        return data[['Time', 'Grip_Strength']]
    elif sensor_type == 'FSR':
        data.rename(columns={'Value': 'Force'}, inplace=True)
        return data[['Time', 'Force']]
    else:
        raise ValueError(f"Unsupported sensor type: {sensor_type}")

def calculate_grip_strength_metrics(data):
    """
    Calculate grip strength metrics: Plateau Coefficient of Variation,
    Peak Grip Strength, and Time to reach specific percentages of max grip strength.
    """
    max_hgs = data['Grip_Strength'].max()
    threshold = 0.9 * max_hgs
    plateau_region = data[data['Grip_Strength'] >= threshold]

    if not plateau_region.empty:
        plateau_mean = plateau_region['Grip_Strength'].mean()
        plateau_std = plateau_region['Grip_Strength'].std()
        plateau_cv = (plateau_std * 100) / plateau_mean
    else:
        plateau_cv = None  # No plateau region found

    peak_time = data.loc[data['Grip_Strength'].idxmax(), 'Time']

    percentages = [25, 50, 75, 80]
    time_for_percentages = {}
    post_peak_data = data[data['Time'] >= peak_time]

    for percentage in percentages:
        target = max_hgs * (percentage / 100)
        subset = post_peak_data[post_peak_data['Grip_Strength'] <= target]

        if not subset.empty:
            time_for_percentages[percentage] = subset.iloc[0]['Time'] - peak_time
        else:
            time_for_percentages[percentage] = None

    return plateau_cv, max_hgs, peak_time, time_for_percentages

def calculate_joint_stiffness_metrics(data):
    """
    Calculate joint stiffness metrics: Force Relaxation Rate,
    Force-Time Integral (Impulse), and Rate of Force Development (RFD).
    """
    peak_idx = data['Force'].idxmax()
    peak_time = data.loc[peak_idx, 'Time']
    post_peak_data = data.loc[peak_idx:]

    dt = np.diff(post_peak_data['Time'])
    dF = np.diff(post_peak_data['Force'])
    slopes = dF / dt
    negative_slopes = slopes[slopes < 0]
    relaxation_rate = np.mean(negative_slopes) if len(negative_slopes) > 0 else None

    impulse = np.trapz(data['Force'], data['Time'])

    window_ms = 100
    window_time = data['Time'].iloc[0] + window_ms / 1000.0
    subset = data[data['Time'] <= window_time]
    if len(subset) >= 2:
        dt = np.diff(subset['Time'])
        dF = np.diff(subset['Force'])
        slopes = dF / dt
        max_rfd = np.max(slopes)
    else:
        max_rfd = None

    return relaxation_rate, impulse, max_rfd

def main():
    if len(sys.argv) != 2:
        print("Usage: python analysis.py <csv_filename>")
        sys.exit(1)

    file_name = sys.argv[1]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, file_name)

    if not os.path.isfile(file_path):
        print(f"Error: The file '{file_name}' does not exist in the directory '{script_dir}'.")
        sys.exit(1)

    # Grip Strength Analysis
    try:
        grip_data = read_data(file_path, 'Weight')
        plateau_cv, peak_strength, peak_time, time_for_percentages = calculate_grip_strength_metrics(grip_data)

        print("\nGrip Strength Analysis:")
        if plateau_cv is not None:
            print(f"Plateau Coefficient of Variation: {plateau_cv:.2f}")
        else:
            print("Plateau Coefficient of Variation: Not calculated (no plateau region found)")
        print(f"Peak Grip Strength: {peak_strength:.2f} kg at {peak_time:.2f} seconds")
        for perc, time in time_for_percentages.items():
            if time is not None:
                print(f"Time to reach {perc}% of max grip strength: {time:.2f} seconds")
            else:
                print(f"{perc}% of max grip strength was not reached during the recording.")
    except ValueError as e:
        print(f"Grip Strength Analysis: {e}")

    # Joint Stiffness Analysis
    try:
        joint_data = read_data(file_path, 'FSR')
        relaxation_rate, impulse, rfd = calculate_joint_stiffness_metrics(joint_data)

        print("\nJoint Stiffness Analysis:")
        if relaxation_rate is not None:
            print(f"Force Relaxation Rate: {relaxation_rate:.2f} N/s")
        else:
            print("Force Relaxation Rate: Not calculated (insufficient descending data)")
        print(f"Force-Time Integral (Impulse): {impulse:.2f} N·s")
        if rfd is not None:
            print(f"Rate of Force Development (RFD, first 100 ms): {rfd:.2f} N/s")
        else:
            print("Rate of Force Development (RFD): Not calculated (insufficient data in initial phase)")
    except ValueError as e:
        print(f"Joint Stiffness Analysis: {e}")

if __name__ == "__main__":
    main()