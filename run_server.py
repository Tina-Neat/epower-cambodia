"""
run_server.py - Background Headless Server Runner for E-Power Cambodia
Runs directly via pythonw without displaying any CMD window.
Binds to 0.0.0.0:8000 (Online Wi-Fi/LAN + Offline Localhost).
Saves logs to server.log.
"""
import os
import sys
import time
import socket
import uvicorn

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    # Anchor strictly to this project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Write PID for process tracking
    pid_file = os.path.join(project_dir, "server.pid")
    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    # Write server info for run.bat
    local_ip = get_local_ip()
    info_file = os.path.join(project_dir, "server_info.txt")
    try:
        with open(info_file, "w", encoding="utf-8") as f:
            f.write(f"LOCAL_IP={local_ip}\n")
            f.write(f"PORT=8000\n")
            f.write(f"OFFLINE_URL=http://localhost:8000\n")
            f.write(f"ONLINE_URL=http://{local_ip}:8000\n")
    except Exception:
        pass

    # Redirect stdout and stderr to server.log
    log_path = os.path.join(project_dir, "server.log")
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log
    sys.stderr = log

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n======================================================")
    print(f"  E-POWER CAMBODIA SERVER STARTED: {timestamp}")
    print(f"  - Offline URL : http://localhost:8000")
    print(f"  - Online URL  : http://{local_ip}:8000")
    print(f"======================================================")

    from web_app import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
