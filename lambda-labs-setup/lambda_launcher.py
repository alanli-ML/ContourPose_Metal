#!/usr/bin/env python3
"""
Lambda Labs Instance Launcher for ContourPose Training
"""
import os
import requests
import json
import time
import base64
from typing import Dict, Any, Optional

class LambdaLabsManager:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://cloud.lambdalabs.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_instance_types(self) -> Dict[str, Any]:
        """Get available instance types with capacity"""
        response = requests.get(f"{self.base_url}/instance-types", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_ssh_keys(self) -> Dict[str, Any]:
        """Get available SSH keys"""
        response = requests.get(f"{self.base_url}/ssh-keys", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def launch_instance(self, instance_type: str, region: str, name: str, 
                       ssh_key_names: list, file_system_names: list = None) -> Dict[str, Any]:
        """Launch a new instance"""
        data = {
            "region_name": region,
            "instance_type_name": instance_type,
            "ssh_key_names": ssh_key_names,
            "name": name
        }
        if file_system_names:
            data["file_system_names"] = file_system_names
        
        response = requests.post(f"{self.base_url}/instance-operations/launch", 
                               headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_instances(self) -> Dict[str, Any]:
        """Get all instances"""
        response = requests.get(f"{self.base_url}/instances", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def terminate_instance(self, instance_id: str) -> Dict[str, Any]:
        """Terminate an instance"""
        data = {"instance_ids": [instance_id]}
        response = requests.post(f"{self.base_url}/instance-operations/terminate", 
                               headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

def find_best_instance():
    """Find the best available instance for ContourPose training"""
    # Load API key
    with open('.env', 'r') as f:
        api_key = f.read().strip().split('=')[1]
    
    manager = LambdaLabsManager(api_key)
    
    # Get available instances
    instance_types = manager.get_instance_types()
    
    # Preferred instance types in order of preference (cost vs performance)
    preferred_types = [
        "gpu_1x_a100_sxm4",  # $1.29/hr - Best bang for buck
        "gpu_8x_v100",       # $4.40/hr - Good for multi-GPU training
        "gpu_1x_a100",       # $1.29/hr - PCIe version
        "gpu_8x_a100_80gb_sxm4",  # $14.32/hr - If we want to go big
        "gpu_8x_h100_sxm5",  # $23.92/hr - Overkill but fastest
    ]
    
    print("🔍 Checking available GPU instances...")
    
    for instance_type in preferred_types:
        if instance_type in instance_types["data"]:
            instance_info = instance_types["data"][instance_type]
            regions = instance_info["regions_with_capacity_available"]
            
            if regions:
                print(f"✅ Found available: {instance_info['instance_type']['description']}")
                print(f"   💰 Cost: ${instance_info['instance_type']['price_cents_per_hour']/100:.2f}/hour")
                print(f"   🌍 Available regions: {[r['description'] for r in regions]}")
                
                return {
                    "instance_type": instance_type,
                    "region": regions[0]["name"],  # Use first available region
                    "info": instance_info
                }
    
    print("❌ No suitable GPU instances available")
    return None

def create_startup_script():
    """Create the startup script for the instance"""
    script = """#!/bin/bash
set -e

echo "🚀 Starting ContourPose setup on Lambda Labs..."

# Update system
sudo apt-get update -y

# Install basic tools
sudo apt-get install -y git curl wget unzip python3-pip python3-venv htop

# Create project directory
mkdir -p /home/ubuntu/contourpose-project
cd /home/ubuntu/contourpose-project

# Clone the repository
git clone https://github.com/your-repo/ContourPose.git || echo "Clone failed, continuing..."

# Create virtual environment
python3 -m venv contourpose-env
source contourpose-env/bin/activate

# Install PyTorch with CUDA support
pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install opencv-python numpy scipy matplotlib PyYAML Pillow tqdm

# Set up environment
echo 'source /home/ubuntu/contourpose-project/contourpose-env/bin/activate' >> ~/.bashrc

# Test GPU
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

echo "✅ Setup complete! Ready for ContourPose training."
echo "📁 Project directory: /home/ubuntu/contourpose-project"
echo "🐍 Virtual env: source contourpose-env/bin/activate"
"""
    return script

def main():
    print("🤖 Lambda Labs ContourPose Launcher")
    print("=" * 50)
    
    # Find best available instance
    best_instance = find_best_instance()
    if not best_instance:
        print("\n💡 Try again later or check Lambda Labs dashboard for availability")
        return
    
    # Load API key
    with open('.env', 'r') as f:
        api_key = f.read().strip().split('=')[1]
    
    manager = LambdaLabsManager(api_key)
    
    # Get SSH keys
    try:
        ssh_keys = manager.get_ssh_keys()
        if not ssh_keys["data"]:
            print("\n❌ No SSH keys found. Please add an SSH key in Lambda Labs dashboard first.")
            print("   Go to: https://cloud.lambdalabs.com/ssh-keys")
            return
        
        ssh_key_name = ssh_keys["data"][0]["name"]
        print(f"🔑 Using SSH key: {ssh_key_name}")
        
    except Exception as e:
        print(f"❌ Error getting SSH keys: {e}")
        return
    
    # Confirm launch
    instance_info = best_instance["info"]["instance_type"]
    cost_per_hour = instance_info["price_cents_per_hour"] / 100
    
    print(f"\n🎯 Ready to launch:")
    print(f"   Instance: {instance_info['description']}")
    print(f"   Cost: ${cost_per_hour:.2f}/hour")
    print(f"   Region: {best_instance['region']}")
    
    confirm = input("\n🚀 Launch instance? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ Launch cancelled")
        return
    
    # Launch instance
    try:
        print("🚀 Launching instance...")
        instance_name = f"contourpose-{int(time.time())}"
        
        result = manager.launch_instance(
            instance_type=best_instance["instance_type"],
            region=best_instance["region"],
            name=instance_name,
            ssh_key_names=[ssh_key_name]
        )
        
        instance_id = result["data"]["instance_ids"][0]
        print(f"✅ Instance launched!")
        print(f"   Instance ID: {instance_id}")
        print(f"   Name: {instance_name}")
        
        # Wait for instance to be ready
        print("\n⏳ Waiting for instance to be ready...")
        for i in range(60):  # Wait up to 5 minutes
            time.sleep(5)
            instances = manager.get_instances()
            
            for instance in instances["data"]["instances"]:
                if instance["id"] == instance_id:
                    if instance["status"] == "running":
                        ip = instance["ip"]
                        print(f"🎉 Instance ready!")
                        print(f"   IP: {ip}")
                        print(f"   SSH: ssh ubuntu@{ip}")
                        print(f"\n📋 Next steps:")
                        print(f"   1. SSH into the instance: ssh ubuntu@{ip}")
                        print(f"   2. Upload your ContourPose code and data")
                        print(f"   3. Run training with GPU acceleration")
                        print(f"\n💰 Remember to terminate when done to avoid charges!")
                        print(f"   Estimated cost for 6 hours: ${cost_per_hour * 6:.2f}")
                        return
                    else:
                        print(f"   Status: {instance['status']}")
                        break
        
        print("⚠️  Instance taking longer than expected to start. Check Lambda Labs dashboard.")
        
    except Exception as e:
        print(f"❌ Error launching instance: {e}")

if __name__ == "__main__":
    main()