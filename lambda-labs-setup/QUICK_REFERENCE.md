# ContourPose Lambda Labs Quick Reference

## 🚀 **1-Minute Setup**

```bash
# Get your API key from https://cloud.lambdalabs.com/api-keys
echo "secret_your_api_key_here" > lambda_api_key.txt

# Launch everything (10 epochs, ~$0.90)
python complete_setup.py launch 10 obj1

# Monitor progress
python complete_setup.py monitor

# When done, terminate
python complete_setup.py terminate
```

## 💰 **Costs (Tested A100 40GB)**

| Epochs | Time | Cost | Use Case |
|--------|------|------|----------|
| 10 | 42 min | $0.90 | Quick test/validation |
| 25 | 105 min | $2.26 | Decent results |
| 50 | 210 min | $4.52 | Good results |
| 150 | 10.5 hr | $13.55 | Full training (paper) |

## ⚡ **Performance Specs**

- **GPU**: A100 40GB (90% utilization)
- **Speed**: 4.2 minutes/epoch
- **Memory**: 2.2GB used / 40GB available
- **Batch Size**: 8 (optimal)
- **Workers**: 4 (critical optimization)

## 📊 **Expected Training Progress**

```
Epoch 1: loss 1.01 → 0.17 (good convergence)
GPU: 90% utilization, 299W power
Iteration: ~20 seconds each
```

## 🔧 **Key Files Modified**

- `main.py`: Added MPS support, fixed data paths, num_workers=4
- `dataset/Dataset.py`: Random background fallback
- All Lambda Labs scripts: Complete automation

## 🚨 **Critical Settings**

```python
# In main.py DataLoader:
num_workers=4  # 4x speed boost!
batch_size=8   # Optimal memory usage
device='cuda'  # A100 utilization
```

## 📂 **Project Structure on Remote**

```
~/contourpose-project/
├── ContourPose/           # Main code
│   ├── main.py           # Training script
│   ├── data/            # Training data
│   │   └── train/obj1/  # Object data
│   ├── keypoints/       # 3D keypoints
│   └── *.log           # Training logs
└── contourpose-env/     # Python environment
```

## 🐛 **Common Issues & Fixes**

| Issue | Solution |
|-------|----------|
| Slow training (16% GPU) | Set `num_workers=4` |
| NumPy errors | `pip install numpy==1.26.4` |
| Missing sklearn | `pip install scikit-learn` |
| Data path errors | Use absolute paths |
| No background images | Random fallback implemented |

## 📱 **Monitoring Commands**

```bash
# Check training progress
ssh ubuntu@IP 'tail -f ~/contourpose-project/ContourPose/*.log'

# Check GPU usage
ssh ubuntu@IP 'nvidia-smi'

# Check if training is running
ssh ubuntu@IP 'ps aux | grep python | grep main.py'

# Access screen session
ssh ubuntu@IP 'screen -r contourpose-training'
```

## 💾 **Download Results**

```bash
# Download trained models
scp -r ubuntu@IP:~/contourpose-project/ContourPose/model/ ./models/

# Download training logs
scp ubuntu@IP:~/contourpose-project/ContourPose/*.log ./logs/
```

## ⏹️ **Emergency Stop**

```bash
# Kill training and terminate instance
ssh ubuntu@IP 'pkill -f main.py'
python complete_setup.py terminate
```

## 🎯 **Success Metrics**

- ✅ GPU utilization >85%
- ✅ Loss decreasing: 1.01 → 0.17+ 
- ✅ ~20 seconds per iteration
- ✅ Memory usage ~2GB
- ✅ No Python errors in log

---

**Total setup time**: ~5 minutes  
**Training cost**: $0.90 (10 epochs)  
**Performance**: Better than paper's 2x RTX 3090!