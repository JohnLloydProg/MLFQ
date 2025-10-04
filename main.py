import tkinter as tk
from tkinter import ttk, messagebox
from objects import ProcessCard, Process, ModifyWindow, GanttCard
import logging
import random
import sys


# Global Variables
processes:list[Process] = [
    Process("P1", 1, 20, 3), 
    Process("P2", 3, 10, 2), 
    Process("P3", 5, 2, 1),
    Process("P4", 8, 7, 2),
    Process("P5", 11, 15, 3), 
    Process("P6", 15, 8, 2), 
    Process("P7", 20, 4, 1)
]
mlfq:dict[int, dict[str, list[Process]|int]] = {
    1:{"queue":[], "quantum_time":3}, 
    2:{"queue":[], "quantum_time":3}, 
    3:{"queue":[], "quantum_time":3},
    4:{"queue":[], "quantum_time":3}
}
settings:dict[str, int] = {"aging_time": 5, "lower_priority_time": 6}
current_card:GanttCard = None
current_process:Process = None
start_processing = None
sim_time = 0
sim_running = False


# Randomizer
def randomize_processes(n=10):
    global processes
    processes = []
    for i in range(1, n+1):
        processes.append(Process(f'P{str(i)}', random.randint(0, 10), random.randint(1, 10), random.randint(1, 4)))
    update_process_table()


# Update Process Table
def update_process_table():
    for row in process_table.get_children():
        process_table.delete(row)
    for p in processes:
        process_table.insert("", "end", values=(p.name, p.arrival_time, p.original_burst_time, p.priority))


def update_queue_display():
    global queue_frames
    for i in range(4):
        for widget in queue_frames[i].winfo_children():
            process_card:ProcessCard = widget
            if process_card.process not in mlfq[i+1]["queue"]:
                process_card.destroy()
            else:
                process_card.update_values()
    for i in range(1, 5):
        for process in mlfq[i]["queue"]:
            if process not in map(lambda process_card: process_card.process, queue_frames[i-1].winfo_children()):
                ProcessCard(queue_frames[i-1], process)


def select_from_queues(queue:dict[int, dict[str, list[Process]|int]]) -> Process:
    global current_card
    for priority in range(1, 5):
        if (queue[priority]["queue"]):
            current_process = queue[priority]["queue"].pop(0)
            current_card = GanttCard(gantt_inner, current_process)
            current_process.sub_wait_time = 0
            return current_process
    return None


def step():
    global sim_time, sim_running, current_process, start_processing
    if not sim_running:
        return

    #Waiting process and aging
    for priority in range(1, 5):
        for process in mlfq[priority]["queue"]:
            process.wait()
            if (process.sub_wait_time >= settings.get("aging_time") and process.priority > 1):
                process.increase_priority()
                mlfq[priority]["queue"].remove(process)
                mlfq[process.priority]["queue"].append(process)

    # Checking arrival time to add to queue
    for process in processes:
        if process.arrival_time == sim_time:
            mlfq[process.priority]["queue"].append(process)
        
    
    #Processing the current process
    if (current_process):
        current_process.process()
        if (current_card):
            current_card.update_values()
        if (sim_time - start_processing >= mlfq[current_process.priority]["quantum_time"] or current_process.is_completed()):
            if (current_process.burst_time > 0):
                if (current_process.processed_time >= settings.get("lower_priority_time") and current_process.priority < 4):
                    current_process.decrease_priority()
                mlfq[current_process.priority]["queue"].append(current_process)
            else:
                current_process.complete(sim_time)
            current_process = select_from_queues(mlfq)
            if (current_process):
                start_processing = sim_time
                if (not current_process.first_response):
                    current_process.first_response = sim_time
            else:
                start_processing = None

    else:
        current_process = select_from_queues(mlfq)
        if (current_process):
            start_processing = sim_time
            if (not current_process.first_response):
                current_process.first_response = sim_time
    
    update_queue_display()
    time_var.set(f"Time: {sim_time}")
    
    if (all(process.is_completed() for process in processes)):
        sim_running = False
        toggle.configure(state="normal")
        run_button.configure(text="Run MLFQ")
        update_stats()
        time_var.set(f"Simulation finished at Time: {sim_time}")
    else:
        if (sim_automatic.get()):
            root.after(750, step)

    sim_time += 1


# Simulation (Round Robin with animated cards & time counter)
def simulate_mlfq_step():
    global sim_time, sim_running, current_process, current_card
    if sim_running:
        sim_running = False
        toggle.configure(state="normal")
        run_button.configure(text="Run MLFQ")
    else:
        sim_running = True
        toggle.configure(state="disabled")
        run_button.configure(text="Stop MLFQ")

    current_card = None
    current_process = None

    # Reset queues, Gantt, and time
    for queue in mlfq.values():
        queue.get("queue", []).clear()
    
    sim_time = 0
    for p in processes:
        p.processed_time = 0
        p.sub_wait_time = 0
        p.burst_time = p.original_burst_time
        p.priority = p.original_priority

    # Clear previous Gantt
    for widget in gantt_inner.winfo_children():
        widget.destroy()
    time_var.set("Time: 0")

    # Sort processes by arrival then PID
    processes.sort(key=lambda x: (x.arrival_time, int(x.name[1:])))

    update_queue_display()
    step()


