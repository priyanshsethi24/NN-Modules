import psutil

# List of Office processes
def terminate_active_processes():
    office_apps = ["WINWORD.EXE", "EXCEL.EXE", "POWERPNT.EXE", "OUTLOOK.EXE"]
    print("Checking for Active processes")
    # Check for running processes and terminate them
    for process in psutil.process_iter(['name']):
        try:
            if process.info['name'] in office_apps:
                print(f"{process.info['name']} is running. Attempting to close...")
                process.terminate()  # Gracefully terminate the process
                process.wait(timeout=5)  # Wait up to 5 seconds for the process to terminate
                print(f"{process.info['name']} has been closed.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"Could not terminate {process.info['name']} due to: {e}")
    print("Terminated active processes")
    return