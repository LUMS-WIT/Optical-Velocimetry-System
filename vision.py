import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, simpledialog

# Global variables
avg_velocities = []
previous_velocities = {}  # Dictionary to store last recorded velocity for each feature
roi_points = []
polygon_drawn = False
displacement_times = {}
initial_positions = {}
state = 'ROI'  # To manage different stages of user input
point_counter = 0  # Counter for distance points
distance_points = []
velocity_ft_per_s_ls = []
distance_in_feet = None
pixel_to_feet_ratio = None
lengths_dict = {}  # To store the length along x and y axis
canal_topwidth_ft = None
axis_for_topwidth = None
canal_width_pixels = None
first_frame = None
length_x = None
length_y = None
CALC_DISCHARGE = False
NUM_SEGMENTS = None
AREAS = None

def click_event(event, x, y, flags, param):
    global roi_points, polygon_drawn, state, point_counter, distance_points, pixel_to_feet_ratio, distance_in_feet, lengths_dict, first_frame, CALC_DISCHARGE, length_x, length_y

    if event == cv2.EVENT_LBUTTONDOWN:
        if state == 'ROI' and len(roi_points) < 4:
            roi_points.append((x, y))
            cv2.circle(first_frame, (x, y), 5, (0, 0, 255), -1)
            cv2.displayOverlay("Tracking Window", "You marked point "+str(len(roi_points)), 2000)     

            if len(roi_points) == 4:
                cv2.polylines(first_frame, [np.array(roi_points)], isClosed=True, color=(0, 255, 0), thickness=2)
                polygon_drawn = True
                state = 'Distance'
                cv2.displayOverlay("Tracking Window",
                                   "Now, please mark two points and input the real distance between them (in feet) for pixel-to-feet conversion.", 
                                   5000)
                
                # Calculate the lengths of the polygon sides along x and y axes
                length_x = abs(roi_points[1][0] - roi_points[0][0])  # Along x-axis
                length_y = abs(roi_points[2][1] - roi_points[1][1])  # Along y-axis
                lengths_dict = {'length_along_X_axis': length_x, 'length_along_Y_axis': length_y}

        elif state == 'Distance' and point_counter < 2:
            distance_points.append((x, y))
            point_counter += 1
            cv2.circle(first_frame, (x, y), 5, (255, 0, 0), -1)
            
            if point_counter == 2:
                # Ask the user for the distance in feet between these two points
                distance_in_feet = simpledialog.askfloat("Real-world unit",
                                                         "Enter the real-world distance between these points (in feet): ")
                pixel_distance = np.sqrt((distance_points[0][0] - distance_points[1][0]) ** 2 + 
                                         (distance_points[0][1] - distance_points[1][1]) ** 2)
                pixel_to_feet_ratio = distance_in_feet / pixel_distance
                cv2.displayOverlay("Tracking Window",
                                   "Distance (ft) = "+str(round(distance_in_feet,3))+\
                                   ", Distance (px) = "+str(round(pixel_distance,3))+ \
                                   "\nPixel-to-feet ratio calculated = "+str(round(pixel_to_feet_ratio,3)), 3000)
                if CALC_DISCHARGE:
                    state = 'Discharge_Calculation'  # Proceed to next stage
                else:
                    state = 'Tracking'
                    cv2.displayOverlay("Tracking Window","Calculating optical flow...",5000)

def get_user_inputs():
    global canal_topwidth_ft, axis_for_topwidth, canal_width_pixels, lengths_dict

    # Ask for the axis corresponding to the canal width
    axis_for_topwidth = simpledialog.askstring("Axis Info", "Which axis (X/Y) corresponds to the canal width in the ROI? ").lower()

    # Convert the canal width to pixels based on the selected axis
    if axis_for_topwidth == 'x':
        canal_width_pixels = lengths_dict['length_along_X_axis']
    elif axis_for_topwidth == 'y':
        canal_width_pixels = lengths_dict['length_along_Y_axis']
    else:
        cv2.displayOverlay("Tracking Window","Invalid axis input. Assuming default X axis.",3000)
        canal_width_pixels = lengths_dict['length_along_X_axis']

    # Calculate pixel-to-physical conversion
    topwidth_pixel_conversion = canal_topwidth_ft / canal_width_pixels

    # Display the calculated pixel width
    cv2.displayOverlay("Tracking Window",f"Canal width in pixels: {canal_width_pixels} pixels", 3000)
    cv2.displayOverlay("Tracking Window",f"Pixel-to-topwidth conversion ratio: {topwidth_pixel_conversion:.4f} feet per pixel", 3000)

