# main.py (Updated to call vision.py)



import os
import cv2
import time
import pandas as pd
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from picamera2 import Picamera2
import threading
from vision import calculate_optical_flow


# Ensure the directory for storing videos exists
SAVE_DIR = os.path.expanduser("~/optical_velocimetry/videos")
RESULT_DIR = os.path.expanduser("~/optical_velocimetry/results")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Global variables
MAX_VIDEOS = 10
picam2 = None  # Camera object
CURR_FILE = None
DISCHARGE = False
WIDTH = None
NUM_SEGMENTS = None
AREAS = None

def exit_program():
    exit()

def get_next_filename():
    """Find the next available filename in a cyclic manner from test_1 to test_10."""
    files = os.listdir(SAVE_DIR)
    total_files = len(files)

    if total_files > 0:
        file_nums = [int(fl.split("test_")[1].split(".")[0]) for fl in files]
        filename = os.path.join(SAVE_DIR, f"test_"+str(max(file_nums)+1)+".mp4")
        if total_files==MAX_VIDEOS:
            file_to_remove = os.path.join(SAVE_DIR, f"test_"+str(min(file_nums))+".mp4")
            os.remove(file_to_remove)
    else:
        filename = os.path.join(SAVE_DIR, "test_1.mp4")
    return filename


# Initialize Tkinter window
root = tk.Tk()
root.title("Optical Velocimetry")
root.geometry("400x300")
root.configure(bg="#f0f0f0")


def show_main_menu():
    for widget in root.winfo_children():
        widget.destroy()

    tk.Label(root, text="Optical Velocimetry", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=20)
    tk.Button(root, text="Velocity Calculation", font=("Arial", 12), command=velocity_info, width=25).pack(pady=10)
    tk.Button(root, text="Discharge Calculation", font=("Arial", 12), command=discharge_info, width=25).pack(pady=10)
    tk.Button(root, text="Exit", font=("Arial", 12), command=exit_program, width=10).pack(pady=40)


def velocity_info():
    global DISCHARGE
    DISCHARGE = False

    for widget in root.winfo_children():
        widget.destroy()
    
    tk.Label(root, text="Ensure stable camera position for velocity calculation.", font=("Arial", 12), wraplength=350, bg="#f0f0f0").pack(pady=20)
    tk.Button(root, text="OK", font=("Arial", 12), command=start_camera, width=15).pack(pady=5)
    tk.Button(root, text="Back", font=("Arial", 12), command=show_main_menu, width=15).pack(pady=5)


def discharge_info():  
    global DISCHARGE
    DISCHARGE = True

    for widget in root.winfo_children():
        widget.destroy()
    
    tk.Label(root, text="If catchment geometry is known, proceed.", font=("Arial", 12), wraplength=350, bg="#f0f0f0").pack(pady=20)
    tk.Button(root, text="Proceed", font=("Arial", 12), command=catchment_geometry, width=15).pack(pady=5)
    tk.Button(root, text="Back", font=("Arial", 12), command=show_main_menu, width=15).pack(pady=5)


def catchment_geometry():
    global WIDTH, NUM_SEGMENTS, AREAS
    
    WIDTH = simpledialog.askfloat("Catchment Width", "Enter catchment width (feet):")
    NUM_SEGMENTS = simpledialog.askinteger("Segments", "Enter an odd number of segments :")
    while NUM_SEGMENTS % 2 == 0:
        NUM_SEGMENTS = simpledialog.askinteger("Segments", "Please enter an odd number of segments :")
    
    if WIDTH and NUM_SEGMENTS and NUM_SEGMENTS > 0:
        segment_width = WIDTH / NUM_SEGMENTS
        depths = []
        AREAS = {}
        
        for i in range(NUM_SEGMENTS):
            depth = simpledialog.askfloat(f"Segment {i+1}", f"Enter depth for segment {i+1} (feet):")
            depths.append(depth)
            AREAS[f"area{i+1}"] = depth * segment_width
        
        area_text = "\n".join([f"A{i+1} = {AREAS[f'area{i+1}']:.2f} ft²" for i in range(NUM_SEGMENTS)])
        messagebox.showinfo("Segment Areas", f"Calculated Areas:\n{area_text}")
        start_camera()
    else:
        messagebox.showwarning("Invalid Input", "Please enter valid values.")


def start_camera():
    global picam2
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    
    camera_window = tk.Toplevel(root)
    camera_window.title("Live Camera Feed")
    camera_window.geometry("700x550")
    
    tk.Label(camera_window, text="Adjust angle and focus.", font=("Arial", 12)).pack(pady=10)
    
    timer_label = tk.Label(camera_window, text="", font=("Arial", 12), fg="red")
    timer_label.pack()
    
    rec_label = tk.Label(camera_window, text="", font=("Arial", 14, "bold"), fg="red")
    rec_label.pack()
    
    record_button = tk.Button(camera_window, text="Record Video", font=("Arial", 12), command=lambda: record_video(timer_label, rec_label), width=15)
    record_button.pack(pady=10)


