#!/usr/bin/env python3
"""
Monitor Lambda Labs instance status
"""
import requests
import json
import time

def get_api_key():
    with open('.env', 'r') as f:
        return f.read().strip().split('=')[1]

def check_instances():
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get("https://cloud.lambdalabs.com/api/v1/instances", headers=headers)
    data = response.json()
    
    if not data["data"]:
        print("❌ No instances found")
        return None
    
    instance = data["data"][0]  # Get the first (most recent) instance
    
    print(f"🖥️  Instance: {instance['name']}")
    print(f"📊 Status: {instance['status']}")
    print(f"🌍 Region: {instance['region']['description']}")
    print(f"🔧 Type: {instance['instance_type']['description']}")
    print(f"💰 Cost: ${instance['instance_type']['price_cents_per_hour']/100:.2f}/hour")
    
    if instance['status'] == 'running':
        if 'ip' in instance:
            ip = instance['ip']
            print(f"🌐 IP: {ip}")
            print(f"🔗 SSH: ssh ubuntu@{ip}")
            
            # Create connection info
            connection_info = {
                "instance_id": instance['id'],
                "ip": ip,
                "ssh_command": f"ssh ubuntu@{ip}",
                "status": instance['status'],
                "cost_per_hour": instance['instance_type']['price_cents_per_hour']/100
            }
            
            with open('instance_info.json', 'w') as f:
                json.dump(connection_info, f, indent=2)
            
            return ip
        else:
            print("⚠️  Instance running but no IP yet")
    
    return None

def main():
    print("🔍 Checking Lambda Labs instance status...")
    print("=" * 50)
    
    while True:
        ip = check_instances()
        
        if ip:
            print(f"\n✅ Instance ready!")
            print(f"\n📋 Next steps:")
            print(f"   1. SSH: ssh ubuntu@{ip}")
            print(f"   2. Upload data and start training")
            break
        else:
            print(f"⏳ Waiting... (checking again in 10 seconds)")
            time.sleep(10)

if __name__ == "__main__":
    main()