def generate_gradient_colors(num_segments):
    center_index = num_segments // 2
    colors = []
    
    for i in range(center_index + 1):
        # Interpolate between Red -> Yellow -> Green
        red = int(255 * (1 - i / center_index))
        green = int(255 * (i / center_index))
        colors.append((0, green, red))
    
    # Mirror the colors for symmetry
    return colors[:-1] + colors[::-1]

def draw_segments(frame):
    global roi_points, NUM_SEGMENTS, axis_for_topwidth, length_x, length_y

    colors = generate_gradient_colors(NUM_SEGMENTS)
    if axis_for_topwidth == 'x':    
        segment_width = length_x // NUM_SEGMENTS
    elif axis_for_topwidth == 'y':
        segment_width = length_y // NUM_SEGMENTS
 
    end_point = roi_points[0]
    segments = {}  # Dictionary to store segment coordinates
    
    for i in range(NUM_SEGMENTS):
        color = colors[i]  # Select color based on position
        if axis_for_topwidth == 'x':
            start_point = (end_point[0], roi_points[0][1])
            end_point = (start_point[0] + segment_width, roi_points[3][1])

        # elif axis_for_topwidth == 'y':
            #start_point = (end_point[0], roi_points[0][1])
            #end_point = (start_point[0] + segment_width, roi_points[3][1])

        frame = cv2.rectangle(frame, start_point, end_point, color, 3)
        
        # Store segment info
        segments[i+1] = {'start': start_point, 'end': end_point, 'color': color}

    return frame, segments

