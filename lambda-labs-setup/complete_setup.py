#!/usr/bin/env python3
"""
Complete Lambda Labs Setup Script for ContourPose
Consolidates all setup, launch, upload, and monitoring functionality
"""

import requests
import json
import os
import sys
import subprocess
import time
from datetime import datetime

# Configuration
API_KEY_FILE = "lambda_api_key.txt"
API_URL = "https://cloud.lambdalabs.com/api/v1"
SSH_KEY_NAME = "contourpose-key"
LOCAL_PROJECT_ROOT = "/Users/alanli/ContourPose"

class LambdaLabsManager:
    def __init__(self):
        self.api_key = self.load_api_key()
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.instance_id = None
        self.instance_ip = None
        self.ssh_user = "ubuntu"

    def load_api_key(self):
        """Load API key from file"""
        if not os.path.exists(API_KEY_FILE):
            print(f"❌ API key file not found: {API_KEY_FILE}")
            print("Please create the file with your Lambda Labs API key")
            sys.exit(1)
        
        with open(API_KEY_FILE, 'r') as f:
            return f.read().strip()

    def get_available_instances(self):
        """Get available instance types"""
        response = requests.get(f"{API_URL}/instance-types", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def find_best_instance(self):
        """Find the best available instance for ContourPose"""
        instance_types = self.get_available_instances()
        
        # Preference order: A100 40GB > RTX 4090 > RTX 3090 > A10G
        preferred_gpus = ["A100 SXM4 40 GB", "RTX 4090", "RTX 3090", "A10G"]
        
        for gpu in preferred_gpus:
            for instance_type in instance_types["data"]:
                if gpu in instance_type["instance_type"]["description"]:
                    regions = self.get_available_regions(instance_type["instance_type"]["name"])
                    if regions:
                        return instance_type["instance_type"], regions[0]
        
        print("❌ No suitable GPU instances available")
        return None, None

    def get_available_regions(self, instance_type_name):
        """Get available regions for instance type"""
        response = requests.get(f"{API_URL}/instance-types", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        for instance_type in data["data"]:
            if instance_type["instance_type"]["name"] == instance_type_name:
                return [region for region in instance_type["regions_with_capacity_available"]]
        return []

    def setup_ssh_key(self):
        """Generate and upload SSH key"""
        ssh_key_path = os.path.expanduser(f"~/.ssh/{SSH_KEY_NAME}")
        
        if not os.path.exists(ssh_key_path):
            print("🔑 Generating SSH key...")
            subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "4096", 
                "-f", ssh_key_path, "-N", "", "-C", "contourpose@lambdalabs"
            ], check=True)
        
        # Read public key
        with open(f"{ssh_key_path}.pub", 'r') as f:
            public_key = f.read().strip()
        
        # Upload to Lambda Labs
        response = requests.post(
            f"{API_URL}/ssh-keys",
            headers=self.headers,
            json={"name": SSH_KEY_NAME, "public_key": public_key}
        )
        
        if response.status_code == 409:
            print("✅ SSH key already exists")
        else:
            response.raise_for_status()
            print("✅ SSH key uploaded successfully")
        
        return ssh_key_path

    def launch_instance(self, instance_type, region, ssh_key_path):
        """Launch a Lambda Labs instance"""
        launch_data = {
            "region_name": region["name"],
            "instance_type_name": instance_type["name"],
            "ssh_key_names": [SSH_KEY_NAME]
        }
        
        print(f"🚀 Launching {instance_type['description']} in {region['description']}...")
        response = requests.post(f"{API_URL}/instance-operations/launch", 
                               headers=self.headers, json=launch_data)
        response.raise_for_status()
        
        self.instance_id = response.json()["data"]["instance_ids"][0]
        print(f"✅ Instance launched: {self.instance_id}")
        
        # Wait for instance to be ready
        self.wait_for_instance()
        return self.instance_id

    def wait_for_instance(self):
        """Wait for instance to be running and get IP"""
        print("⏳ Waiting for instance to start...")
        
        for attempt in range(60):  # Wait up to 10 minutes
            response = requests.get(f"{API_URL}/instances", headers=self.headers)
            response.raise_for_status()
            
            instances = response.json().get('data', [])
            if not instances:
                time.sleep(10)
                continue
                
            instance = instances[0]  # Get the first (latest) instance
            status = instance.get('status')
            
            if status == 'running':
                self.instance_ip = instance['ip']
                print(f"✅ Instance ready! IP: {self.instance_ip}")
                return
            elif status in ['terminated', 'terminating']:
                print(f"❌ Instance failed to start (status: {status})")
                sys.exit(1)
            
            print(f"⏳ Instance status: {status}, waiting...")
            time.sleep(10)
        
        print("❌ Timeout waiting for instance")
        sys.exit(1)

    def upload_project(self):
        """Upload ContourPose project and data to instance"""
        if not self.instance_ip:
            print("❌ No instance IP available")
            return
        
        print("📤 Uploading ContourPose project...")
        
        # Upload main project files
        subprocess.run([
            "rsync", "-avz", "--progress",
            "--exclude", "data/", "--exclude", "model/", "--exclude", ".git/",
            "--exclude", "__pycache__/", "--exclude", "*.pyc", "--exclude", "*.log",
            "--exclude", ".DS_Store", "--exclude", "lambda-labs-setup/",
            f"{LOCAL_PROJECT_ROOT}/",
            f"{self.ssh_user}@{self.instance_ip}:~/contourpose-project/ContourPose/"
        ], check=True)
        
        # Upload training data if exists
        if os.path.exists(f"{LOCAL_PROJECT_ROOT}/data/train"):
            print("📤 Uploading training data...")
            subprocess.run([
                "rsync", "-avz", "--progress",
                f"{LOCAL_PROJECT_ROOT}/data/train/",
                f"{self.ssh_user}@{self.instance_ip}:~/contourpose-project/ContourPose/data/train/"
            ], check=True)
        
        # Upload keypoints
        if os.path.exists(f"{LOCAL_PROJECT_ROOT}/keypoints"):
            print("📤 Uploading keypoints...")
            subprocess.run([
                "rsync", "-avz", "--progress",
                f"{LOCAL_PROJECT_ROOT}/keypoints/",
                f"{self.ssh_user}@{self.instance_ip}:~/contourpose-project/ContourPose/keypoints/"
            ], check=True)
        
        print("✅ Project upload complete")

    def setup_environment(self):
        """Setup Python environment and dependencies on remote instance"""
        if not self.instance_ip:
            print("❌ No instance IP available")
            return
        
        print("🔧 Setting up environment...")
        
        setup_commands = [
            "cd ~/contourpose-project",
            "python3 -m venv contourpose-env",
            "source contourpose-env/bin/activate",
            "pip install --upgrade pip",
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118",
            "pip install opencv-python opencv-contrib-python",
            "pip install scikit-learn scikit-image scipy",
            "pip install matplotlib tqdm pyyaml plyfile",
            "pip install tensorboard ipython",
            "pip install numpy==1.26.4",  # Fix NumPy compatibility
            "echo 'Environment setup complete'"
        ]
        
        subprocess.run([
            "ssh", f"{self.ssh_user}@{self.instance_ip}",
            " && ".join(setup_commands)
        ], check=True)
        
        print("✅ Environment setup complete")

    def start_training(self, class_type="obj1", epochs=10, batch_size=8):
        """Start training on the remote instance"""
        if not self.instance_ip:
            print("❌ No instance IP available")
            return
        
        print(f"🚀 Starting training for {class_type} ({epochs} epochs)...")
        
        training_cmd = f"""
        cd ~/contourpose-project/ContourPose && 
        source ../contourpose-env/bin/activate && 
        screen -dmS contourpose-training bash -c "python -u main.py --train --class_type {class_type} --data_path ./data --epochs {epochs} --batch_size {batch_size} | tee training_{class_type}_{epochs}epochs.log"
        """
        
        subprocess.run([
            "ssh", f"{self.ssh_user}@{self.instance_ip}",
            training_cmd
        ], check=True)
        
        print(f"✅ Training started in screen session 'contourpose-training'")
        print(f"📊 Monitor with: ssh {self.ssh_user}@{self.instance_ip} 'screen -r contourpose-training'")

    def monitor_training(self):
        """Monitor training progress"""
        if not self.instance_ip:
            print("❌ No instance IP available")
            return
        
        print("📊 Monitoring training progress...")
        
        while True:
            try:
                # Get training log
                result = subprocess.run([
                    "ssh", f"{self.ssh_user}@{self.instance_ip}",
                    "cd ~/contourpose-project/ContourPose && ls -la *.log | tail -1 && tail -5 *.log 2>/dev/null | tail -5"
                ], capture_output=True, text=True, timeout=30)
                
                if result.stdout:
                    print("\n" + "="*50)
                    print(f"📊 Training Progress ({datetime.now().strftime('%H:%M:%S')})")
                    print("="*50)
                    print(result.stdout)
                
                # Get GPU status
                gpu_result = subprocess.run([
                    "ssh", f"{self.ssh_user}@{self.instance_ip}",
                    "nvidia-smi | grep -A 2 'GPU.*Util'"
                ], capture_output=True, text=True, timeout=30)
                
                if gpu_result.stdout:
                    print("🖥️  GPU Status:")
                    print(gpu_result.stdout)
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
                break
            except subprocess.TimeoutExpired:
                print("⚠️  Connection timeout, retrying...")
                continue

    def terminate_instance(self):
        """Terminate the current instance"""
        if not self.instance_id:
            print("❌ No instance to terminate")
            return
        
        print(f"🛑 Terminating instance {self.instance_id}...")
        
        response = requests.post(
            f"{API_URL}/instance-operations/terminate",
            headers=self.headers,
            json={"instance_ids": [self.instance_id]}
        )
        response.raise_for_status()
        
        print("✅ Instance terminated")

