#!/bin/bash
# Start ContourPose training on Lambda Labs

IP="129.158.238.46"
echo "🚀 Starting ContourPose training on $IP..."

ssh ubuntu@$IP << 'EOF'
cd ~/contourpose-project/ContourPose
source ../contourpose-env/bin/activate

echo "🔧 Final GPU test..."
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

echo "🎯 Starting training for obj1 (150 epochs)..."
echo "💰 Cost estimate: ~$193.50 for 150 hours at $1.29/hour"
echo ""

# Create screen session for training
screen -dmS contourpose-training bash -c '
cd ~/contourpose-project/ContourPose
source ../contourpose-env/bin/activate
python3 main.py --class_type obj1 --epochs 150 --batch_size 8 --lr 0.001
echo "Training completed! Check the model/ directory for results."
read -p "Press Enter to close..."
'

echo "✅ Training started in screen session 'contourpose-training'"
echo "📊 Monitor progress with: screen -r contourpose-training"
echo "🔄 Detach with: Ctrl+A then D"
echo "📈 Check GPU usage: nvidia-smi"
EOF

echo ""
echo "🎉 Training launched successfully!"
echo "💡 Useful commands:"
echo "   - Connect: ssh ubuntu@$IP"
echo "   - Monitor training: ssh ubuntu@$IP -t 'screen -r contourpose-training'"
echo "   - Check GPU: ssh ubuntu@$IP -t 'nvidia-smi'"
echo "   - Download results: rsync -avz ubuntu@$IP:~/contourpose-project/ContourPose/model/ ./results/"
echo ""
echo "⏱️  Estimated training time: ~150 hours"
echo "💰 Estimated cost: ~$193.50"
echo "⚠️  Remember to terminate instance when training is complete!"