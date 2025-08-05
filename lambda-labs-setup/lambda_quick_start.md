# 🚀 Lambda Labs Quick Start for ContourPose

## Step-by-Step Setup (5 minutes)

### 1. Launch Lambda Labs Instance
1. Go to [cloud.lambdalabs.com](https://cloud.lambdalabs.com)
2. Click **"Launch instance"**
3. **Select GPU**: RTX 4090 (24GB) - **$0.40/hour** ⭐
4. **Environment**: PyTorch
5. **Storage**: 100GB+
6. **SSH Key**: Upload your public key
7. Click **"Launch"**

### 2. Connect via SSH
```bash
# Use the IP provided in Lambda Labs console
ssh ubuntu@<your-instance-ip>

# Example:
ssh ubuntu@150.136.X.X
```

### 3. Run Setup Script
```bash
# Download and run our setup script
curl -fsSL https://raw.githubusercontent.com/yourusername/ContourPose/main/lambda-labs-setup/setup_lambda.sh | bash

# Or manually:
wget https://raw.githubusercontent.com/yourusername/ContourPose/main/lambda-labs-setup/setup_lambda.sh
chmod +x setup_lambda.sh
./setup_lambda.sh
```

### 4. Clone ContourPose
```bash
cd ~/contourpose-project
git clone https://github.com/yourusername/ContourPose.git
cd ContourPose

# Copy optimized training script
cp ../main_lambda.py .
```

### 5. Start Training
```bash
# Test with small run first
python main_lambda.py --train --class_type obj1 --epochs 2 --batch_size 4

# Full training run
python main_lambda.py --train --class_type obj1 --epochs 150 --batch_size 8 --auto_shutdown 8
```

## 🎯 GPU Recommendations

| GPU | VRAM | Price/Hour | Best For | Batch Size |
|-----|------|------------|----------|------------|
| **RTX 4090** ⭐ | 24GB | $0.40 | **Perfect balance** | 8-16 |
| RTX 3090 | 24GB | $0.30 | **Budget option** | 8-12 |
| A100 40GB | 40GB | $1.10 | **Fast training** | 16-32 |

## 💰 Cost Estimates

### RTX 4090 ($0.40/hour)
- **Single object**: 3-6 hours → $1.20-2.40
- **All 10 objects**: 30-60 hours → $12-24 total
- **Per epoch**: ~$0.016 (2.4 minutes average)

### Comparison with Other Clouds
- **Lambda Labs**: $12-24 total
- **GCP**: $50-100 total  
- **AWS**: $60-120 total
- **75% cost savings with Lambda Labs!** 🎉

## 🔧 Connect with Cursor

### Option 1: Direct SSH
```bash
# In Cursor: Cmd+Shift+P → "Remote-SSH: Connect to Host"
# Add host: ubuntu@<your-lambda-ip>
```

### Option 2: SSH Config
```bash
# Add to ~/.ssh/config on your local machine:
Host lambda-contourpose
    HostName <your-lambda-ip>
    User ubuntu
    IdentityFile ~/.ssh/your_key

# Then in Cursor: Connect to "lambda-contourpose"
```

## 📊 Monitoring Training

### TensorBoard
```bash
# Start TensorBoard
tensorboard --logdir logs --host 0.0.0.0 --port 6006

# Access in browser: http://<lambda-ip>:6006
```

### GPU Monitoring
```bash
# Real-time GPU usage
watch -n 1 nvidia-smi

# Our custom GPU monitor
python gpu_monitor.py

# Training progress
python training_status.py
```

### Cost Tracking
```bash
# Calculate training costs
python cost_calculator.py

# Check instance uptime
uptime
```

## 🔄 Training Multiple Objects

### Sequential Training
```bash
# Train each object one by one
for obj in obj1 obj2 obj3 obj7 obj13 obj16 obj18 obj21 obj32; do
    echo "Training $obj..."
    python main_lambda.py --train --class_type $obj --epochs 150 --batch_size 8
done
```

### Background Training
```bash
# Use screen/tmux for background training
screen -S contourpose-training

# Inside screen:
python main_lambda.py --train --class_type obj1 --epochs 150 --batch_size 8

# Detach: Ctrl+A, D
# Reattach: screen -r contourpose-training
```

## ⏰ Auto-Shutdown Features

### Built-in Auto-Shutdown
```bash
# Training script with 8-hour auto-shutdown
python main_lambda.py --train --class_type obj1 --auto_shutdown 8

# Manual shutdown timers
shutdown-in-1h    # Shutdown in 1 hour
shutdown-in-2h    # Shutdown in 2 hours
cancel-shutdown   # Cancel scheduled shutdown
```

### Smart Shutdown (After Training Complete)
```bash
# Add to end of training script
echo "sudo shutdown -h now" | at now + 5 minutes
```

## 🛠️ Troubleshooting

### Common Issues

**CUDA Out of Memory**
```bash
# Reduce batch size
python main_lambda.py --train --class_type obj1 --batch_size 4

# Monitor memory usage
nvidia-smi -l 1
```

**Instance Not Available**
- Try different regions (US-East, US-West, Europe)
- Try different GPU types (RTX 3090 vs 4090)
- Check Lambda Labs status page

**Slow Training**
```bash
# Check GPU utilization
nvidia-smi

# Increase batch size if memory allows
python main_lambda.py --train --class_type obj1 --batch_size 12

# Use more data workers
python main_lambda.py --train --class_type obj1 --num_workers 12
```

**Connection Lost**
```bash
# Use screen/tmux for persistent sessions
screen -S training
python main_lambda.py --train --class_type obj1

# Detach and close connection safely
# Training continues in background
```

## 📦 Data Management

### Upload Dataset
```bash
# From local machine
scp -r /path/to/your/dataset ubuntu@<lambda-ip>:~/contourpose-project/ContourPose/data/

# Or use rsync for better performance
rsync -avz /path/to/dataset/ ubuntu@<lambda-ip>:~/contourpose-project/ContourPose/data/
```

### Download Trained Models
```bash
# Download all models
scp -r ubuntu@<lambda-ip>:~/contourpose-project/ContourPose/model/ ./models/

# Download specific object model
scp -r ubuntu@<lambda-ip>:~/contourpose-project/ContourPose/model/obj1/ ./models/obj1/
```

### Backup to Cloud Storage
```bash
# Install cloud CLI tools
pip install awscli   # for AWS S3
pip install gsutil   # for Google Cloud Storage

# Backup models to S3
aws s3 sync model/ s3://your-bucket/contourpose-models/

# Backup to Google Cloud
gsutil -m cp -r model/ gs://your-bucket/contourpose-models/
```

## 🎯 Best Practices

### Cost Optimization
1. **Always shutdown** when not training
2. **Use auto-shutdown** for unattended training
3. **Monitor costs** with our calculator script
4. **Use screen/tmux** to avoid connection issues
5. **Train multiple objects** in one session

### Performance Optimization
1. **Use RTX 4090** for best price/performance
2. **Batch size 8-12** for optimal GPU utilization
3. **Save checkpoints** every 10 epochs
4. **Use TensorBoard** for monitoring
5. **Upload data once** and reuse for all objects

### Reliability
1. **Use persistent sessions** (screen/tmux)
2. **Save progress frequently**
3. **Test with small runs** before full training
4. **Backup important models** to cloud storage
5. **Have fallback plans** for instance unavailability

## 🎉 Complete Workflow

```bash
# 1. Launch RTX 4090 instance on Lambda Labs
# 2. Connect and setup
ssh ubuntu@<lambda-ip>
./setup_lambda.sh

# 3. Clone and prepare
git clone https://github.com/yourusername/ContourPose.git
cd ContourPose
cp ../main_lambda.py .

# 4. Upload your dataset
# (use scp from local machine)

# 5. Start training with monitoring
screen -S training
python main_lambda.py --train --class_type obj1 --epochs 150 --batch_size 8 --auto_shutdown 8

# 6. Monitor progress
# Detach: Ctrl+A, D
# Check progress: python training_status.py
# Check costs: python cost_calculator.py

# 7. Download results and shutdown
scp -r model/ local-machine:./models/
sudo shutdown -h now
```

**Result**: Professional-grade 6D pose estimation training for **75% less cost** than major cloud providers! 🚀