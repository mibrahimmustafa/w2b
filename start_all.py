import subprocess
import time
import sys
import os

def run_scraper_system():
    print("🚀 W2B Scraper: Launching Full System...")
    
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_script = os.path.join(current_dir, "app", "main.py")
    frontend_dir = os.path.join(current_dir, "frontend")
    
    vector_db_script = os.path.join(current_dir, "vectorDB_API", "main.py")
    
    # 1. Start Backend
    print("📦 Starting FastAPI Backend (Port 8000)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = current_dir
    backend_proc = subprocess.Popen([sys.executable, backend_script], env=env)
    
    # Wait for backend to start
    time.sleep(2)

    # 1.5 Start Vector DB API
    print("🧠 Starting Vector DB API (Port 8001)...")
    vectordb_proc = subprocess.Popen([sys.executable, vector_db_script], env=env)
    
    time.sleep(2)
    
    # 2. Start Frontend
    print("🎨 Starting Next.js Frontend (Port 3000)...")
    try:
        frontend_proc = subprocess.Popen("npm run dev", cwd=frontend_dir, shell=True)
    except FileNotFoundError:
        print("❌ Error: 'npm' not found. Please ensure Node.js is installed.")
        backend_proc.terminate()
        vectordb_proc.terminate()
        return

    print("\n✅ System Running!")
    print("👉 Dashboard: http://localhost:3000")
    print("👉 Scraper API Docs:  http://localhost:8000/docs")
    print("👉 Vector DB API Docs: http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop all servers.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        backend_proc.terminate()
        vectordb_proc.terminate()
        frontend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    run_scraper_system()
