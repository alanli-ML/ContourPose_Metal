import os
import torch
import numpy as np
from network import ContourPose
from dataset.Dataset import MyDataset
from torch.utils.data import DataLoader
from eval import evaluator
import argparse
import time
from torch import nn
import json
from datetime import datetime

def train(model, dataloader, optimizer, device, epoch, total_epochs):
    model.train()
    total_loss = 0.0
    heatmap_loss_total = 0.0
    contour_loss_total = 0.0
    iter = 0
    start = time.time()
    
    for data in dataloader:
        iter += 1
        # Move data to device
        img, heatmap, K, pose, gt_contour = [x.to(device) for x in data]
        
        loss = model(img, heatmap, gt_contour)
        final_loss = torch.mean(loss["heatmap_loss"]) + torch.mean(loss["contour_loss"])
        final_loss = final_loss.to(torch.float32)
        
        heatmap_loss = torch.mean(loss["heatmap_loss"]).item()
        contour_loss = torch.mean(loss["contour_loss"]).item()
        loss_item = final_loss.item()
        
        total_loss += loss_item
        heatmap_loss_total += heatmap_loss
        contour_loss_total += contour_loss

        if iter % 20 == 0:  # More frequent logging
            elapsed = time.time() - start
            eta = elapsed / iter * (len(dataloader) - iter)
            print(f'Epoch {epoch}/{total_epochs} [{iter}/{len(dataloader)}] '
                  f'Loss: {loss_item:.6f} (H: {heatmap_loss:.6f}, C: {contour_loss:.6f}) '
                  f'ETA: {eta/60:.1f}min')
        
        optimizer.zero_grad()
        final_loss.backward()
        optimizer.step()
    
    duration = time.time() - start
    avg_loss = total_loss / len(dataloader)
    avg_heatmap = heatmap_loss_total / len(dataloader)
    avg_contour = contour_loss_total / len(dataloader)
    
    print(f'Epoch {epoch} completed in {duration/60:.1f}min - '
          f'Avg Loss: {avg_loss:.6f} (H: {avg_heatmap:.6f}, C: {avg_contour:.6f})')
    
    return avg_loss, avg_heatmap, avg_contour

def load_network(net, model_dir, optimizer, resume=True, epoch=-1, strict=True):
    if not resume:
        return 0
    if not os.path.exists(model_dir):
        print(f"Model directory {model_dir} does not exist, starting from scratch")
        return 0
    
    pths = [int(pth.split(".")[0]) for pth in os.listdir(model_dir) if "pkl" in pth and pth.split(".")[0].isdigit()]
    if len(pths) == 0:
        print("No model checkpoints found, starting from scratch")
        return 0
    
    if epoch == -1:
        pth = max(pths)
    else:
        pth = epoch

    model_path = os.path.join(model_dir, "{}.pkl".format(pth))
    print(f"Loading model from: {model_path}")
    
    try:
        pretrained_model = torch.load(model_path, map_location='cpu')
        if 'net' in pretrained_model:
            net.load_state_dict(pretrained_model['net'], strict=strict)
            if 'optimizer' in pretrained_model and optimizer is not None:
                optimizer.load_state_dict(pretrained_model['optimizer'])
        else:
            net.load_state_dict(pretrained_model, strict=strict)
        print(f"Successfully loaded model from epoch {pth}")
        return pth
    except Exception as e:
        print(f"Error loading model: {e}")
        return 0

