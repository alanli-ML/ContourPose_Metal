#!/usr/bin/env python3
"""
ContourPose Trainer - Unified Lambda Labs Training with Auto Model Sync
Consolidates all training and model sync functionality into a single script.
"""

import os
import sys
import time
import json
import subprocess
import argparse
import threading
from datetime import datetime
import signal

class ContourPoseTrainer:
    def __init__(self, args):
        self.args = args
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.script_dir)
        
        # Instance state
        self.instance_info = None
        self.sync_thread = None
        self.sync_running = False
        
        # Paths
        self.api_key_file = os.path.join(self.script_dir, args.api_key_file)
        self.ssh_key_path = os.path.join(self.script_dir, args.ssh_key)
        self.instance_file = os.path.join(self.script_dir, 'instance.json')
        
        # Ensure required files exist
        self.validate_setup()
        
    def validate_setup(self):
        """Validate required files and dependencies"""
        if not os.path.exists(self.api_key_file):
            print(f"❌ API key file not found: {self.api_key_file}")
            print(f"Create it with: echo 'your_api_key' > {self.api_key_file}")
            sys.exit(1)
            
        if not os.path.exists(self.ssh_key_path):
            print(f"❌ SSH key not found: {self.ssh_key_path}")
            sys.exit(1)
            
        # Check dependencies
        for cmd in ['curl', 'rsync', 'ssh']:
            if not subprocess.run(['which', cmd], capture_output=True).returncode == 0:
                print(f"❌ Required command not found: {cmd}")
                sys.exit(1)
                
    def log(self, message, level="INFO"):
        """Logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[0;34m",    # Blue
            "SUCCESS": "\033[0;32m", # Green  
            "WARNING": "\033[1;33m", # Yellow
            "ERROR": "\033[0;31m",   # Red
            "RESET": "\033[0m"       # Reset
        }
        color = colors.get(level, colors["INFO"])
        print(f"{color}{timestamp} - {message}{colors['RESET']}")
        
    def run_command(self, cmd, capture=True, timeout=30):
        """Run command with error handling"""
        try:
            result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
            
    def lambda_api_request(self, endpoint, method="GET", data=None):
        """Make Lambda Labs API request"""
        with open(self.api_key_file, 'r') as f:
            api_key = f.read().strip()
            
        cmd = ['curl', '-s', '-X', method, '-H', f'Authorization: Bearer {api_key}']
        
        if data:
            cmd.extend(['-H', 'Content-Type: application/json', '-d', json.dumps(data)])
            
        cmd.append(f'https://cloud.lambdalabs.com/api/v1/{endpoint}')
        
        success, stdout, stderr = self.run_command(cmd, timeout=60)
        if not success:
            return None, stderr
            
        try:
            return json.loads(stdout), None
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {str(e)}"
            
    def find_a100_instance_type(self):
        """Find A100 instance type"""
        self.log("🔍 Finding A100 instance type...")
        data, error = self.lambda_api_request('instance-types')
        
        if error:
            self.log(f"❌ Failed to get instance types: {error}", "ERROR")
            return None
            
        for instance_type, details in data['data'].items():
            if 'A100' in details['description']:
                self.log(f"✅ Found A100 instance: {details['description']}")
                return instance_type
                
        self.log("❌ A100 instance type not found", "ERROR")
        return None
        
    def launch_instance(self):
        """Launch Lambda Labs instance"""
        instance_type = self.find_a100_instance_type()
        if not instance_type:
            return False
            
        self.log("🚀 Launching Lambda Labs instance...")
        
        launch_data = {
            'region_name': 'us-east-1',
            'instance_type_name': instance_type,
            'ssh_key_names': [self.args.ssh_key.replace('.pem', '').replace('.key', '')],
            'quantity': 1,
            'name': f'contourpose-{int(time.time())}'
        }
        
        data, error = self.lambda_api_request('instance-operations/launch', 'POST', launch_data)
        
        if error or 'data' not in data or 'instance_ids' not in data['data']:
            self.log(f"❌ Failed to launch instance: {error or data}", "ERROR")
            return False
            
        instance_id = data['data']['instance_ids'][0]
        self.log(f"✅ Instance launched: {instance_id}")
        
        # Wait for instance to be ready
        return self.wait_for_instance(instance_id)
        
    def wait_for_instance(self, instance_id, timeout=600):
        """Wait for instance to be ready"""
        self.log("⏳ Waiting for instance to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            data, error = self.lambda_api_request('instances')
            
            if not error and 'data' in data:
                for instance in data['data']:
                    if instance['id'] == instance_id:
                        if instance['status'] == 'active' and 'ip' in instance:
                            self.instance_info = {
                                'id': instance_id,
                                'ip': instance['ip'],
                                'status': 'active',
                                'start_time': time.time()
                            }
                            
                            # Save instance info
                            with open(self.instance_file, 'w') as f:
                                json.dump(self.instance_info, f, indent=2)
                                
                            self.log(f"✅ Instance ready: {instance['ip']}")
                            return True
                            
            time.sleep(10)
            
        self.log("❌ Instance failed to become ready", "ERROR")
        return False
        
    def ssh_command(self, command, timeout=60):
        """Execute SSH command on instance"""
        if not self.instance_info:
            return False, "", "No instance available"
            
        ssh_cmd = [
            'ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'PasswordAuthentication=no',
            '-i', self.ssh_key_path, f"ubuntu@{self.instance_info['ip']}", command
        ]
        
        return self.run_command(ssh_cmd, timeout=timeout)
        
    def upload_project(self):
        """Upload ContourPose project to instance"""
        if not self.instance_info:
            return False
            
        self.log("📤 Uploading ContourPose project...")
        
        rsync_cmd = [
            'rsync', '-avz', '--progress',
            '-e', f'ssh -o StrictHostKeyChecking=no -i {self.ssh_key_path}',
            f'{self.project_root}/',
            f"ubuntu@{self.instance_info['ip']}:~/contourpose-project/",
            '--exclude=.git', '--exclude=*.pyc', '--exclude=__pycache__',
            '--exclude=.DS_Store', '--exclude=instance.json'
        ]
        
        success, stdout, stderr = self.run_command(rsync_cmd, timeout=300)
        
        if success:
            self.log("✅ Project uploaded successfully")
            return True
        else:
            self.log(f"❌ Upload failed: {stderr}", "ERROR")
            return False
            
    def setup_environment(self):
        """Setup environment on remote instance"""
        if not self.instance_info:
            return False
            
        self.log("🔧 Setting up environment...")
        
        setup_commands = [
            'cd contourpose-project/lambda-labs-setup',
            'bash setup_lambda.sh'
        ]
        
        for cmd in setup_commands:
            success, stdout, stderr = self.ssh_command(cmd, timeout=600)
            if not success:
                self.log(f"❌ Setup command failed: {cmd}", "ERROR")
                self.log(f"Error: {stderr}", "ERROR")
                return False
                
        self.log("✅ Environment setup complete")
        return True
        
    def start_training(self):
        """Start training on remote instance"""
        if not self.instance_info:
            return False
            
        self.log(f"🎓 Starting training for {self.args.class_type}...")
        
        training_cmd = (
            f'cd contourpose-project && '
            f'screen -dmS training bash -c "'
            f'echo \"🚀 Training started: $(date)\" > training_{self.args.class_type}.log && '
            f'python main.py --train --class_type {self.args.class_type} '
            f'--epochs {self.args.epochs} --batch_size {self.args.batch_size} '
            f'2>&1 | tee -a training_{self.args.class_type}.log && '
            f'echo \"🏁 Training completed: $(date)\" >> training_{self.args.class_type}.log"'
        )
        
        success, stdout, stderr = self.ssh_command(training_cmd)
        
        if success:
            self.log("✅ Training started in background")
            return True
        else:
            self.log(f"❌ Failed to start training: {stderr}", "ERROR")
            return False
            
    def start_model_sync(self):
        """Start model synchronization thread"""
        if self.sync_running:
            return
            
        self.log("🔄 Starting model sync...")
        self.sync_running = True
        self.sync_thread = threading.Thread(target=self.model_sync_worker, daemon=True)
        self.sync_thread.start()
        
    def model_sync_worker(self):
        """Model sync worker thread"""
        local_model_dir = os.path.join(self.project_root, 'model', self.args.class_type)
        os.makedirs(local_model_dir, exist_ok=True)
        
        sync_count = 0
        
        while self.sync_running and self.instance_info:
            try:
                # Check for new models
                remote_models = self.get_remote_models()
                local_models = self.get_local_models(local_model_dir)
                
                new_models = [m for m in remote_models if m not in local_models]
                
                if new_models:
                    self.log(f"📥 Found {len(new_models)} new models: {new_models}")
                    
                    for model in new_models:
                        if self.download_model(model, local_model_dir):
                            sync_count += 1
                            self.log(f"✅ Downloaded {model}.pkl", "SUCCESS")
                        else:
                            self.log(f"❌ Failed to download {model}.pkl", "WARNING")
                            
                elif sync_count > 0:  # Only log if we've synced before
                    self.log(f"✅ All models up to date ({len(local_models)} models)")
                    
                time.sleep(self.args.sync_interval)
                
            except Exception as e:
                self.log(f"⚠️ Sync error: {str(e)}", "WARNING")
                time.sleep(30)  # Wait longer on error
                
    def get_remote_models(self):
        """Get list of models on remote instance"""
        if not self.instance_info:
            return []
            
        cmd = f'ls contourpose-project/model/{self.args.class_type}/*.pkl 2>/dev/null | grep -E "[0-9]+\\.pkl$|best\\.pkl$|latest\\.pkl$" | xargs -n1 basename | sed "s/.pkl$//" || echo ""'
        success, stdout, stderr = self.ssh_command(cmd)
        
        if success and stdout.strip():
            models = []
            for line in stdout.strip().split('\n'):
                if line and line != '':
                    models.append(line)
            return models
        return []
        
    def get_local_models(self, local_dir):
        """Get list of local models"""
        if not os.path.exists(local_dir):
            return []
            
        models = []
        for file in os.listdir(local_dir):
            if file.endswith('.pkl'):
                models.append(file.replace('.pkl', ''))
        return models
        
    def download_model(self, model_name, local_dir):
        """Download a specific model"""
        if not self.instance_info:
            return False
            
        remote_file = f"ubuntu@{self.instance_info['ip']}:contourpose-project/model/{self.args.class_type}/{model_name}.pkl"
        local_file = os.path.join(local_dir, f"{model_name}.pkl")
        
        rsync_cmd = [
            'rsync', '-avz',
            '-e', f'ssh -o StrictHostKeyChecking=no -i {self.ssh_key_path}',
            remote_file, local_file
        ]
        
        success, stdout, stderr = self.run_command(rsync_cmd, timeout=120)
        
        if success and os.path.exists(local_file) and os.path.getsize(local_file) > 0:
            return True
        return False
        
    def monitor_training(self):
        """Monitor training progress"""
        if not self.instance_info:
            return
            
        self.log("📊 Monitoring training progress...")
        self.log("Press Ctrl+C to stop monitoring (training will continue)")
        
        try:
            cmd = f'tail -f contourpose-project/training_{self.args.class_type}.log'
            process = subprocess.Popen([
                'ssh', '-o', 'StrictHostKeyChecking=no', '-i', self.ssh_key_path,
                f"ubuntu@{self.instance_info['ip']}", cmd
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line.rstrip())
                    
        except KeyboardInterrupt:
            self.log("🛑 Monitoring stopped")
            process.terminate()
            
    def terminate_instance(self):
        """Terminate the Lambda Labs instance"""
        if not self.instance_info:
            self.log("⚠️ No instance to terminate", "WARNING")
            return True
            
        self.log("🔴 Terminating instance...")
        
        terminate_data = {"instance_ids": [self.instance_info['id']]}
        data, error = self.lambda_api_request('instance-operations/terminate', 'POST', terminate_data)
        
        if error:
            self.log(f"❌ Failed to terminate instance: {error}", "ERROR")
            return False
            
        self.log("✅ Instance terminated")
        
        # Clean up
        if os.path.exists(self.instance_file):
            os.remove(self.instance_file)
        self.instance_info = None
        
        return True
        
    def show_status(self):
        """Show current status"""
        if os.path.exists(self.instance_file):
            with open(self.instance_file, 'r') as f:
                self.instance_info = json.load(f)
                
        if self.instance_info:
            runtime = time.time() - self.instance_info.get('start_time', time.time())
            cost = runtime / 3600 * 1.29
            
            self.log("📊 **CURRENT STATUS**")
            print(f"  • Instance ID: {self.instance_info['id']}")
            print(f"  • IP Address: {self.instance_info['ip']}")
            print(f"  • Status: {self.instance_info['status']}")
            print(f"  • Runtime: {runtime/3600:.1f} hours")
            print(f"  • Estimated cost: ${cost:.2f}")
            
            # Check if training is running
            success, stdout, stderr = self.ssh_command('screen -list | grep training || echo "No training session"')
            if success:
                print(f"  • Training: {'Running' if 'training' in stdout else 'Not running'}")
                
            # Check local models
            local_dir = os.path.join(self.project_root, 'model', self.args.class_type)
            if os.path.exists(local_dir):
                models = self.get_local_models(local_dir)
                print(f"  • Local models: {len(models)} downloaded")
        else:
            self.log("⚠️ No active instance", "WARNING")
            
    def cleanup(self):
        """Cleanup resources"""
        self.log("🧹 Cleaning up...")
        self.sync_running = False
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
            
    def run(self):
        """Main execution flow"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
        
        try:
            if self.args.command == 'launch':
                if not self.launch_instance():
                    return 1
                if not self.upload_project():
                    return 1
                if not self.setup_environment():
                    return 1
                if not self.start_training():
                    return 1
                    
                self.start_model_sync()
                self.log("🎉 Training setup complete!")
                
                if self.args.monitor:
                    self.monitor_training()
                else:
                    self.log("💡 Use 'python contourpose_trainer.py monitor' to watch training")
                    
            elif self.args.command == 'status':
                self.show_status()
                
            elif self.args.command == 'monitor':
                if os.path.exists(self.instance_file):
                    with open(self.instance_file, 'r') as f:
                        self.instance_info = json.load(f)
                    self.monitor_training()
                else:
                    self.log("❌ No active instance found", "ERROR")
                    return 1
                    
            elif self.args.command == 'sync':
                if os.path.exists(self.instance_file):
                    with open(self.instance_file, 'r') as f:
                        self.instance_info = json.load(f)
                    self.start_model_sync()
                    self.log("🔄 Model sync started. Press Ctrl+C to stop.")
                    try:
                        while self.sync_running:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        pass
                else:
                    self.log("❌ No active instance found", "ERROR")
                    return 1
                    
            elif self.args.command == 'terminate':
                if os.path.exists(self.instance_file):
                    with open(self.instance_file, 'r') as f:
                        self.instance_info = json.load(f)
                    
                # Final model sync before termination
                self.log("📥 Final model sync before termination...")
                remote_models = self.get_remote_models()
                local_dir = os.path.join(self.project_root, 'model', self.args.class_type)
                os.makedirs(local_dir, exist_ok=True)
                
                for model in remote_models:
                    self.download_model(model, local_dir)
                    
                if not self.terminate_instance():
                    return 1
                    
            return 0
            
        except KeyboardInterrupt:
            self.log("🛑 Interrupted by user")
            return 0
        except Exception as e:
            self.log(f"❌ Unexpected error: {str(e)}", "ERROR")
            return 1
        finally:
            self.cleanup()

def main():
    parser = argparse.ArgumentParser(description='ContourPose Trainer - Lambda Labs Training with Auto Model Sync')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Launch command
    launch_parser = subparsers.add_parser('launch', help='Launch instance and start training')
    launch_parser.add_argument('--class-type', default='obj1', help='Object class to train')
    launch_parser.add_argument('--epochs', type=int, default=10, help='Number of epochs')
    launch_parser.add_argument('--batch-size', type=int, default=16, help='Batch size')
    launch_parser.add_argument('--monitor', action='store_true', help='Monitor training after launch')
    
    # Other commands
    subparsers.add_parser('status', help='Show current status')
    subparsers.add_parser('monitor', help='Monitor training progress')
    subparsers.add_parser('sync', help='Start model sync daemon')
    subparsers.add_parser('terminate', help='Terminate instance')
    
    # Common options
    parser.add_argument('--api-key-file', default='lambda_api_key.txt', help='API key file')
    parser.add_argument('--ssh-key', default='contourpose-key', help='SSH key file')
    parser.add_argument('--sync-interval', type=int, default=60, help='Model sync interval in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    trainer = ContourPoseTrainer(args)
    return trainer.run()

if __name__ == '__main__':
    sys.exit(main())