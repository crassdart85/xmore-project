import subprocess
import sys
import time
import os
from datetime import datetime

def run_script(script_name):
    """Run a Python script and check for success"""
    print(f"\n{'='*60}")
    print(f"🎬 Running {script_name}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run([sys.executable, script_name], capture_output=False)
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ {script_name} completed successfully in {duration:.2f}s")
        return True
    else:
        print(f"❌ {script_name} failed with exit code {result.returncode}")
        return False

def main():
    print(f"🚀 Starting Stock Prediction Pipeline at {datetime.now()}")
    
    # 1. Collect Data (Prices + News Sentiment)
    if not run_script("collect_data.py"):
        print("🛑 Pipeline stopped due to data collection failure.")
        return

    # 2. Train Model (Random Forest)
    # Only strictly necessary if we want to retrain on new data every time.
    # For production, you might run this less often (e.g., weekly), but for this robust pipeline we'll include it.
    if not run_script("train_model.py"):
        print("🛑 Pipeline stopped due to training failure.")
        return

    # 3. Generate Predictions (using MLAgent)
    if not run_script("run_agents.py"):
        print("🛑 Pipeline stopped due to prediction failure.")
        return

    # 4. Evaluate Past Predictions (Self-Correction)
    if not run_script("evaluate.py"):
        print("⚠️ Evaluation failed, but continuing pipeline.")

    print("\n" + "="*60)
    print("🎉 Pipeline Completed Successfully!")
    print("="*60)
    
    # Check if we should help start the web server
    web_dir = os.path.join(os.getcwd(), "web-ui")
    print("\n🌐 To view results on the dashboard:")
    print(f"   1. Navigate to: {web_dir}")
    print("   2. Run: npm start")
    print("   3. Open: http://localhost:3000")

if __name__ == "__main__":
    main()
