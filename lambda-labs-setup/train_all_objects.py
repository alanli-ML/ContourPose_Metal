#!/usr/bin/env python3
"""
Automated training script for all ContourPose objects on Lambda Labs
This script trains multiple objects sequentially with proper monitoring and cost tracking
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime, timedelta

# ContourPose object mapping (from README.md)
OBJECT_MAPPING = {
    # Paper index -> Actual code index
    "obj1": "obj1",   # obj1 in paper -> obj1 in code  
    "obj2": "obj2",   # obj2 in paper -> obj2 in code
    "obj3": "obj3",   # obj3 in paper -> obj3 in code
    "obj4": "obj7",   # obj4 in paper -> obj7 in code
    "obj5": "obj13",  # obj5 in paper -> obj13 in code
    "obj6": "obj16",  # obj6 in paper -> obj16 in code
    "obj7": "obj18",  # obj7 in paper -> obj18 in code
    "obj8": "obj18",  # obj8 in paper -> obj18 in code (duplicate)
    "obj9": "obj21",  # obj9 in paper -> obj21 in code
    "obj10": "obj32"  # obj10 in paper -> obj32 in code
}

# Get unique objects (remove duplicates)
UNIQUE_OBJECTS = list(set(OBJECT_MAPPING.values()))

def log_message(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def estimate_costs(objects, gpu_type="RTX 4090"):
    """Estimate training costs"""
    gpu_costs = {
        "RTX 3090": 0.30,
        "RTX 4090": 0.40,
        "A100": 1.10,
        "V100": 0.50
    }
    
    cost_per_hour = gpu_costs.get(gpu_type, 0.40)
    hours_per_object = 5  # Estimated average
    total_hours = len(objects) * hours_per_object
    total_cost = total_hours * cost_per_hour
    
    log_message(f"Cost Estimate for {len(objects)} objects:")
    log_message(f"  GPU: {gpu_type} @ ${cost_per_hour}/hour")
    log_message(f"  Time: ~{total_hours} hours")
    log_message(f"  Cost: ~${total_cost:.2f}")
    
    return total_cost, total_hours

def check_requirements():
    """Check if all requirements are met"""
    log_message("Checking requirements...")
    
    # Check if in ContourPose directory
    if not os.path.exists("main_lambda.py"):
        log_message("ERROR: main_lambda.py not found. Run from ContourPose directory.", "ERROR")
        return False
    
    # Check if keypoints exist
    missing_keypoints = []
    for obj in UNIQUE_OBJECTS:
        keypoint_file = f"keypoints/{obj}.txt"
        if not os.path.exists(keypoint_file):
            missing_keypoints.append(obj)
    
    if missing_keypoints:
        log_message(f"ERROR: Missing keypoint files for: {missing_keypoints}", "ERROR")
        return False
    
    # Check if data directory exists
    if not os.path.exists("data"):
        log_message("WARNING: data directory not found. Make sure to upload your dataset.", "WARN")
    
    # Check GPU
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode != 0:
            log_message("ERROR: nvidia-smi failed. GPU not available?", "ERROR")
            return False
    except FileNotFoundError:
        log_message("ERROR: nvidia-smi not found. NVIDIA drivers not installed?", "ERROR")
        return False
    
    log_message("✅ All requirements check passed!")
    return True

def train_object(obj, args):
    """Train a single object"""
    log_message(f"🎯 Starting training for {obj}")
    
    cmd = [
        "python", "main_lambda.py",
        "--train",
        "--class_type", obj,
        "--epochs", str(args.epochs),
        "--batch_size", str(args.batch_size),
        "--lr", str(args.lr),
        "--save_interval", str(args.save_interval),
        "--num_workers", str(args.num_workers)
    ]
    
    if args.auto_shutdown > 0:
        cmd.extend(["--auto_shutdown", str(args.auto_shutdown)])
    
    log_message(f"Command: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        # Run training
        result = subprocess.run(cmd, check=True)
        
        duration = time.time() - start_time
        log_message(f"✅ {obj} training completed in {duration/3600:.1f} hours")
        
        return True, duration
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        log_message(f"❌ {obj} training failed after {duration/3600:.1f} hours", "ERROR")
        log_message(f"Error: {e}", "ERROR")
        
        return False, duration

def save_training_summary(results, total_time, args):
    """Save training summary to JSON"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_time_hours": total_time / 3600,
        "args": vars(args),
        "results": results,
        "successful_objects": sum(1 for r in results if r["success"]),
        "failed_objects": sum(1 for r in results if not r["success"]),
        "estimated_cost_usd": (total_time / 3600) * 0.40  # RTX 4090 rate
    }
    
    os.makedirs("logs", exist_ok=True)
    summary_file = f"logs/training_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    log_message(f"📄 Training summary saved to {summary_file}")

