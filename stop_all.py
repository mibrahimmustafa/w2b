import subprocess
import sys

def kill_process_on_port(port):
    """Finds and kills the process listening on the specified port (Windows)."""
    try:
        # Run netstat to find the process ID (PID)
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        
        # Look for listening port
        for line in result.stdout.splitlines():
            # Example line: TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       12345
            if f":{port}" in line and "LISTENING" in line:
                # Extract PID (last column)
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid != "0":
                        print(f"🛑 Found process {pid} on port {port}. Killing it...")
                        # Kill the process and its children (/T) forcefully (/F)
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
                        print(f"✅ Process {pid} and its children killed.")
                        return True
        print(f"ℹ️ No process found listening on port {port}.")
        return False
    except Exception as e:
        print(f"❌ Error killing process on port {port}: {e}")
        return False

def stop_all():
    print("🛑 W2B Scraper: Stopping Full System...\n")
    
    ports_to_kill = [
        ("FastAPI Backend", 8000),
        ("Vector DB API", 8001),
        ("Next.js Frontend", 3000)
    ]
    
    for name, port in ports_to_kill:
        print(f"Checking {name} (Port {port})...")
        kill_process_on_port(port)
        print("-" * 30)
        
    print("\n✅ All specified servers have been stopped!")

if __name__ == "__main__":
    if sys.platform != "win32":
        print("❌ This script is currently designed for Windows.")
        sys.exit(1)
        
    stop_all()
