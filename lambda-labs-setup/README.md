# ContourPose Lambda Labs Training Suite

Complete training solution for ContourPose on Lambda Labs with automatic model synchronization, optimized for A100 GPUs.

## 🚀 Quick Start

### 1. Setup
```bash
cd lambda-labs-setup

# Add your Lambda Labs API key
echo "your_lambda_api_key_here" > lambda_api_key.txt

# Ensure SSH key is available (should already exist)
ls -la contourpose-key
```

### 2. Launch Training with Auto Model Sync
```bash
# Start complete training session
python3 contourpose_trainer.py launch --class-type obj1 --epochs 10 --monitor

# Or launch without immediate monitoring
python3 contourpose_trainer.py launch --class-type obj1 --epochs 10
```

### 3. Monitor and Manage
```bash
# Check status
python3 contourpose_trainer.py status

# Monitor training progress
python3 contourpose_trainer.py monitor

# Start/check model sync
python3 contourpose_trainer.py sync

# Terminate when done
python3 contourpose_trainer.py terminate
```

## 📁 What You Get

### Automatic Features
- ✅ **A100 Instance Management** - Automatic launch and setup
- ✅ **Environment Setup** - Complete Python environment with optimized settings
- ✅ **Model Auto-Download** - Models synced every 60 seconds to local storage
- ✅ **Training Monitoring** - Real-time progress tracking
- ✅ **Cost Tracking** - Runtime and cost estimation
- ✅ **Graceful Cleanup** - Proper instance termination with final model sync

### Optimized Performance
- 🎯 **Optimal Configuration**: `batch_size=16`, `num_workers=8`
- 🚀 **4.9x Speedup**: 3.76 min/epoch (vs 18.59 min unoptimized)
- 💰 **80% Cost Reduction**: $0.81 per 10 epochs (vs $4.00)
- 📈 **96% GPU Utilization**: Maximum A100 efficiency

## 🛠️ Commands Reference

### Primary Command: `contourpose_trainer.py`

This single script handles everything:

```bash
# Launch new training session
python3 contourpose_trainer.py launch [OPTIONS]

# Monitor existing training
python3 contourpose_trainer.py monitor

# Check status and costs
python3 contourpose_trainer.py status

# Manual model sync
python3 contourpose_trainer.py sync

# Terminate instance (with final model download)
python3 contourpose_trainer.py terminate
```

### Launch Options
```bash
--class-type TYPE     Object to train (obj1, obj2, etc.) [default: obj1]
--epochs NUM          Number of epochs [default: 10]
--batch-size NUM      Batch size [default: 16]
--monitor            Start monitoring immediately after launch
--sync-interval NUM   Model sync interval in seconds [default: 60]
```

### Examples
```bash
# Quick 10-epoch training for obj1
python3 contourpose_trainer.py launch

# Train obj2 for 50 epochs with monitoring
python3 contourpose_trainer.py launch --class-type obj2 --epochs 50 --monitor

# Train with smaller batch size
python3 contourpose_trainer.py launch --batch-size 8 --epochs 20
```

## 📊 File Structure

```
lambda-labs-setup/
├── contourpose_trainer.py          # Main unified script
├── lambda_api_key.txt              # Your API key (create this)
├── contourpose-key                 # SSH key for Lambda Labs
├── instance.json                   # Current instance info (auto-generated)
├── setup_lambda.sh                 # Environment setup script
└── README.md                       # This file

Generated during training:
├── training_obj1.log               # Training logs (on remote)
└── ../model/obj1/                  # Downloaded models (local)
    ├── 10.pkl                      # Epoch checkpoints
    ├── 20.pkl
    ├── best.pkl                    # Best performing model
    └── latest.pkl                  # Most recent model
```

## 🔍 Monitoring and Logs

### Real-time Training Monitoring
```bash
# Watch training progress live
python3 contourpose_trainer.py monitor

# Check current status
python3 contourpose_trainer.py status
```

### What You'll See
```
📊 **CURRENT STATUS**
  • Instance ID: abc123...
  • IP Address: 150.136.208.28
  • Status: active
  • Runtime: 0.5 hours
  • Estimated cost: $0.65
  • Training: Running
  • Local models: 3 downloaded
```

### Training Progress
```
🎓 Training epoch 1...
  Batch 0050: Loss=0.543210 (Heatmap=0.481234, Contour=0.061976)
  Batch 0100: Loss=0.432109 (Heatmap=0.387654, Contour=0.044455)
✅ Epoch 1 completed in 224.1s - Avg Loss: 0.456789
💾 Saved model: 1.pkl
📥 Downloaded 1.pkl (15.2 MB)
```

## 💰 Cost Management

### Real-time Cost Tracking
The system tracks costs automatically:
- **A100 40GB**: $1.29/hour
- **10 epochs**: ~$0.81 (37.6 minutes)
- **Model sync overhead**: ~$0.01/hour

### Cost Examples
```bash
# Short test (3 epochs): ~$0.25
python3 contourpose_trainer.py launch --epochs 3

# Full training (150 epochs): ~$12.15
python3 contourpose_trainer.py launch --epochs 150

# Quick experiment (1 epoch): ~$0.08
python3 contourpose_trainer.py launch --epochs 1
```

## 🎯 Model Management

### Automatic Model Downloads
- Models are downloaded every 60 seconds
- All epoch checkpoints preserved locally
- Best and latest models always available
- No data loss even if instance crashes