def record_video(timer_label, rec_label):
    global CURR_FILE
    filename = get_next_filename()
    
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
    
    start_time = time.time()
    duration = 20  # Recording duration in seconds
    
    def update_timer():
        elapsed = int(time.time() - start_time)
        remaining = duration - elapsed
        if remaining > 0:
            timer_label.config(text=f"Recording... {remaining}s", fg="red")
            rec_label.config(text="REC" if elapsed % 2 == 0 else "", fg="red")
            timer_label.after(1000, update_timer)
        else:
            timer_label.config(text="Recording complete.", fg="green")
            rec_label.config(text="")
    
    update_timer()
    
    while time.time() - start_time < duration:
        frame = picam2.capture_array()
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        frame = cv2.putText(frame, "REC", (580, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("Recording", frame)
        cv2.waitKey(1)


    CURR_FILE = filename
    out.release()
    cv2.destroyAllWindows()
    messagebox.showinfo("Video Saved", f"Video saved as {filename}")

    btn_process = tk.Button(root, text="Process Video", command=process_video)
    btn_process.pack(pady=20)


def process_video():
    global CURR_FILE, DISCHARGE, WIDTH, NUM_SEGMENTS, AREAS, RESULT_DIR
    if CURR_FILE is None:
        messagebox.showerror("Error", "No recorded video found. Please record a video first.")
        return
    video_path = CURR_FILE  # Example file, replace with dynamic selection

    result_dict = calculate_optical_flow(video_path, DISCHARGE, WIDTH, NUM_SEGMENTS, AREAS)
    
    if DISCHARGE:
        total_discharge = 0
        total_velocity = 0
        df_results = []

        tree_window = tk.Toplevel()
        tree_window.title("Result")
        tree = ttk.Treeview(tree_window, columns=("Segment ID", "Average Velocity (ft/s)", "Discharge (cusec)"), show="headings", height=6)
        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=250)
        for seg_id, seg_data in result_dict.items():
            if len(seg_data)>0:
                df_results.append({"Segment ID":seg_id, "Average Velocity (ft/s)":round(seg_data[0],2),
                                   "Discharge (cusec)":round(seg_data[1],2)})
                tree.insert("", "end", values=(seg_id, str(round(seg_data[0],2)), str(round(seg_data[1],2))))
                total_velocity += seg_data[0]
                total_discharge += seg_data[1]
            else:
                df_results.append({"Segment ID":seg_id, "Average Velocity (ft/s)":"No features were detected",
                                   "Discharge (cusec)":""})                
                tree.insert("", "end", values=(seg_id, "No features were detected", ""))
        df_results.append({"Segment ID":"", "Average Velocity (ft/s)":"", "Discharge (cusec)":""})
        df_results.append({"Segment ID":f"Canal velocity is {round(total_velocity/NUM_SEGMENTS,2)} ft/s",
                           "Average Velocity (ft/s)":"", "Discharge (cusec)":""})
        df_results.append({"Segment ID":f"Canal discharge is {round(total_discharge,2)} cusec",
                           "Average Velocity (ft/s)":"", "Discharge (cusec)":""})
        df_results = pd.DataFrame(df_results)
                
        tree.insert("", "end", values=("", "", ""))
        tree.insert("", "end", values=(f"    Canal velocity is {round(total_velocity/NUM_SEGMENTS,2)} ft/s", "", ""))
        tree.insert("", "end", values=(f"    Canal discharge is {round(total_discharge,2)} cusec", "", ""))
        tree.pack(padx=10, pady=10)
        tree_window.wait_window()

        # save results to file
        fname = "Result_discharge_"+os.path.basename(video_path).split(".")[0]+".csv"
        df_results.to_csv(os.path.join(RESULT_DIR, fname), index=False)
        messagebox.showinfo("Result","Results saved to "+os.path.join(RESULT_DIR, fname))
    else:
        fname = "Result_velocity_"+os.path.basename(video_path).split(".")[0]+".csv"
        df_results = pd.DataFrame([{"Average Velocity (ft/s)":round(result_dict['avg_vel'],3)}])
        df_results.to_csv(os.path.join(RESULT_DIR, fname), index=False)
        messagebox.showinfo("Result","Average velocity = "+str(round(result_dict['avg_vel'],3))+" ft/s\nResults saved to "+os.path.join(RESULT_DIR, fname))
    show_main_menu()

show_main_menu()
root.mainloop()
