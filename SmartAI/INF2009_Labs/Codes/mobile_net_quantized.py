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

# Set quantization configuration
quantize = True

if quantize:
    print("Setting up quantization...")
    torch.backends.quantized.engine = "qnnpack"

print(f"Available quantization engines: {torch.backends.quantized.supported_engines}")
print(f"Selected quantization engine: {torch.backends.quantized.engine}")

# Load the model using modern approach
print("Loading model...")
weights = MobileNet_V2_QuantizedWeights.DEFAULT
model = models.quantization.mobilenet_v2(weights=weights)
model.eval()
print("Model loaded and ready")

# Create a test image if camera fails
def create_test_image():
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.putText(img, 'Test', (10, 112), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img

# Try to open camera with fallback options
def setup_camera():
    print("Setting up camera...")
    # Try different camera indices
    for i in range(10):
        print(f"Trying camera index {i}...")
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Successfully opened camera at index {i}")
            ret, test_frame = cap.read()
            if ret:
                print("Successfully read test frame")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
                cap.set(cv2.CAP_PROP_FPS, 36)
                return cap, False
            print("Failed to read test frame")
            cap.release()
    
    print("Warning: Could not initialize camera. Using test image instead.")
    return None, True

# Initialize camera or use test image
cap, use_test_image = setup_camera()

# Set up preprocessing
preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Get class names for predictions
classes = weights.meta["categories"]

# Performance tracking
started = time.time()
last_logged = time.time()
frame_count = 0
fps_measurements = 0

print("Starting inference loop...")
with torch.no_grad():
    while True:
        if use_test_image:
            image = create_test_image()
        else:
            ret, image = cap.read()
            if not ret:
                print("Failed to read frame, switching to test image")
                use_test_image = True
                image = create_test_image()

        try:
            # Convert BGR to RGB
            image = image[:, :, [2, 1, 0]]

            # Preprocess
            input_tensor = preprocess(image)
            input_batch = input_tensor.unsqueeze(0)

            # Run inference
            output = model(input_batch)

            # Show top predictions
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            top5_prob, top5_catid = torch.topk(probabilities, 5)
            for i in range(5):
                print(f"{classes[top5_catid[i]]:>20}: {top5_prob[i].item()*100:>6.2f}%")

            # Calculate FPS
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

if cap is not None:
    cap.release()
print("Test completed") 