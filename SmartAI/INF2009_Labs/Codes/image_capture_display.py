# Reference: https://pyimagesearch.com/2014/08/04/opencv-python-color-detection/
import cv2
import numpy as np
import os
from datetime import datetime

# %% Defining a list of boundaries in the RGB color space
# (or rather, BGR, since OpenCV represents images as NumPy arrays in reverse order)
# Refer to https://docs.opencv.org/3.4/da/d97/tutorial_threshold_inRange.html
boundaries = [
    ([0, 0, 100], [100, 100, 255]),  # For Red (more lenient)
    ([100, 0, 0], [255, 100, 100]),  # For Blue (more lenient)
    ([0, 100, 0], [100, 255, 100]),  # For Green (more lenient)
    ([0, 100, 100], [100, 255, 255]),
]  # For Yellow (B: 0-100, G: 100-255, R: 100-255)


# %% Normalize the Image for display (Optional)
def normalizeImg(Img):
    Img = np.float64(Img)  # Converting to float to avoid errors due to division
    if np.max(Img) - np.min(Img) != 0:  # Avoid division by zero
        norm_img = (Img - np.min(Img)) / (np.max(Img) - np.min(Img))
        norm_img = np.uint8(norm_img * 255.0)
    else:
        norm_img = np.zeros_like(Img, dtype=np.uint8)
    return norm_img


# %% Create output directory if it doesn't exist
output_dir = "results"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# %% Open CV Video Capture and frame analysis
cap = cv2.VideoCapture(0)

# Check if the webcam is opened correctly
if not cap.isOpened():
    raise IOError("Cannot open webcam")

# Set a consistent display width for each frame
DISPLAY_WIDTH = 320  # You can adjust this value
DISPLAY_HEIGHT = 240  # You can adjust this value

# Variables for saving images
save_image = False
saved = False

print("Press 's' to save current frame")
print("Press 'q' to quit")

# The loop will break on pressing the 'q' key
while True:
    try:
        # Capture one frame
        ret, frame = cap.read()

        # Resize the original frame
        frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))

        output = []

        # loop over the boundaries
        for lower, upper in boundaries:
            # create NumPy arrays from the boundaries
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

            # find the colors within the specified boundaries and apply the mask
            mask = cv2.inRange(frame, lower, upper)
            segmented = cv2.bitwise_and(frame, frame, mask=mask)
            # Resize the segmented image to match display size
            segmented = cv2.resize(segmented, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
            output.append(segmented)

        # Output is appended to be of size Pixels X 4 (for R, G, B, Y)
        red_img = normalizeImg(output[0])
        green_img = normalizeImg(output[1])
        blue_img = normalizeImg(output[2])
        yellow_img = normalizeImg(output[3])

        # Add labels to each image
        def add_label(image, label):
            # Create a copy of the image to avoid modifying the original
            labeled = image.copy()
            # Add text at the top of the image
            cv2.putText(labeled, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, (255, 255, 255), 2)
            return labeled

        # Add labels to images
        frame = add_label(frame, "Original")
        red_img = add_label(red_img, "Red")
        green_img = add_label(green_img, "Green")
        blue_img = add_label(blue_img, "Blue")
        yellow_img = add_label(yellow_img, "Yellow")

        # horizontal Concatenation for displaying the images and colour segmentations
        top_row = cv2.hconcat([frame, red_img, green_img])
        bottom_row = cv2.hconcat([blue_img, yellow_img, np.zeros_like(frame)])  # Add blank space to match top row
        catImg = cv2.vconcat([top_row, bottom_row])
        
        # Display the final image
        cv2.imshow("Color Segmentation", catImg)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s") and not saved:
            # Generate timestamp for unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"color_segmentation_{timestamp}.jpg")
            cv2.imwrite(filename, catImg)
            print(f"Saved result to {filename}")
            saved = True

    except KeyboardInterrupt:
        break

cap.release()
cv2.destroyAllWindows()
