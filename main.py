import pandas as pd
from objects import Process
import logging
from time import sleep
import sys


logging.basicConfig(handlers=[logging.FileHandler("output.log", 'w'), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

processes:list[Process] = [
    Process("P1", 1, 20, 3), 
    Process("P2", 3, 10, 2), 
    Process("P3", 5, 2, 1),
    Process("P4", 8, 7, 2),
    Process("P5", 11, 15, 3), 
    Process("P6", 15, 8, 2), 
    Process("P7", 20, 4, 1),
]
queues:dict[int, dict[str, list[Process]|int]] = {
    1:{"queue":[], "quantum_time":3}, 
    2:{"queue":[], "quantum_time":3}, 
    3:{"queue":[], "quantum_time":3}
}
aging_time = 5
lower_priority_time = 6
current_process:Process = None
start_processing = None
finished_jobs:list[tuple[int, int]] = []
time = 0

def select_from_queues(queue:dict[int, dict[str, list[Process]|int]]) -> Process:
    for priority in range(1, 4):
        if (queue[priority]["queue"]):
            current_process = queue[priority]["queue"].pop(0)
            logger.info(f"Process {current_process.name} from Queue {priority} is selected to run")
            current_process.sub_wait_time = 0
            return current_process
    return None

logger.info("started")
while True:
    #Waiting process and aging
    for priority in range(1, 4):
        for process in queues[priority]["queue"]:
            process.wait()
            if (process.sub_wait_time >= aging_time and process.priority > 1):
                process.increase_priority()
                queues[priority]["queue"].remove(process)
                queues[process.priority]["queue"].append(process)
                logger.info(f"Process {process.name} has been promoted to Queue {process.priority} due to aging")

    # Checking arrival time to add to queue
    for process in processes:
        if process.arrival_time == time:
            queues[process.priority]["queue"].append(process)
            logger.info(f"Process {process.name} has arrived and added to Queue {process.priority}")
        
    
    #Processing the current process
    if (current_process):
        current_process.process()
        logger.info(f"Processing {current_process.name}, remaining burst time: {current_process.burst_time}")
        if (time - start_processing >= queues[current_process.priority]["quantum_time"] or current_process.is_completed()):
            if (current_process.burst_time > 0):
                if (current_process.processed_time >= lower_priority_time):
                    current_process.decrease_priority()
                    logger.info(f"Process {current_process.name} has been demoted to Queue {current_process.priority} due to exceeding lower priority time")
                queues[current_process.priority]["queue"].append(current_process)
            else:
                current_process.complete(time)
                logger.info(f"Process {current_process.name} has completed execution")
            finished_jobs.append((current_process.name, start_processing, time))
            logger.info(f"Quantum time finished for process {current_process.name}")
            current_process = select_from_queues(queues)
            start_processing = time if (current_process) else None
    else:
        current_process = select_from_queues(queues)
        if (current_process):
            start_processing = time
    
    logger.info("=========================================================")
    logger.info(f"Time: {str(time)}")
    logger.info(f"Current Process: {str(current_process)}")
    for priority in range(1, 4):
        out = f"Queue {str(priority)}: ["
        for proceses in queues[priority]["queue"]:
            out += f"{proceses}, "
        out +="]"
        logger.info(out)
    logger.info("=========================================================")
    
    if (all(process.is_completed() for process in processes)):
        logger.info("All processes have completed execution.")
        logger.info(f"Gantt Chart: {str(finished_jobs)}")
        break
    
    time += 1

