#!/bin/bash
# Upload ContourPose to Lambda Labs and set up environment

IP="129.158.238.46"
echo "🚀 Setting up ContourPose on Lambda Labs instance: $IP"

# First, test SSH connection
echo "🔐 Testing SSH connection..."
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@$IP "echo 'SSH connection successful!'"

if [ $? -ne 0 ]; then
    echo "❌ SSH connection failed. Instance might still be starting up."
    echo "   Try again in a few minutes with: ssh ubuntu@$IP"
    exit 1
fi

# Set up the environment on remote instance
echo "🔧 Setting up environment..."
ssh ubuntu@$IP << 'EOF'
set -e

# Update system
sudo apt-get update -y
sudo apt-get install -y git curl wget unzip python3-pip python3-venv htop rsync

# Create project directory
mkdir -p ~/contourpose-project
cd ~/contourpose-project

# Create virtual environment
python3 -m venv contourpose-env
source contourpose-env/bin/activate

# Install PyTorch with CUDA support
echo "📦 Installing PyTorch with CUDA..."
pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install opencv-python numpy scipy matplotlib PyYAML Pillow tqdm

# Test GPU
echo "🔧 Testing GPU..."
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo "✅ Environment setup complete!"
EOF

echo "📦 Uploading ContourPose code..."
rsync -avz --progress \
  --exclude='data/' \
  --exclude='model/' \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='lambda-labs-setup/' \
  ../../../ContourPose/ \
  ubuntu@$IP:~/contourpose-project/ContourPose/

echo "📊 Uploading training data..."
rsync -avz --progress \
  ../../../ContourPose/data/train/ \
  ubuntu@$IP:~/contourpose-project/ContourPose/data/train/

echo "🎯 Uploading keypoints..."
rsync -avz --progress \
  ../../../ContourPose/keypoints/ \
  ubuntu@$IP:~/contourpose-project/ContourPose/keypoints/

# Verify upload
echo "✅ Verifying upload..."
ssh ubuntu@$IP << 'EOF'
cd ~/contourpose-project/ContourPose
echo "📁 Directory structure:"
ls -la
echo ""
echo "📊 Training data:"
ls -la data/train/ 2>/dev/null || echo "   (No data directory yet)"
echo ""
echo "🎯 Keypoints:"
ls -la keypoints/ 2>/dev/null || echo "   (No keypoints directory yet)"
EOF

echo ""
echo "🎉 Upload complete!"
echo "💡 Next steps:"
echo "   1. SSH to instance: ssh ubuntu@$IP"
echo "   2. Activate environment: source ~/contourpose-project/contourpose-env/bin/activate"
echo "   3. Go to project: cd ~/contourpose-project/ContourPose"
echo "   4. Start training: python3 main.py --class_type obj1 --epochs 150 --batch_size 8 --lr 0.001"
echo ""
echo "💰 Instance cost: $1.29/hour"
echo "⚠️  Remember to terminate when done!"