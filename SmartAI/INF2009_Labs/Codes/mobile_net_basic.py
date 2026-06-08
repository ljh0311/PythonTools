import time
import torch
import numpy as np
from torchvision import models, transforms
from torchvision.models.quantization import MobileNet_V2_QuantizedWeights
import cv2
from PIL import Image
import warnings
import traceback

# Filter out unnecessary warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torchvision')
warnings.filterwarnings('ignore', category=UserWarning, module='torch')

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

# This is the basic version without quantization
quantize = False

def create_test_image():
    print("Creating test image...")
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.putText(img, 'Test', (10, 112), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img

def setup_camera():
    try:
        print("Setting up camera...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Could not open camera. Using test image.")
            return None, True
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
        cap.set(cv2.CAP_PROP_FPS, 36)
        
        ret, test_frame = cap.read()
        if not ret:
            print("Could not read from camera. Using test image.")
            cap.release()
            return None, True
            
        return cap, False
    except Exception as e:
        print(f"Camera setup error: {str(e)}")
        return None, True

# Set up preprocessing
preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Load model
print("Loading model...")
weights = MobileNet_V2_QuantizedWeights.DEFAULT
classes = weights.meta["categories"]
net = models.mobilenet_v2(weights=None)  # Basic version without quantization
net.eval()  # Set to evaluation mode
print("Model loaded successfully")

# Initialize camera or test image
cap, use_test_image = setup_camera()
if use_test_image:
    test_image = create_test_image()

# Performance tracking
started = time.time()
last_logged = time.time()
frame_count = 0
fps_measurements = 0

print("Starting inference loop...")
try:
    with torch.no_grad():
        while True:
            try:
                # Get frame
                if use_test_image:
                    image = test_image
                else:
                    ret, image = cap.read()
                    if not ret:
                        print("Failed to read frame, switching to test image")
                        use_test_image = True
                        test_image = create_test_image()
                        image = test_image
                        if cap is not None:
                            cap.release()
                            cap = None

                # Convert BGR to RGB
                image_rgb = image[:, :, [2, 1, 0]]

                # Preprocess
                input_tensor = preprocess(image_rgb)
                input_batch = input_tensor.unsqueeze(0)

                # Run inference
                output = net(input_batch)

                # Print top 5 predictions every second
                if time.time() - last_logged > 1:
                    top = list(enumerate(output[0].softmax(dim=0)))
                    top.sort(key=lambda x: x[1], reverse=True)
                    print("\nTop 5 predictions:")
                    for idx, val in top[:5]:
                        print(f"{classes[idx]:>20}: {val.item()*100:.2f}%")

                # Log performance
                frame_count += 1
                now = time.time()
                if now - last_logged > 1:
                    current_fps = frame_count / (now - last_logged)
                    print(f"============={current_fps:.2f} fps =================")
                    fps_measurements += 1
                    if fps_measurements >= 3:  # Exit after 3 measurements
                        print("Completed FPS measurements")
                        break
                    last_logged = now
                    frame_count = 0

            except Exception as e:
                print(f"Error during inference: {str(e)}")
                traceback.print_exc()
                break

finally:
    if cap is not None:
        cap.release()
    print("Test completed")

