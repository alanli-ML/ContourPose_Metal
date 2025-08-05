#!/usr/bin/env python3
"""
Monitor ContourPose training progress on Lambda Labs
"""
import subprocess
import time
import re
import json
from datetime import datetime, timedelta

def run_ssh_command(command):
    """Run a command via SSH and return the output"""
    full_command = f"ssh ubuntu@129.158.238.46 '{command}'"
    try:
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def get_gpu_usage():
    """Get current GPU usage stats"""
    command = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits"
    output = run_ssh_command(command)
    
    if output and "ERROR" not in output and "TIMEOUT" not in output:
        parts = output.strip().split(', ')
        if len(parts) >= 5:
            return {
                "gpu_util": f"{parts[0]}%",
                "memory_used": f"{parts[1]} MB",
                "memory_total": f"{parts[2]} MB",
                "temperature": f"{parts[3]}°C",
                "power": f"{parts[4]} W"
            }
    return None

def get_training_progress():
    """Check training progress from screen session"""
    # First check if screen session exists
    screen_check = run_ssh_command("screen -list")
    if "contourpose-training" not in screen_check:
        return {"status": "no_session", "message": "Training session not found"}
    
    # Get recent training output
    command = "screen -S contourpose-training -X hardcopy /tmp/training_output.txt && tail -50 /tmp/training_output.txt"
    output = run_ssh_command(command)
    
    if not output or "ERROR" in output:
        return {"status": "unknown", "message": "Could not read training output"}
    
    # Parse training information
    lines = output.split('\n')
    current_epoch = None
    current_loss = None
    last_loss_line = None
    
    for line in lines:
        # Look for epoch information
        epoch_match = re.search(r'epoch:\s*(\d+)', line.lower())
        if epoch_match:
            current_epoch = int(epoch_match.group(1))
        
        # Look for loss information
        if "loss:" in line.lower() and "heatmap_loss:" in line.lower():
            last_loss_line = line
            loss_match = re.search(r'loss:\s*([\d.]+)', line.lower())
            if loss_match:
                current_loss = float(loss_match.group(1))
    
    return {
        "status": "running",
        "current_epoch": current_epoch,
        "current_loss": current_loss,
        "last_loss_line": last_loss_line,
        "recent_output": '\n'.join(lines[-10:])  # Last 10 lines
    }

def estimate_remaining_time(current_epoch, total_epochs, start_time, iterations_per_epoch=3630):
    """Estimate remaining training time"""
    if not current_epoch or current_epoch == 0:
        return None
    
    elapsed_time = time.time() - start_time
    epochs_completed = current_epoch
    epochs_remaining = total_epochs - current_epoch
    
    time_per_epoch = elapsed_time / epochs_completed
    estimated_remaining = time_per_epoch * epochs_remaining
    
    return {
        "elapsed_hours": elapsed_time / 3600,
        "time_per_epoch_minutes": time_per_epoch / 60,
        "estimated_remaining_hours": estimated_remaining / 3600,
        "estimated_completion": datetime.now() + timedelta(seconds=estimated_remaining)
    }

def calculate_cost(hours, rate_per_hour=1.29):
    """Calculate training cost"""
    return hours * rate_per_hour

def main():
    print("🔍 ContourPose Training Monitor")
    print("=" * 60)
    
    # Assume training started recently (you can adjust this)
    training_start_time = time.time() - 300  # Assume started 5 minutes ago
    total_epochs = 150
    
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📊 Status Check - {current_time}")
        print("-" * 40)
        
        # Get GPU usage
        gpu_stats = get_gpu_usage()
        if gpu_stats:
            print("🔥 GPU Status:")
            print(f"   Utilization: {gpu_stats['gpu_util']}")
            print(f"   Memory: {gpu_stats['memory_used']} / {gpu_stats['memory_total']}")
            print(f"   Temperature: {gpu_stats['temperature']}")
            print(f"   Power: {gpu_stats['power']}")
        else:
            print("⚠️  Could not get GPU stats")
        
        # Get training progress
        progress = get_training_progress()
        print(f"\n🎯 Training Status: {progress['status']}")
        
        if progress['status'] == 'running':
            if progress['current_epoch']:
                print(f"   Current Epoch: {progress['current_epoch']}/{total_epochs}")
                print(f"   Progress: {progress['current_epoch']/total_epochs*100:.1f}%")
                
                # Estimate remaining time
                time_estimate = estimate_remaining_time(
                    progress['current_epoch'], 
                    total_epochs, 
                    training_start_time
                )
                
                if time_estimate:
                    print(f"   Elapsed: {time_estimate['elapsed_hours']:.1f} hours")
                    print(f"   Time per epoch: {time_estimate['time_per_epoch_minutes']:.1f} minutes")
                    print(f"   Estimated remaining: {time_estimate['estimated_remaining_hours']:.1f} hours")
                    print(f"   Estimated completion: {time_estimate['estimated_completion'].strftime('%Y-%m-%d %H:%M')}")
                    
                    # Cost calculation
                    total_cost = calculate_cost(time_estimate['elapsed_hours'] + time_estimate['estimated_remaining_hours'])
                    current_cost = calculate_cost(time_estimate['elapsed_hours'])
                    print(f"\n💰 Cost:")
                    print(f"   Current cost: ${current_cost:.2f}")
                    print(f"   Estimated total: ${total_cost:.2f}")
            
            if progress['current_loss']:
                print(f"   Current Loss: {progress['current_loss']:.6f}")
            
            if progress['last_loss_line']:
                print(f"   Last Loss Line: {progress['last_loss_line'].strip()}")
        
        elif progress['status'] == 'no_session':
            print("❌ Training session not found!")
            break
        
        print(f"\n📝 Recent Output:")
        if progress.get('recent_output'):
            recent_lines = progress['recent_output'].split('\n')[-3:]  # Last 3 lines
            for line in recent_lines:
                if line.strip():
                    print(f"   {line.strip()}")
        
        print("\n" + "="*60)
        print("⏳ Refreshing in 30 seconds... (Ctrl+C to stop)")
        
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped.")
            break

if __name__ == "__main__":
    main()