# Stats
def update_stats():
    total_wait = 0
    total_turnaround = 0
    total_response = 0
    for p in processes:
        total_wait += p.turnaround_time - p.original_burst_time
        total_turnaround += p.turnaround_time
        total_response += p.first_response - p.arrival_time
    n = len(processes)
    avg_wait = total_wait / n if n else 0
    avg_turnaround = total_turnaround / n if n else 0
    avg_response = total_response / n if n else 0
    stats_var.set(f"Avg Waiting Time: {avg_wait:.2f} | Avg Turnaround Time: {avg_turnaround:.2f} | Avg Response Time: {avg_response:.2f}")


def toggle_action():
    if sim_automatic.get():
        toggle.configure(text="Automatic", relief=tk.SUNKEN)
        step_button.configure(state="disabled")
    else:
        toggle.configure(text="Step-By-Step", relief=tk.RAISED)
        step_button.configure(state="normal")


# GUI
root = tk.Tk()
root.title("MLFQ Round Robin Scheduler")
root.geometry("1080x720")
root.wm_resizable(False, False)

sim_automatic = tk.BooleanVar(value=True)

top_frame = tk.Frame(root)
top_frame.pack(side=tk.TOP, fill=tk.X)
tk.Button(top_frame, text="Modify", command=lambda: ModifyWindow(processes, mlfq, settings, process_table)).pack(side=tk.LEFT, padx=5, pady=5)
tk.Button(top_frame, text="Randomize (10)", command=lambda: randomize_processes(10)).pack(side=tk.LEFT, padx=5, pady=5)

process_frame = tk.Frame(root)
process_frame.pack(side=tk.TOP, fill=tk.BOTH)
columns = ("PID", "Arrival", "Burst", "Priority")
process_table = ttk.Treeview(process_frame, columns=columns, show="headings", height=6)
for col in columns:
    process_table.heading(col, text=col)
    process_table.column(col, width=10)
scrollbar = ttk.Scrollbar(process_frame, orient="vertical", command=process_table.yview)
process_table.configure(yscroll=scrollbar.set)
process_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

main_frame = tk.Frame(root)
main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Queue
queue_frame = tk.Frame(main_frame, width=500)
queue_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
queue_frame.pack_propagate(False)
tk.Label(queue_frame, text="Queue 1 (High)").pack()
queue0_frame = tk.Frame(queue_frame)
queue0_frame.pack(pady=5, fill=tk.X)
tk.Label(queue_frame, text="Queue 2 (Medium)").pack()
queue1_frame = tk.Frame(queue_frame)
queue1_frame.pack(pady=5, fill=tk.X)
tk.Label(queue_frame, text="Queue 3 (Low)").pack()
queue2_frame = tk.Frame(queue_frame)
queue2_frame.pack(pady=5, fill=tk.X)
tk.Label(queue_frame, text="Queue 4 (Very Low)").pack()
queue3_frame = tk.Frame(queue_frame)
queue3_frame.pack(pady=5, fill=tk.X)
queue_frames = [queue0_frame, queue1_frame, queue2_frame, queue3_frame]

# Time counter above Gantt chart
gantt_frame = tk.Frame(main_frame)
gantt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
time_var = tk.StringVar(value="Time:")
gantt_top_frame = tk.Frame(gantt_frame)
gantt_top_frame.pack(anchor='w', fill=tk.X)
run_button = tk.Button(gantt_top_frame, text="Run MLFQ", command=simulate_mlfq_step)
run_button.pack(side=tk.LEFT, padx=5, pady=5)
toggle = tk.Checkbutton(gantt_top_frame, text="Automatic", variable=sim_automatic, command=toggle_action, indicatoron=0, relief=tk.SUNKEN, width=10)
toggle.pack(side=tk.LEFT, padx=5, pady=5)
step_button = tk.Button(gantt_top_frame, text="Step", command=step, state="disabled")
step_button.pack(side=tk.LEFT, padx=5, pady=5)
tk.Label(gantt_top_frame, textvariable=time_var, font=("Arial", 12)).pack(side=tk.LEFT)

# Gantt chart scrollable
gantt_canvas = tk.Canvas(gantt_frame, bg="white", height=100)
h_scroll = tk.Scrollbar(gantt_frame, orient=tk.HORIZONTAL, command=gantt_canvas.xview)
gantt_canvas.configure(xscrollcommand=h_scroll.set)
gantt_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
h_scroll.pack(side=tk.TOP, fill=tk.X)
gantt_inner = tk.Frame(gantt_canvas, bg="white")
gantt_canvas.create_window((0, 0), window=gantt_inner, anchor="nw")
gantt_inner.bind("<Configure>", lambda event: gantt_canvas.configure(scrollregion=gantt_canvas.bbox("all")))

# Stats
stats_var = tk.StringVar()
tk.Label(root, textvariable=stats_var, font=("Arial", 12)).pack(pady=10, side=tk.BOTTOM)

update_process_table()
root.mainloop()
