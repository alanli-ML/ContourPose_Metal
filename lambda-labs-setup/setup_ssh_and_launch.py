#!/usr/bin/env python3
"""
Complete Lambda Labs setup: Add SSH key and launch instance for ContourPose
"""
import os
import requests
import json
import time
import subprocess

def get_api_key():
    """Load API key from .env file"""
    with open('.env', 'r') as f:
        return f.read().strip().split('=')[1]

def get_public_key():
    """Get the public SSH key"""
    try:
        with open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("❌ SSH key not found. Please run ssh-keygen first.")
        return None

def add_ssh_key(api_key, public_key, key_name="contourpose-key"):
    """Add SSH key to Lambda Labs account"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": key_name,
        "public_key": public_key
    }
    
    response = requests.post(
        "https://cloud.lambdalabs.com/api/v1/ssh-keys",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 409:
        print(f"🔑 SSH key '{key_name}' already exists")
        return {"data": {"name": key_name}}
    else:
        print(f"❌ Error adding SSH key: {response.status_code}")
        print(response.text)
        return None

def launch_instance(api_key, ssh_key_name):
    """Launch the best available instance"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Get available instances
    response = requests.get("https://cloud.lambdalabs.com/api/v1/instance-types", headers=headers)
    instance_types = response.json()
    
    # Find best available instance
    preferred_types = [
        "gpu_1x_a100_sxm4",
        "gpu_8x_v100", 
        "gpu_1x_a100",
        "gpu_8x_a100_80gb_sxm4"
    ]
    
    for instance_type in preferred_types:
        if instance_type in instance_types["data"]:
            instance_info = instance_types["data"][instance_type]
            regions = instance_info["regions_with_capacity_available"]
            
            if regions:
                print(f"🎯 Launching: {instance_info['instance_type']['description']}")
                print(f"💰 Cost: ${instance_info['instance_type']['price_cents_per_hour']/100:.2f}/hour")
                
                # Launch instance
                launch_data = {
                    "region_name": regions[0]["name"],
                    "instance_type_name": instance_type,
                    "ssh_key_names": [ssh_key_name],
                    "name": f"contourpose-{int(time.time())}"
                }
                
                response = requests.post(
                    "https://cloud.lambdalabs.com/api/v1/instance-operations/launch",
                    headers=headers,
                    json=launch_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    instance_id = result["data"]["instance_ids"][0]
                    return {
                        "instance_id": instance_id,
                        "instance_type": instance_type,
                        "region": regions[0]["name"],
                        "name": launch_data["name"],
                        "cost_per_hour": instance_info['instance_type']['price_cents_per_hour']/100
                    }
                else:
                    print(f"❌ Launch failed: {response.status_code}")
                    print(response.text)
                    continue
    
    return None

def wait_for_instance(api_key, instance_id):
    """Wait for instance to be ready and return IP"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("⏳ Waiting for instance to be ready...")
    
    for i in range(60):  # Wait up to 5 minutes
        time.sleep(5)
        
        response = requests.get("https://cloud.lambdalabs.com/api/v1/instances", headers=headers)
        instances = response.json()
        
        for instance in instances["data"]["instances"]:
            if instance["id"] == instance_id:
                status = instance["status"]
                print(f"   Status: {status}")
                
                if status == "running":
                    return instance["ip"]
                elif status in ["terminated", "terminating"]:
                    print(f"❌ Instance {status}")
                    return None
    
    print("⚠️  Instance taking longer than expected")
    return None

def create_upload_script(ip_address):
    """Create a script to upload ContourPose code and data"""
    upload_script = f"""#!/bin/bash
# Upload ContourPose to Lambda Labs instance

echo "📦 Uploading ContourPose code and data to {ip_address}..."

# Upload the ContourPose code
rsync -avz --progress \\
  --exclude='data/' \\
  --exclude='model/' \\
  --exclude='.git/' \\
  --exclude='__pycache__/' \\
  --exclude='*.pyc' \\
  /Users/alanli/ContourPose/ \\
  ubuntu@{ip_address}:~/contourpose-project/

# Upload the training data
echo "📊 Uploading training data..."
rsync -avz --progress \\
  /Users/alanli/ContourPose/data/train/ \\
  ubuntu@{ip_address}:~/contourpose-project/data/train/

# Upload keypoints
rsync -avz --progress \\
  /Users/alanli/ContourPose/keypoints/ \\
  ubuntu@{ip_address}:~/contourpose-project/keypoints/

echo "✅ Upload complete!"
echo "🚀 Ready to start training!"
"""
    
    with open('upload_to_lambda.sh', 'w') as f:
        f.write(upload_script)
    os.chmod('upload_to_lambda.sh', 0o755)
    
    return 'upload_to_lambda.sh'

def create_training_script(ip_address):
    """Create a script to start training on the remote instance"""
    training_script = f"""#!/bin/bash
# Start ContourPose training on Lambda Labs

echo "🚀 Starting ContourPose training on {ip_address}..."

ssh ubuntu@{ip_address} << 'EOF'
cd ~/contourpose-project
source contourpose-env/bin/activate

# Test GPU
echo "🔧 Testing GPU..."
python3 -c "import torch; print(f'CUDA available: {{torch.cuda.is_available()}}'); print(f'GPU count: {{torch.cuda.device_count()}}')"

# Start training
echo "🎯 Starting training for obj1..."
python3 main.py --class_type obj1 --epochs 150 --batch_size 8 --lr 0.001

echo "✅ Training complete!"
EOF
"""
    
    with open('start_training.sh', 'w') as f:
        f.write(training_script)
    os.chmod('start_training.sh', 0o755)
    
    return 'start_training.sh'

def main():
    print("🤖 Lambda Labs ContourPose Complete Setup")
    print("=" * 50)
    
    # Get API key
    api_key = get_api_key()
    
    # Get public key
    public_key = get_public_key()
    if not public_key:
        return
    
    print(f"🔑 Adding SSH key to Lambda Labs...")
    
    # Add SSH key
    key_result = add_ssh_key(api_key, public_key)
    if not key_result:
        return
    
    ssh_key_name = key_result["data"]["name"]
    print(f"✅ SSH key added: {ssh_key_name}")
    
    # Launch instance
    print(f"🚀 Launching instance...")
    instance_info = launch_instance(api_key, ssh_key_name)
    
    if not instance_info:
        print("❌ No suitable instances available")
        return
    
    print(f"✅ Instance launched: {instance_info['instance_id']}")
    
    # Wait for instance to be ready
    ip = wait_for_instance(api_key, instance_info['instance_id'])
    
    if not ip:
        print("❌ Instance failed to start")
        return
    
    print(f"🎉 Instance ready!")
    print(f"   IP: {ip}")
    print(f"   SSH: ssh ubuntu@{ip}")
    print(f"   Cost: ${instance_info['cost_per_hour']:.2f}/hour")
    
    # Create helper scripts
    upload_script = create_upload_script(ip)
    training_script = create_training_script(ip)
    
    print(f"\n📋 Next steps:")
    print(f"   1. Upload code and data: ./{upload_script}")
    print(f"   2. Start training: ./{training_script}")
    print(f"   3. Monitor: ssh ubuntu@{ip}")
    print(f"\n💰 Estimated costs:")
    print(f"   6 hours: ${instance_info['cost_per_hour'] * 6:.2f}")
    print(f"   24 hours: ${instance_info['cost_per_hour'] * 24:.2f}")
    print(f"\n⚠️  Remember to terminate when done!")
    
    # Save instance info
    with open('instance_info.json', 'w') as f:
        json.dump({
            **instance_info,
            "ip": ip,
            "ssh_command": f"ssh ubuntu@{ip}"
        }, f, indent=2)
    
    print(f"📄 Instance info saved to: instance_info.json")

if __name__ == "__main__":
    main()