def main():
    parser = argparse.ArgumentParser(description="Train all ContourPose objects on Lambda Labs")
    
    # Training parameters
    parser.add_argument("--objects", nargs="+", default=UNIQUE_OBJECTS,
                       help="Objects to train (default: all unique objects)")
    parser.add_argument("--epochs", type=int, default=150,
                       help="Number of epochs per object")
    parser.add_argument("--batch_size", type=int, default=8,
                       help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001,
                       help="Learning rate")
    parser.add_argument("--save_interval", type=int, default=10,
                       help="Save model every N epochs")
    parser.add_argument("--num_workers", type=int, default=8,
                       help="Number of data loading workers")
    
    # Lambda Labs specific
    parser.add_argument("--auto_shutdown", type=int, default=0,
                       help="Auto-shutdown after N hours (0 to disable)")
    parser.add_argument("--skip_failed", action="store_true",
                       help="Continue training even if some objects fail")
    parser.add_argument("--dry_run", action="store_true",
                       help="Show what would be trained without actually training")
    
    args = parser.parse_args()
    
    # Validate objects
    invalid_objects = [obj for obj in args.objects if obj not in UNIQUE_OBJECTS]
    if invalid_objects:
        log_message(f"ERROR: Invalid objects: {invalid_objects}", "ERROR")
        log_message(f"Valid objects: {UNIQUE_OBJECTS}", "INFO")
        return 1
    
    log_message("🚀 ContourPose Multi-Object Training on Lambda Labs")
    log_message("=" * 60)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Show training plan
    log_message(f"📋 Training Plan:")
    log_message(f"  Objects: {args.objects}")
    log_message(f"  Epochs per object: {args.epochs}")
    log_message(f"  Batch size: {args.batch_size}")
    log_message(f"  Learning rate: {args.lr}")
    
    # Estimate costs
    total_cost, total_hours = estimate_costs(args.objects)
    
    if args.dry_run:
        log_message("🏃 Dry run complete - no actual training performed")
        return 0
    
    # Confirm training
    print(f"\nThis will cost approximately ${total_cost:.2f} and take ~{total_hours} hours.")
    if input("Continue? (y/N): ").lower() != 'y':
        log_message("Training cancelled by user")
        return 0
    
    # Start training
    log_message("🎓 Starting multi-object training...")
    
    results = []
    total_start = time.time()
    
    for i, obj in enumerate(args.objects, 1):
        log_message(f"📊 Progress: {i}/{len(args.objects)} objects")
        
        success, duration = train_object(obj, args)
        
        result = {
            "object": obj,
            "success": success,
            "duration_hours": duration / 3600,
            "timestamp": datetime.now().isoformat()
        }
        results.append(result)
        
        if not success and not args.skip_failed:
            log_message(f"❌ Training failed for {obj}. Stopping.", "ERROR")
            break
        
        # Small break between objects
        if i < len(args.objects):
            log_message("⏸️  Waiting 30 seconds before next object...")
            time.sleep(30)
    
    total_time = time.time() - total_start
    
    # Show final results
    log_message("🎉 Multi-object training completed!")
    log_message("=" * 60)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    log_message(f"✅ Successful: {len(successful)}/{len(results)} objects")
    log_message(f"❌ Failed: {len(failed)} objects")
    log_message(f"⏱️  Total time: {total_time/3600:.1f} hours")
    log_message(f"💰 Estimated cost: ${(total_time/3600)*0.40:.2f}")
    
    if successful:
        log_message("Successful objects:")
        for r in successful:
            log_message(f"  ✅ {r['object']} ({r['duration_hours']:.1f}h)")
    
    if failed:
        log_message("Failed objects:")
        for r in failed:
            log_message(f"  ❌ {r['object']} ({r['duration_hours']:.1f}h)")
    
    # Save summary
    save_training_summary(results, total_time, args)
    
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())