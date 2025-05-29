# Start GUI for JAILA
# Dette script starter Streamlit-interfacet for JAILA

import subprocess
import os
import sys
import socket
import time
import signal
from pathlib import Path
from contextlib import closing

def find_free_port():
    """Find en ledig port at bruge til Streamlit"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def is_port_in_use(port):
    """Tjek om en port er i brug"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """Dræb process der kører på den angivne port (kun Windows)"""
    try:
        # Find PID for processen der bruger porten
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        lines = output.strip().split('\n')
        
        if lines:
            # Sidste tal på linjen er PID
            for line in lines:
                if f":{port}" in line:
                    parts = line.strip().split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        print(f"Afslutter process med PID {pid} på port {port}...")
                        try:
                            subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                            time.sleep(1)  # Vent på at processen afsluttes
                            return True
                        except Exception as e:
                            print(f"Kunne ikke afslutte process: {e}")
    except Exception as e:
        print(f"Fejl ved forsøg på at finde og afslutte process: {e}")
    
    return False

def main():
    print("Starter JAILA GUI...")
    # Find stien til gui.py filen
    script_dir = Path(__file__).parent
    gui_path = script_dir / "JAILA" / "gui.py"
    
    # Tjek om Streamlit er installeret
    try:
        import streamlit
        print("Streamlit er installeret. Version:", streamlit.__version__)
    except ImportError:
        print("Streamlit er ikke installeret. Installerer nu...")
        subprocess.call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("Streamlit installeret.")
    
    # Find en ledig port
    port = find_free_port()
    print(f"Bruger port {port} til Streamlit.")
    
    # Start Streamlit server med den ledige port
    print(f"Starter Streamlit server med {gui_path} på port {port}...")
    print(f"Når serveren er startet, åbn http://localhost:{port} i din browser.")
    subprocess.call(["streamlit", "run", str(gui_path), f"--server.port={port}"])

if __name__ == "__main__":
    main()
