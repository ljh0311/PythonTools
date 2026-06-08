import time
import torch
import numpy as np
from torchvision import models, transforms
from torchvision.models.quantization import MobileNet_V2_QuantizedWeights
import cv2
from PIL import Image
import warnings

# Filter out unnecessary warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torchvision')
warnings.filterwarnings('ignore', category=UserWarning, module='torch')

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

# This is the basic version without quantization
quantize = False

# Create a test image
def create_test_image():
    print("Creating test image...")
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.putText(img, 'Test', (10, 112), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img

print("Loading model...")
weights = MobileNet_V2_QuantizedWeights.DEFAULT
classes = weights.meta["categories"]
net = models.mobilenet_v2(weights=None)  # Basic version without quantization
print("Model loaded successfully")

# Set up preprocessing
preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Performance tracking
started = time.time()
last_logged = time.time()
frame_count = 0
fps_measurements = 0

print("Starting inference loop with test image...")
image = create_test_image()

with torch.no_grad():
    while True:
        try:
            # convert test image from BGR to RGB
            image_rgb = image[:, :, [2, 1, 0]]

            # preprocess
            input_tensor = preprocess(image_rgb)
            input_batch = input_tensor.unsqueeze(0)

            # run model
            output = net(input_batch)

            # Print top 5 predictions every second
            if time.time() - last_logged > 1:
                top = list(enumerate(output[0].softmax(dim=0)))
                top.sort(key=lambda x: x[1], reverse=True)
                print("\nTop 5 predictions:")
                for idx, val in top[:5]:
                    print(f"{classes[idx]:>20}: {val.item()*100:.2f}%")
            
            # log model performance
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
            break

print("Test completed") 