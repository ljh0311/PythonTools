import time
import torch
import numpy as np
from torchvision import models, transforms
import cv2
from PIL import Image
import sys
import platform
import warnings

# Filter warnings
warnings.filterwarnings('ignore', category=UserWarning)

print("Starting MobileNet with predictions...")

print("Setting up camera...")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
cap.set(cv2.CAP_PROP_FPS, 36)

preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

print("Loading model...")
# Load the model
net = models.mobilenet_v2(weights='DEFAULT')
net.eval()

# Get the class labels
with open('imagenet_classes.txt', 'r') as f:
    classes = [line.strip() for line in f.readlines()]

print("Model loaded successfully")

started = time.time()
last_logged = time.time()
frame_count = 0
fps_measurements = 0

print("Starting inference loop...")
try:
    with torch.no_grad():
        while fps_measurements < 3:  # Only run for exactly 3 measurements
            # read frame
            ret, image = cap.read()
            if not ret:
                print("Failed to read frame")
                break

            # convert opencv output from BGR to RGB
            image = image[:, :, [2, 1, 0]]

            # preprocess
            input_tensor = preprocess(image)
            input_batch = input_tensor.unsqueeze(0)

            # run model
            output = net(input_batch)

            # Print top 10 predictions
            top = list(enumerate(output[0].softmax(dim=0)))
            top.sort(key=lambda x: x[1], reverse=True)
            print("\nTop 10 predictions:")
            for idx, val in top[:10]:
                print(f"{val.item()*100:.2f}% {classes[idx]}")
            print("=" * 70)

            # log model performance
            frame_count += 1
            now = time.time()
            if now - last_logged > 1:
                current_fps = frame_count / (now-last_logged)
                print(f"\nMeasurement {fps_measurements + 1}/3")
                print(f"Current FPS: {current_fps:.2f}")
                print("=" * 30)
                fps_measurements += 1
                last_logged = now
                frame_count = 0

finally:
    print("\nCompleted FPS measurements")
    if cap is not None:
        cap.release()
    print("Test completed") 