def main():
    if len(sys.argv) < 2:
        print("""
🚀 ContourPose Lambda Labs Manager

Usage:
    python complete_setup.py launch [epochs] [class_type]  - Launch and setup complete environment
    python complete_setup.py monitor                       - Monitor existing training
    python complete_setup.py terminate                     - Terminate instance
    python complete_setup.py quick [epochs]                - Quick training (assumes setup done)

Examples:
    python complete_setup.py launch 10 obj1               - Full setup + 10 epoch training
    python complete_setup.py quick 50                     - Quick 50 epoch training
    python complete_setup.py monitor                      - Monitor training progress
        """)
        return

    command = sys.argv[1]
    manager = LambdaLabsManager()

    if command == "launch":
        epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        class_type = sys.argv[3] if len(sys.argv) > 3 else "obj1"
        
        # Complete setup workflow
        instance_type, region = manager.find_best_instance()
        if not instance_type:
            return
        
        print(f"💰 Selected: {instance_type['description']} (${instance_type['price_cents_per_hour']/100}/hour)")
        ssh_key_path = manager.setup_ssh_key()
        manager.launch_instance(instance_type, region, ssh_key_path)
        manager.upload_project()
        manager.setup_environment()
        manager.start_training(class_type, epochs)
        
        print(f"""
✅ Complete setup finished!

📊 Training Details:
- Class: {class_type}
- Epochs: {epochs}
- Estimated time: {epochs * 4.2:.1f} minutes
- Estimated cost: ${epochs * 4.2 * instance_type['price_cents_per_hour'] / 6000:.2f}

🔗 Connect with Cursor:
ssh {manager.ssh_user}@{manager.instance_ip}

📊 Monitor training:
python complete_setup.py monitor
        """)

    elif command == "monitor":
        # Load existing instance info (you'd need to store this)
        print("📊 Starting training monitor...")
        manager.monitor_training()

    elif command == "terminate":
        manager.terminate_instance()

    elif command == "quick":
        epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        # Quick training (assumes instance exists)
        manager.start_training("obj1", epochs)
        print(f"🚀 Quick training started ({epochs} epochs)")

if __name__ == "__main__":
    main()