### Local Model Storage
```bash
# Check downloaded models
ls -la ../model/obj1/

# Model files you'll get:
# 10.pkl, 20.pkl, 30.pkl... (epoch checkpoints)
# best.pkl (lowest loss model)
# latest.pkl (most recent model)
```

### Model Evaluation
```bash
# After training, evaluate performance
cd ..
python main.py --eval --class_type obj1 --used_epoch best
```

## 🔧 Advanced Usage

### Multiple Object Training
```bash
# Train different objects in sequence
python3 contourpose_trainer.py launch --class-type obj1 --epochs 10
python3 contourpose_trainer.py terminate
python3 contourpose_trainer.py launch --class-type obj2 --epochs 10
```

### Custom Sync Intervals
```bash
# Fast sync every 30 seconds (for debugging)
python3 contourpose_trainer.py launch --sync-interval 30

# Slow sync every 5 minutes (for long training)
python3 contourpose_trainer.py launch --sync-interval 300
```

### Background Training
```bash
# Launch without monitoring (runs in background)
python3 contourpose_trainer.py launch --class-type obj1 --epochs 50

# Later, check status and monitor
python3 contourpose_trainer.py status
python3 contourpose_trainer.py monitor
```

## 🛠️ Troubleshooting

### Common Issues

**1. API Key Issues**
```bash
# Error: API key file not found
echo "your_actual_api_key" > lambda_api_key.txt
```

**2. SSH Connection Failed**
```bash
# Check SSH key permissions
chmod 600 contourpose-key

# Test connection manually
ssh -i contourpose-key ubuntu@INSTANCE_IP
```

**3. Training Not Starting**
```bash
# Check instance status
python3 contourpose_trainer.py status

# SSH to instance and check
ssh -i contourpose-key ubuntu@INSTANCE_IP 'screen -list'
```

**4. Models Not Downloading**
```bash
# Manual sync
python3 contourpose_trainer.py sync

# Check remote models
ssh -i contourpose-key ubuntu@INSTANCE_IP 'ls -la contourpose-project/model/obj1/'
```

### Emergency Recovery
If you lose connection but training continues:
```bash
# Check Lambda Labs dashboard for instance IP
# Update instance.json manually if needed
echo '{"id":"your_instance_id","ip":"new_ip","status":"active"}' > instance.json

# Resume monitoring and sync
python3 contourpose_trainer.py status
python3 contourpose_trainer.py sync
```

### Performance Issues
```bash
# Check GPU utilization
ssh -i contourpose-key ubuntu@INSTANCE_IP 'nvidia-smi'

# Check training logs for errors
python3 contourpose_trainer.py monitor
```

## 📈 Performance Optimization

### Tested Optimal Settings
Based on our A100 performance testing:
- **batch_size=16**: Best balance of speed and memory usage
- **num_workers=8**: Optimal parallel data loading
- **96% GPU utilization**: Maximum efficiency achieved

### Batch Size Guidelines
```bash
# For experimentation (faster startup)
--batch-size 8

# For production (optimal performance)  
--batch-size 16

# For very large models (if OOM errors)
--batch-size 4
```

### Training Duration Estimates
```bash
# With optimized settings (batch_size=16):
# 1 epoch:   ~3.8 minutes  (~$0.08)
# 10 epochs: ~38 minutes   (~$0.81)
# 50 epochs: ~3.1 hours    (~$4.05)
# 150 epochs: ~9.4 hours   (~$12.15)
```

## 🔒 Security Notes

- SSH keys are used for secure authentication
- API keys are stored locally only
- No sensitive data transmitted in plain text
- Instance access is restricted to your SSH key

## 📞 Support

### Self-Help
1. Check this README for common solutions
2. Review error messages carefully
3. Test individual components (SSH, API access)
4. Verify files exist (API key, SSH key)

### Debugging Steps
```bash
# 1. Verify setup
ls -la lambda_api_key.txt contourpose-key

# 2. Test API access
curl -H "Authorization: Bearer $(cat lambda_api_key.txt)" \
     https://cloud.lambdalabs.com/api/v1/instance-types

# 3. Check for running instances
python3 contourpose_trainer.py status

# 4. Manual cleanup if needed
python3 contourpose_trainer.py terminate
```

## 📋 Migration from Old Scripts

If you were using the previous separate scripts, the new unified approach provides:

### Old → New Command Mapping
```bash
# Old way (multiple scripts)
./model_sync_daemon.sh start --lambda-ip IP
./quick_start_with_sync.sh --class-type obj1

# New way (single script)
python3 contourpose_trainer.py launch --class-type obj1

# Old monitoring
ssh -i key ubuntu@IP 'tail -f training.log'

# New monitoring  
python3 contourpose_trainer.py monitor
```

### Advantages of New Approach
- ✅ Single script handles everything
- ✅ Better error handling and recovery
- ✅ Integrated cost tracking
- ✅ Automatic cleanup
- ✅ Simpler command interface
- ✅ Built-in status monitoring

---

## 🎉 Ready to Train!

You now have a complete, optimized training solution for ContourPose on Lambda Labs. The system will:

1. **Launch** A100 instances automatically
2. **Setup** optimized training environment  
3. **Train** with maximum efficiency (4.9x speedup)
4. **Sync** models continuously (never lose progress)
5. **Monitor** training in real-time
6. **Track** costs automatically
7. **Cleanup** resources properly

Get started with just one command:
```bash
python3 contourpose_trainer.py launch --class-type obj1 --epochs 10 --monitor
```

Happy training! 🚀