def save_training_log(log_data, log_file):
    """Save training metrics to JSON log file"""
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []
    
    logs.append(log_data)
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def adjust_learning_rate(optimizer, epoch, init_lr):
    """Sets the learning rate to the initial LR decayed by 0.5 every 20 epochs"""
    lr = init_lr * (0.5 ** (epoch // 20))
    for param_group in optimizer.param_groups:
        param_group["lr"] = lr
    return lr

@torch.no_grad()
def get_wd_params(model: nn.Module):
    """Separate parameters for weight decay"""
    all_params = tuple(model.parameters())
    wd_params = list()
    
    for m in model.modules():
        if isinstance(m, (nn.Linear, nn.Conv1d, nn.Conv2d, nn.Conv3d, 
                         nn.ConvTranspose1d, nn.ConvTranspose2d, nn.ConvTranspose3d)):
            wd_params.append(m.weight)
    
    no_wd_params = []
    for p in all_params:
        if p.dim() == 1:  # bias terms, batch norm parameters
            no_wd_params.append(p)
    
    assert len(wd_params) + len(no_wd_params) == len(all_params), "Parameter count mismatch"
    return wd_params, no_wd_params

def setup_auto_shutdown(hours=8):
    """Setup automatic shutdown after specified hours"""
    minutes = hours * 60
    os.system(f'echo "sudo shutdown -h now" | at now + {minutes} minutes')
    print(f"⏰ Auto-shutdown scheduled in {hours} hours")

def main(args):
    print("🚀 ContourPose Training on Lambda Labs")
    print("=" * 50)
    
    # Device setup
    if torch.cuda.is_available():
        device = torch.device("cuda:0")
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"🎯 GPU: {gpu_name}")
        print(f"💾 VRAM: {gpu_memory:.1f} GB")
    else:
        device = torch.device("cpu")
        print("⚠️ Using CPU (GPU not available)")

    # Setup auto-shutdown if enabled
    if args.auto_shutdown > 0:
        setup_auto_shutdown(args.auto_shutdown)

    # Create directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("model", exist_ok=True)
    
    # Setup datasets
    if args.train:
        print(f"📂 Setting up training dataset for {args.class_type}...")
        train_set = MyDataset(args.data_path, args.class_type, is_train=True)
        train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, 
                                num_workers=args.num_workers, pin_memory=True)
        print(f"📊 Training samples: {len(train_set)}")
    
    if args.eval:
        print(f"📂 Setting up evaluation dataset for {args.class_type}...")
        test_set = MyDataset(args.data_path, args.class_type, is_train=False, 
                           scene=args.scene, index=args.index)
        test_loader = DataLoader(test_set, batch_size=args.batch_size, shuffle=False, 
                               num_workers=args.num_workers, pin_memory=True)
        print(f"📊 Test samples: {len(test_set)}")

    # Load keypoints
    keypoints_file = os.path.join(os.getcwd(), "keypoints/{}.txt".format(args.class_type))
    if not os.path.exists(keypoints_file):
        print(f"❌ Keypoints file not found: {keypoints_file}")
        return
    
    corners = np.loadtxt(keypoints_file)
    print(f"🎯 Keypoints: {corners.shape[0]} for {args.class_type}")

    # Create model
    print("🏗️ Creating ContourPose model...")
    ContourNet = ContourPose(heatmap_dim=corners.shape[0])
    ContourNet = ContourNet.to(device)
    
    # Count parameters
    total_params = sum(p.numel() for p in ContourNet.parameters())
    trainable_params = sum(p.numel() for p in ContourNet.parameters() if p.requires_grad)
    print(f"📊 Model parameters: {total_params:,} total, {trainable_params:,} trainable")
    
    # Setup optimizer
    wd_params, no_wd_params = get_wd_params(ContourNet)
    optimizer = torch.optim.AdamW([
        {'params': list(no_wd_params), 'weight_decay': 0}, 
        {'params': list(wd_params), 'weight_decay': args.weight_decay}
    ], lr=args.lr)
    
    model_path = os.path.join(os.getcwd(), "model", args.class_type)
    log_file = os.path.join("logs", f"{args.class_type}_training.json")

    if args.train:
        print(f"🎓 Starting training for {args.class_type}...")
        
        # Load existing model if available
        start_epoch = load_network(ContourNet, model_path, optimizer) + 1
        print(f"📈 Starting from epoch {start_epoch}")
        
        # Create model directory
        os.makedirs(model_path, exist_ok=True)
        
        # Training loop
        best_loss = float('inf')
        training_start = time.time()
        
        for epoch in range(start_epoch, args.epochs + 1):
            print(f"\n🔄 Epoch {epoch}/{args.epochs} - {args.class_type}")
            print("-" * 40)
            
            # Adjust learning rate
            lr = adjust_learning_rate(optimizer, epoch, args.lr)
            print(f"📚 Learning rate: {lr:.6f}")
            
            # Train one epoch
            avg_loss, avg_heatmap, avg_contour = train(
                ContourNet, train_loader, optimizer, device, epoch, args.epochs
            )
            
            # Log training metrics
            log_data = {
                "epoch": epoch,
                "timestamp": datetime.now().isoformat(),
                "class_type": args.class_type,
                "avg_loss": avg_loss,
                "heatmap_loss": avg_heatmap,
                "contour_loss": avg_contour,
                "learning_rate": lr,
                "batch_size": args.batch_size
            }
            save_training_log(log_data, log_file)
            
            # Save model checkpoint
            if epoch % args.save_interval == 0 or avg_loss < best_loss:
                print(f"💾 Saving checkpoint at epoch {epoch}")
                state = {
                    'net': ContourNet.state_dict(), 
                    'optimizer': optimizer.state_dict(), 
                    'epoch': epoch,
                    'loss': avg_loss,
                    'heatmap_loss': avg_heatmap,
                    'contour_loss': avg_contour,
                    'args': vars(args)
                }
                torch.save(state, os.path.join(model_path, f'{epoch}.pkl'))
                
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    torch.save(state, os.path.join(model_path, 'best.pkl'))
                    print(f"🏆 New best model saved! Loss: {best_loss:.6f}")
            
            # Memory cleanup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        training_time = time.time() - training_start
        print(f"\n🎉 Training completed in {training_time/3600:.1f} hours!")
        print(f"💰 Approximate cost: ${training_time/3600 * 0.40:.2f} (RTX 4090)")
    
    if args.eval:
        print(f"📊 Starting evaluation for {args.class_type}...")
        ContourNet_eval = evaluator(args, ContourNet, test_loader, device)
        load_network(ContourNet, model_path, None, epoch=args.used_epoch)
        ContourNet_eval.evaluate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ContourPose Training on Lambda Labs')
    
    # Mode arguments
    parser.add_argument("--train", action='store_true', help="Enable training mode")
    parser.add_argument("--eval", action='store_true', help="Enable evaluation mode")
    
    # Data arguments
    parser.add_argument("--data_path", type=str, default=os.path.join(os.getcwd(), "data"),
                       help="Path to dataset")
    parser.add_argument("--class_type", type=str, default="obj1",
                       help="Object class to train/evaluate")
    
    # Training arguments
    parser.add_argument("--lr", type=float, default=0.001,
                       help="Learning rate")
    parser.add_argument("--batch_size", type=int, default=8,
                       help="Batch size (optimized for Lambda Labs GPUs)")
    parser.add_argument("--epochs", type=int, default=150,
                       help="Number of training epochs")
    parser.add_argument("--weight_decay", type=float, default=0.1,
                       help="Weight decay for AdamW optimizer")
    parser.add_argument("--num_workers", type=int, default=8,
                       help="Number of data loading workers")
    parser.add_argument("--save_interval", type=int, default=10,
                       help="Save model every N epochs")
    
    # Lambda Labs specific
    parser.add_argument("--auto_shutdown", type=int, default=8,
                       help="Auto-shutdown after N hours (0 to disable)")
    
    # Evaluation arguments
    parser.add_argument("--used_epoch", type=int, default=-1,
                       help="Epoch to use for evaluation (-1 for latest)")
    parser.add_argument("--scene", type=int, default=13,
                       help="Scene number for evaluation")
    parser.add_argument("--index", type=int, default=2,
                       help="Object index in scene")
    parser.add_argument("--threshold", type=int, default=5,
                       help="Threshold for evaluation metrics")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate arguments
    if not args.train and not args.eval:
        parser.error("Must specify either --train or --eval (or both)")
    
    print(f"🔧 Configuration: {vars(args)}")
    main(args)