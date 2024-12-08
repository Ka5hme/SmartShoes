import socket
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from scipy.ndimage import gaussian_filter
import re

# Server configuration
HOST = '0.0.0.0'
PORT = 65432

# Updated foot layout
foot_layout = np.array([
    [0, None, None, None],   # Toes
    [1, 4, 2, None],         # Ball of foot
    [None, 5, 3, None],      # Arch
    [None, 6, 7, None]       # Heel
])

# Define foot outline as a polygon
foot_outline_x = [0.5, 0, 0.875, 0.75, 0.75, 2.25, 2.25, 2.25, 2.375, 2.0, 0.5]
foot_outline_y = [0.375, 1, 2.000, 3.00, 3.00, 3.00, 2.50, 2.00, 1.000, 0.5, 0.375]
foot_polygon = Path(np.column_stack((foot_outline_x, foot_outline_y)))

# Parse incoming data
def parse_data(data_str):
    step_pattern = r"Steps: (\d+),"
    adc_pattern = r"Channel (\d+): (\d+)"

    steps_match = re.search(step_pattern, data_str)
    adc_matches = re.findall(adc_pattern, data_str)

    steps = int(steps_match.group(1)) if steps_match else 0
    channel_values = {int(ch): int(val) for ch, val in adc_matches}

    return steps, channel_values

# Generate heatmap based on the updated foot layout
def generate_foot_heatmap(channel_values, steps):
    # Initialize a grid for the foot layout
    foot_grid = np.full(foot_layout.shape, np.nan)

    # Populate the grid with sensor data
    for channel, value in channel_values.items():
        indices = np.where(foot_layout == channel)
        if indices[0].size > 0 and indices[1].size > 0:
            row, col = indices[0][0], indices[1][0]
            foot_grid[row, col] = value

    # Replace NaNs with zeros for interpolation
    foot_grid = np.nan_to_num(foot_grid, nan=0)

    # Smooth the grid with a Gaussian filter
    interpolated_grid = gaussian_filter(foot_grid, sigma=1.5)

    # Mask unused areas of the foot grid
    mask = np.isnan(np.array(foot_layout, dtype=float))
    masked_grid = np.ma.masked_array(interpolated_grid, mask=mask)

    # Generate X and Y coordinates for the grid
    x = np.linspace(0, foot_grid.shape[1] - 1, foot_grid.shape[1])
    y = np.linspace(0, foot_grid.shape[0] - 1, foot_grid.shape[0])
    X, Y = np.meshgrid(x, y)

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(6, 10))

    # Plot the heatmap
    cp = ax.contourf(X, Y, masked_grid, levels=20, cmap="hot", alpha=0.8)
    plt.colorbar(cp, ax=ax, label="Pressure Intensity")
    ax.contour(X, Y, masked_grid, levels=10, colors="white", linewidths=0.5)
    ax.invert_yaxis()

    # Add black dots at sensor locations
    for row in range(foot_layout.shape[0]):
        for col in range(foot_layout.shape[1]):
            if foot_layout[row, col] is not None:
                ax.plot(col, row, 'ko')  # Black dots

    # Clip the heatmap to the foot polygon
    foot_path = Path(np.column_stack((foot_outline_x, foot_outline_y)))
    patch = PathPatch(foot_path, transform=ax.transData, color='none', alpha=0.8)
    ax.add_patch(patch)

    # Clip the plotted elements to the foot shape
    for artist in ax.collections:
        artist.set_clip_path(patch)

    # Draw the foot outline
    ax.plot(foot_outline_x, foot_outline_y, 'k--', linewidth=1.5, label="Foot Outline")

    # Set title
    ax.set_title(f"Foot Pressure Map - Steps: {steps}")
    plt.legend()
    plt.show()

# Start server to receive data
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")

        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data_str = data.decode('utf-8')
                print(f"Received: {data_str}")

                # Parse and generate the heatmap
                steps, channel_values = parse_data(data_str)
                generate_foot_heatmap(channel_values, steps)

if __name__ == "__main__":
    start_server()
