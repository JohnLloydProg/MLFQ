import tkinter as tk
from tkinter import ttk, messagebox
from objects import ProcessCard, Process, ModifyWindow, GanttCard
import logging
import random
import sys

logging.basicConfig(handlers=[logging.FileHandler("output.log", 'w'), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    3:{"queue":[], "quantum_time":3}
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
        processes.append(Process(f'P{str(i)}', random.randint(0, 10), random.randint(1, 10), random.randint(1, 3)))
    update_process_table()


# Update Process Table
def update_process_table():
    for row in process_table.get_children():
        process_table.delete(row)
    for p in processes:
        process_table.insert("", "end", values=(p.name, p.arrival_time, p.original_burst_time, p.priority))


def update_queue_display():
    global queue_frames
    for i in range(3):
        for widget in queue_frames[i].winfo_children():
            process_card:ProcessCard = widget
            if process_card.process not in mlfq[i+1]["queue"]:
                process_card.destroy()
            else:
                process_card.update_values()
    for i in range(1, 4):
        for process in mlfq[i]["queue"]:
            if process not in map(lambda process_card: process_card.process, queue_frames[i-1].winfo_children()):
                ProcessCard(queue_frames[i-1], process)


def select_from_queues(queue:dict[int, dict[str, list[Process]|int]]) -> Process:
    global current_card
    for priority in range(1, 4):
        if (queue[priority]["queue"]):
            current_process = queue[priority]["queue"].pop(0)
            logger.info(f"Process {current_process.name} from Queue {priority} is selected to run")
            current_card = GanttCard(gantt_inner, current_process)
            current_process.sub_wait_time = 0
            return current_process
    return None


def step():
    global sim_time, sim_running, current_process, start_processing, sim_paused

    #Waiting process and aging
    for priority in range(1, 4):
        for process in mlfq[priority]["queue"]:
            process.wait()
            if (process.sub_wait_time >= settings.get("aging_time") and process.priority > 1):
                process.increase_priority()
                mlfq[priority]["queue"].remove(process)
                mlfq[process.priority]["queue"].append(process)
                logger.info(f"Process {process.name} has been promoted to Queue {process.priority} due to aging")

    # Checking arrival time to add to queue
    for process in processes:
        if process.arrival_time == sim_time:
            mlfq[process.priority]["queue"].append(process)
            logger.info(f"Process {process.name} has arrived and added to Queue {process.priority}")
        
    
    #Processing the current process
    if (current_process):
        current_process.process()
        logger.info(f"Processing {current_process.name}, remaining burst time: {current_process.burst_time}")
        if (current_card):
            current_card.update_values()
        if (sim_time - start_processing >= mlfq[current_process.priority]["quantum_time"] or current_process.is_completed()):
            if (current_process.burst_time > 0):
                if (current_process.processed_time >= settings.get("lower_priority_time") and current_process.priority < 3):
                    current_process.decrease_priority()
                    logger.info(f"Process {current_process.name} has been demoted to Queue {current_process.priority} due to exceeding lower priority time")
                mlfq[current_process.priority]["queue"].append(current_process)
            else:
                current_process.complete(sim_time)
                logger.info(f"Process {current_process.name} has completed execution")
            logger.info(f"Quantum time finished for process {current_process.name}")
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

    logger.info("=========================================================")
    logger.info(f"Time: {str(sim_time)}")
    logger.info(f"Current Process: {str(current_process)}")
    for priority in range(1, 4):
        out = f"Queue {str(priority)}: ["
        for proceses in mlfq[priority]["queue"]:
            out += f"{proceses}, "
        out +="]"
        logger.info(out)
    logger.info("=========================================================")
    
    if (all(process.is_completed() for process in processes)):
        logger.info("All processes have completed execution.")
        sim_running = False
        update_stats()
        time_var.set(f"Simulation finished at Time: {sim_time}")
    else:
        if (sim_automatic.get()):
            root.after(750, step)

    sim_time += 1


# Simulation (Round Robin with animated cards & time counter)
def simulate_mlfq_step():
    global sim_time, sim_running, current_process, current_card
    current_card = None
    current_process = None
    sim_running = True

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
    else:
        toggle.configure(text="Step-By-Step", relief=tk.RAISED)


# GUI
root = tk.Tk()
root.title("MLFQ Round Robin Scheduler")
root.geometry("1200x800")

sim_automatic = tk.BooleanVar(value=True)

top_frame = tk.Frame(root)
top_frame.pack(side=tk.TOP, fill=tk.X)
tk.Button(top_frame, text="Modify", command=lambda: ModifyWindow(processes, mlfq, settings, process_table)).pack(side=tk.LEFT, padx=5)
tk.Button(top_frame, text="Randomize (10)", command=lambda: randomize_processes(10)).pack(side=tk.LEFT, padx=5)
tk.Button(top_frame, text="Run MLFQ", command=simulate_mlfq_step).pack(side=tk.LEFT, padx=5)
toggle = tk.Checkbutton(top_frame, text="Automatic", variable=sim_automatic, command=toggle_action, indicatoron=0, relief=tk.SUNKEN, width=10)
toggle.pack(side=tk.LEFT, padx=5)

process_frame = tk.Frame(root)
process_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
columns = ("PID", "Arrival", "Burst", "Priority")
process_table = ttk.Treeview(process_frame, columns=columns, show="headings", height=8)
for col in columns:
    process_table.heading(col, text=col)
    process_table.column(col, width=100)
scrollbar = ttk.Scrollbar(process_frame, orient="vertical", command=process_table.yview)
process_table.configure(yscroll=scrollbar.set)
process_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

main_frame = tk.Frame(root)
main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Queue
queue_frame = tk.Frame(main_frame)
queue_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10, expand=True)
queue_frame.pack_propagate(False)
tk.Label(queue_frame, text="Queue 1 (High)").pack()
queue0_frame = tk.Frame(queue_frame)
queue0_frame.pack(pady=5)
tk.Label(queue_frame, text="Queue 2 (Medium)").pack()
queue1_frame = tk.Frame(queue_frame)
queue1_frame.pack(pady=5)
tk.Label(queue_frame, text="Queue 3 (Low)").pack()
queue2_frame = tk.Frame(queue_frame)
queue2_frame.pack(pady=5)
queue_frames = [queue0_frame, queue1_frame, queue2_frame]

# Time counter above Gantt chart
gantt_frame = tk.Frame(main_frame)
gantt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
time_var = tk.StringVar()
gantt_top_frame = tk.Frame(gantt_frame)
gantt_top_frame.pack(anchor='w', fill=tk.X)
tk.Button(gantt_top_frame, text="Step", command=step).pack(side=tk.LEFT, padx=5)
tk.Label(gantt_top_frame, textvariable=time_var, font=("Arial", 12)).pack(side=tk.LEFT)

# Gantt chart scrollable
gantt_canvas = tk.Canvas(gantt_frame, bg="white", height=200)
h_scroll = tk.Scrollbar(gantt_frame, orient=tk.HORIZONTAL, command=gantt_canvas.xview)
gantt_canvas.configure(xscrollcommand=h_scroll.set)
h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
gantt_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
gantt_inner = tk.Frame(gantt_canvas, bg="white")
gantt_canvas.create_window((0, 0), window=gantt_inner, anchor="nw")

def update_canvas_scroll(event):
    gantt_canvas.configure(scrollregion=gantt_canvas.bbox("all"))
gantt_inner.bind("<Configure>", update_canvas_scroll)

# Stats
stats_frame = tk.Frame(root)
stats_frame.pack(side=tk.BOTTOM, fill=tk.X)
stats_var = tk.StringVar()
tk.Label(stats_frame, textvariable=stats_var, font=("Arial", 12)).pack(pady=10)

update_process_table()
root.mainloop()
