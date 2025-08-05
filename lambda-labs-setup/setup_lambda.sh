#!/bin/bash

# ContourPose Setup Script for Lambda Labs
# Run this script after launching your Lambda Labs instance

echo "🚀 Setting up ContourPose on Lambda Labs"
echo "========================================"

# Check GPU
echo "🔍 Checking GPU availability..."
nvidia-smi
python -c "import torch; print(f'PyTorch CUDA: {torch.cuda.is_available()}')"

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y htop screen tmux git curl wget

# Install additional Python packages for ContourPose
echo "🐍 Installing ContourPose dependencies..."
pip install --upgrade pip

# Core ML packages (should already be installed in Lambda Labs)
pip install torch torchvision torchaudio --upgrade

# Computer vision packages
pip install opencv-python==4.8.1.78
pip install opencv-contrib-python==4.8.1.78
pip install Pillow==10.0.0

# Scientific computing
pip install numpy==1.24.3
pip install scipy==1.11.1
pip install scikit-learn==1.3.0
pip install scikit-image==0.21.0

# Data handling
pip install pandas==2.0.3
pip install matplotlib==3.7.2
pip install tqdm==4.65.0
pip install pyyaml==6.0.1
pip install plyfile==0.7.4

# Development tools
pip install tensorboard
pip install ipython
pip install jupyterlab

# Create project directory
echo "📁 Setting up project structure..."
mkdir -p ~/contourpose-project
cd ~/contourpose-project

# Create useful aliases
echo "🔗 Setting up useful aliases..."
cat >> ~/.bashrc << 'EOF'

# ContourPose aliases
alias gpu='nvidia-smi'
alias tb='tensorboard --logdir=logs --host=0.0.0.0 --port=6006'
alias train='python main_lambda.py --train'
alias cpose='cd ~/contourpose-project/ContourPose'
alias logs='tail -f logs/*.json'

# Lambda Labs shortcuts
alias shutdown-in-1h='echo "sudo shutdown -h now" | at now + 60 minutes'
alias shutdown-in-2h='echo "sudo shutdown -h now" | at now + 120 minutes'
alias cancel-shutdown='sudo pkill -f shutdown'

EOF

source ~/.bashrc

# Create helpful scripts
echo "📝 Creating helper scripts..."

# GPU monitoring script
cat > gpu_monitor.py << 'EOF'
import subprocess
import time
import json
from datetime import datetime

def get_gpu_info():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        for i, line in enumerate(lines):
            parts = [p.strip() for p in line.split(', ')]
            if len(parts) >= 5:
                name, mem_used, mem_total, util, temp = parts
                print(f"GPU {i}: {name}")
                print(f"  Memory: {mem_used}MB / {mem_total}MB ({float(mem_used)/float(mem_total)*100:.1f}%)")
                print(f"  Utilization: {util}%")
                print(f"  Temperature: {temp}°C")
                print()
    except Exception as e:
        print(f"Error reading GPU info: {e}")

if __name__ == "__main__":
    while True:
        print(f"\n=== GPU Status at {datetime.now().strftime('%H:%M:%S')} ===")
        get_gpu_info()
        time.sleep(5)
EOF

# Training status script
cat > training_status.py << 'EOF'
import json
import os
import glob
from datetime import datetime

def show_training_status():
    log_files = glob.glob("logs/*_training.json")
    
    if not log_files:
        print("No training logs found.")
        return
    
    for log_file in log_files:
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        if logs:
            latest = logs[-1]
            class_type = latest['class_type']
            epoch = latest['epoch']
            loss = latest['avg_loss']
            lr = latest['learning_rate']
            
            print(f"\n📊 {class_type.upper()} Training Status:")
            print(f"  Epoch: {epoch}")
            print(f"  Loss: {loss:.6f}")
            print(f"  Learning Rate: {lr:.6f}")
            print(f"  Last Update: {latest['timestamp']}")
            
            # Show progress
            if len(logs) > 1:
                first_loss = logs[0]['avg_loss']
                improvement = (first_loss - loss) / first_loss * 100
                print(f"  Improvement: {improvement:.1f}%")

if __name__ == "__main__":
    show_training_status()
EOF

# Cost calculator
cat > cost_calculator.py << 'EOF'
import json
import glob
from datetime import datetime, timedelta

def calculate_costs():
    gpu_costs = {
        "RTX 3090": 0.30,
        "RTX 4090": 0.40,
        "A100": 1.10,
        "V100": 0.50
    }
    
    print("💰 Lambda Labs Cost Calculator")
    print("=" * 30)
    
    # Get training logs
    log_files = glob.glob("logs/*_training.json")
    
    for log_file in log_files:
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        if len(logs) < 2:
            continue
            
        class_type = logs[0]['class_type']
        start_time = datetime.fromisoformat(logs[0]['timestamp'])
        end_time = datetime.fromisoformat(logs[-1]['timestamp'])
        duration = end_time - start_time
        hours = duration.total_seconds() / 3600
        
        print(f"\n{class_type.upper()}:")
        print(f"  Duration: {hours:.1f} hours")
        
        for gpu, cost_per_hour in gpu_costs.items():
            total_cost = hours * cost_per_hour
            print(f"  {gpu}: ${total_cost:.2f}")

if __name__ == "__main__":
    calculate_costs()
EOF

# Make scripts executable
chmod +x *.py

# Test the installation
echo "🧪 Testing installation..."
python -c "
import torch
import cv2
import numpy as np
import matplotlib
print(f'✅ PyTorch: {torch.__version__}')
print(f'✅ OpenCV: {cv2.__version__}')
print(f'✅ NumPy: {np.__version__}')
print(f'✅ CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'✅ GPU: {torch.cuda.get_device_name(0)}')
    print(f'✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB')
"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 Next Steps:"
echo "1. Clone ContourPose: git clone https://github.com/yourusername/ContourPose.git"
echo "2. Copy training script: cp main_lambda.py ContourPose/"
echo "3. Upload your dataset to ~/contourpose-project/ContourPose/data/"
echo "4. Start training: python main_lambda.py --train --class_type obj1"
echo ""
echo "🔧 Useful Commands:"
echo "• gpu                 - Show GPU status"
echo "• tb                  - Start TensorBoard"
echo "• python gpu_monitor.py - Monitor GPU usage"
echo "• python training_status.py - Check training progress"
echo "• python cost_calculator.py - Calculate training costs"
echo ""
echo "⏰ Auto-shutdown:"
echo "• shutdown-in-1h     - Shutdown in 1 hour"
echo "• shutdown-in-2h     - Shutdown in 2 hours"
echo "• cancel-shutdown    - Cancel auto-shutdown"
echo ""
echo "Happy training! 🚀"