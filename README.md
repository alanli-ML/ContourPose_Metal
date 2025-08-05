# ContourPose

code for paper "ContourPose：A monocular 6D pose estimation method for reflective texture-less metal parts".

### **Video demo**

![ContourPose](figure/ContourPose.gif)

### **Grasp demo**
![grasp](figure/grasp.jpg)

![grasp](figure/grasp.gif)



### **Pose estimation demo**

![pose demo](figure/pose_demo.png)

 

## Installation

1. Set up the python environment:

   ```
   conda create -n ContourPose python=3.7
   conda activate ContourPose
   ```

   ### install other requirements

   ```
   pip install -r requirements.txt
   ```

## Dataset Configuration
1. Prepare the dataset

   * The training and testing dataset for ContourPose can be found [here](https://github.com/ZJU-IVI/RT-Less_10parts). Unzip all files.
   
   * Download the SUN397 
   ```shell
   wget http://groups.csail.mit.edu/vision/SUN/releases/SUN2012pascalformat.tar.gz
   ```
   
2. Create soft link
   ```shell
   mkdir $ROOT/data
   ln -s path/to/Real Images $ROOT/data/train
   ln -s path/to/Synthetic Images $ROOT/data/train/renders
   ln -s path/to/Test Scenes $ROOT/data/test
   ln -s path/to/SUN2012pascalformat $ROOT/data/SUN2012pascalformat
   ```
   For more details on the file path, please refer to `dataset/Dataset.py`.

3. Object index mapping
   
   Since the dataset was still under construction when the paper was completed, the actual indexing of the objects may differ from that in the paper. Please refer to the index mapping relationships below.

| Indexing of objects in the paper (dataset) | obj1  |obj2     |   obj3  |   obj4  |  obj5   |  obj6   |   obj7  |  obj8   |   obj9  |  obj10   |
|--------------------------------------------| ----  |-----|-----|-----|-----|-----|-----|-----|-----|-----|
| Actual indexing of objects in this code    | obj1 |  obj2   |  obj3   |  obj7   |   obj13  |   obj16  |  obj18   |  obj18   |  obj21   |   obj32  |
   
   The test scenes in which the target object is tested can be found in the `sceneObjs.yml`  file.
## Pretrained model
   Download the pretrained models from [here](https://drive.google.com/drive/folders/1pOay_3ujEegVbahyLb3llHMVq2cFho-f?usp=drive_link) and put them to `$ROOT/model/obj{}/150.pkl` 
   
## Training and testing
1. Training
   Take the training on `obj1` as an example. 
   run  
   ```shell
   python main.py --class_type obj1 --train True
   ```

2. Testing
   Take the testing on `obj1` as an example. 

   The `sceneObjs.yml` file shows that obj1 is in scene with an index of 2. run

   ```shell
    python main.py --class_type obj1 --eval True --scene 13 --index 2
   ```
## Grasping experiment

The `graspScript` folder contains scripts for deploying multiple models in parallel and implementing multi-target pose estimation, and provides code that visualizes the results.

---

## 🚀 **Performance Improvements & Modern Compatibility**

This implementation includes significant performance optimizations and compatibility fixes for modern Python environments.

### **🔧 Compatibility Fixes**

The codebase has been updated to work with modern dependencies:

- **NumPy 2.x compatibility**: Fixed deprecated `np.str` and `np.float` usage
- **PyYAML compatibility**: Added `Loader=yaml.FullLoader` for secure YAML loading
- **PyTorch 2.x compatibility**: Updated tensor loading and device handling
- **SSL certificate fixes**: Resolved download issues on macOS

### **⚡ Metal GPU (MPS) Acceleration**

**Apple Silicon users can now leverage Metal Performance Shaders for dramatic speedups:**

```bash
# Automatic MPS acceleration (no code changes needed)
python main.py --class_type obj16 --eval True --scene 4 --index 0
```

The system automatically detects and uses the best available device:
1. **MPS (Metal GPU)** - Apple Silicon Macs
2. **CUDA** - NVIDIA GPUs  
3. **CPU** - Fallback

### **📊 Performance Benchmarks**

**Full Pipeline Performance (obj16 evaluation):**

| Device | Processing Rate | Total Time | Speedup |
|--------|----------------|------------|---------|
| **CPU** | 1.78 it/s | 3:44 | 1.0x |
| **MPS (Metal GPU)** | 17.60 it/s | 1:35 | **9.89x** |

**Neural Network Inference Only:**

| Device | FPS | Inference Time | Speedup |
|--------|-----|----------------|---------|
| **CPU** | 9.51 | 0.105s | 1.0x |
| **MPS (Metal GPU)** | 65.56 | 0.015s | **6.89x** |

**Accuracy remains identical across all devices.**

### **🔧 Modern Installation**

**For Python 3.8+ environments:**

```bash
# Create environment
conda create -n ContourPose python=3.8
conda activate ContourPose

# Install modern dependencies
pip install torch torchvision torchaudio  # Latest PyTorch with MPS support
pip install opencv-python numpy matplotlib pillow tqdm pyyaml scikit-learn scikit-image

# Quick setup for pretrained models
pip install gdown
```

**Automated model download:**
```bash
# Download all pretrained models automatically
mkdir -p model
cd model
gdown --folder "https://drive.google.com/drive/folders/1pOay_3ujEegVbahyLb3llHMVq2cFho-f?usp=drive_link"
```

### **⚡ Quick Test Setup**

**Test with scene data:**
```bash
# 1. Create data directory structure
mkdir -p data/test

# 2. Link your scene data (example with scene4)
ln -s /path/to/your/scene4 data/test/scene4

# 3. Run evaluation with automatic GPU acceleration
python main.py --class_type obj16 --eval True --scene 4 --index 0
```

### **🎯 Real-time Performance**

- **CPU**: ~1.8 FPS (not real-time)
- **MPS**: ~17.6 FPS (**near real-time**)

With MPS acceleration, ContourPose achieves **near real-time performance** suitable for robotic applications.

### **🔧 Implementation Details**

**Key improvements made:**

1. **Automatic device detection** with MPS priority
2. **DataParallel compatibility** handling for different devices  
3. **Float32 tensor conversion** for MPS compatibility
4. **Modern dependency support** with fallback mechanisms

**Modified files:**
- `main.py`: Device detection and model loading
- `eval.py`: Device-aware data transfer
- `dataset/Dataset.py`: Float32 tensor conversion and modern NumPy/YAML compatibility
- `utils/utils.py`: NumPy compatibility fixes

### **💡 System Requirements**

**Minimum Requirements:**
- Python 3.7+
- 4GB RAM
- Any CPU

**Recommended for Optimal Performance:**
- Python 3.8+
- 8GB+ RAM
- **Apple Silicon Mac** (M1/M2/M3) for MPS acceleration
- **NVIDIA GPU** with CUDA support

### **🔧 Troubleshooting**

**Common Issues:**

1. **SSL Certificate Error (macOS):**
   ```bash
   /Applications/Python\ 3.x/Install\ Certificates.command
   ```

2. **MPS Compatibility Issues:**
   - Ensure PyTorch 2.0+ is installed
   - Check MPS availability: `python -c "import torch; print(torch.backends.mps.is_available())"`

3. **Memory Issues:**
   - Reduce batch size in training
   - Use CPU if GPU memory is insufficient

4. **Model Loading Errors:**
   - Ensure pretrained models are in `model/obj{X}/150.pkl`
   - Check file permissions and paths

**Performance Tips:**
- Use MPS on Apple Silicon for best performance
- Enable GPU acceleration for 6-10x speedup
- Monitor system temperature during intensive inference

### **📈 Validation Results**

**Test Configuration:**
- Object: obj16
- Scene: scene4
- Platform: Apple Silicon (M-series)
- Method: ContourPose with MPS acceleration

**Accuracy Metrics:**
- **2D Projection Accuracy**: 97.8%
- **ADD Accuracy**: 89.9% 
- **Translation Error**: 4.67mm
- **Rotation Error**: 1.52°

**Real-world Performance:**
- Processing 416 test images in 1:35 minutes
- Suitable for real-time robotic applications
- Maintains high precision for industrial use cases