# Load video 
def calculate_optical_flow(video_path, discharge, width, num_segments, areas):

    global first_frame, state, CALC_DISCHARGE, canal_topwidth_ft, NUM_SEGMENTS, AREAS, roi_points, velocity_ft_per_s_ls
    CALC_DISCHARGE = discharge
    canal_topwidth_ft = width
    NUM_SEGMENTS = num_segments
    AREAS = areas

    result_dict = {}

    cap = cv2.VideoCapture(video_path)

    # Get frames per second (fps) of the video
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Parameters for ShiTomasi corner detection
    feature_params = dict(maxCorners=50, qualityLevel=0.01, minDistance=7, blockSize=5)

    # Parameters for Lucas-Kanade optical flow
    lk_params = dict(winSize=(15, 15), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

    # Take first frame and display it to get user input
    ret, first_frame = cap.read()
    if not ret:
        print("Error reading the video")
        cap.release()
        exit()

    first_frame = cv2.resize(first_frame, (640,480))
    cv2.imshow('Tracking Window', first_frame)
    cv2.displayOverlay("Tracking Window","Please mark four points as your ROI", 2000)

    # Set the mouse callback function to capture the clicks
    cv2.setMouseCallback('Tracking Window',  click_event)


    # Wait until the user selects the ROI and marks the distance points
    while True:
        cv2.imshow('Tracking Window', first_frame)

        if state == 'Discharge_Calculation':
            get_user_inputs()
            state = 'Tracking'
        
        if state == 'Tracking':
            break
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    # Convert the first frame to grayscale
    old_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)

    # Create a mask to define the region of interest based on the polygon
    roi_mask = np.zeros_like(old_gray)
    cv2.fillPoly(roi_mask, [np.array(roi_points)], 255)

    # Detect good features to track within the region of interest (ROI)
    p0 = cv2.goodFeaturesToTrack(old_gray, mask=roi_mask, **feature_params)

    # Create a mask image for drawing purposes
    mask = np.zeros_like(first_frame)

    # Initialize IDs for each detected feature
    ids = np.arange(len(p0)).reshape(-1, 1)  # Reshape to match p0's shape

    # Store the initial positions to calculate displacement
    initial_positions = np.copy(p0)

    # Initialize a dictionary to track how many frames each feature was tracked
    frame_counts = {int(id_num): 0 for id_num in ids.ravel()}

    # Define the codec and create VideoWriter object
    # fourcc = cv2.VideoWriter_fourcc(*'MP4V')  # You can change the codec (e.g., 'MJPG', 'MP4V', etc.)
    # out = cv2.VideoWriter('output_video_namal.mp4', fourcc, 30.0, (640, 480))


    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (640,480))
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if CALC_DISCHARGE:
            frame, segments = draw_segments(frame)

        # Calculate Optical Flow using Lucas-Kanade method
        p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)

        # Select good points
        good_new = p1[st == 1]
        good_old = p0[st == 1]
        good_ids = ids[st == 1].ravel()  # Keep track of the IDs for the good points
        good_initial = initial_positions[st == 1]  # Ensure valid points are taken from initial_positions

        # Update the frame count for each tracked feature
        for id_num in good_ids:
            frame_counts[int(id_num)] += 1

        # Draw the tracks within the polygon, display ID numbers, and calculate displacement
        for i, (new, old, id_num, initial) in enumerate(zip(good_new, good_old, good_ids, good_initial)):
            a, b = new.ravel()
            c, d = old.ravel()
            x_init, y_init = initial.ravel()
            
            if cv2.pointPolygonTest(np.array(roi_points), (a, b), False) >= 0:
                mask = cv2.line(mask, (int(a), int(b)), (int(c), int(d)), (0, 255, 0), 2)
                frame = cv2.circle(frame, (int(a), int(b)), 5, (0, 0, 255), -1)

                # Calculate displacement (current position - initial position)
                displacement_px = np.sqrt((a - x_init) ** 2 + (b - y_init) ** 2)
                displacement_ft = displacement_px * pixel_to_feet_ratio

                # Calculate the total time for which this feature has been tracked
                total_time = frame_counts[int(id_num)] / fps  # Time in seconds
                #print ("id_num ", id_num, " frame_counts ", frame_counts, " fps ", fps, " total_time ", total_time)


                # Calculate the velocity for each feature
                velocity_ft_per_s = displacement_ft / total_time
                

                # Check if velocity is decreasing; if so, stop tracking this feature
                if id_num in previous_velocities and velocity_ft_per_s < previous_velocities[id_num]:
                    #print(f'Stopping tracking for feature ID {id_num} as velocity is decreasing.')
                    continue  # Skip this feature in further calculations
            
                # Store the current velocity as the last known velocity for this feature
                previous_velocities[id_num] = velocity_ft_per_s

                if CALC_DISCHARGE:
                    for i, segment in segments.items():
                        start_x, start_y = segment['start']
                        end_x, end_y = segment['end']

                        # Check if the tracked feature (a, b) is inside the segment
                        if start_x <= a <= end_x and start_y <= b <= end_y:
                            segment_key = f"segment_{i}_vels"  # Generate dynamic variable name
                            if segment_key not in globals():
                                globals()[segment_key] = []  # Initialize list if not exists
                            globals()[segment_key].append(velocity_ft_per_s)


                # Display the feature ID, displacement (in feet), and time next to the tracked point
                text_position = (int(a), int(b))
                #displacement_position = (int(a), int(b) + 15)
                #time_position = (int(a), int(b) + 30)
                velocity_position = (int(a), int(b) + 15)


                if velocity_ft_per_s >= 0.15:
                    cv2.putText(frame, f'{id_num}', text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    #cv2.putText(frame, f'{displacement_ft:.2f}ft', displacement_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    #cv2.putText(frame, f'{total_time:.2f}s', time_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                
                    cv2.putText(frame, f'{velocity_ft_per_s:.2f}ft/s', velocity_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    avg_velocities.append(velocity_ft_per_s)

                # Print the ID, displacement, and total time in the console
                #print(f'Feature ID: {id_num}, Displacement: {displacement_ft:.2f}ft, Time: {total_time:.2f}s, Velocity: {velocity_ft_per_s:.2f}ft/s')
            

        img = cv2.add(frame, mask)

        # Show the result
        cv2.imshow('Tracking Window', img)

        # Update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)
        ids = good_ids.reshape(-1, 1)  # Update IDs to track the correct points
        initial_positions = good_initial.reshape(-1, 1, 2)  # Update initial positions for valid points

        if cv2.waitKey(500) & 0xFF == ord('q'):
            break

        # Inside your loop to process frames, write each frame to the video
        # out.write(frame)

    if CALC_DISCHARGE:
        for i in range(NUM_SEGMENTS):
            segment_key = f"segment_{i+1}_vels"  # Dynamically generate segment variable name
            area = AREAS[f"area{i+1}"]  # Assuming area variables are named area1, area2, etc.
            # Ensure the velocity list exists
            if segment_key in globals() and len(globals()[segment_key]) > 0:
                avg_velocity = sum(globals()[segment_key]) / len(globals()[segment_key])
                discharge = avg_velocity * area
                result_dict[f"Seg_{i+1}"] = [avg_velocity, discharge]
            else:
                result_dict[f"Seg_{i+1}"] = []
    else:
        avg_V = sum(avg_velocities) / len(avg_velocities)
        result_dict['avg_vel'] = avg_V    

    cap.release()
    # out.release()
    cv2.destroyAllWindows()

    return result_dict