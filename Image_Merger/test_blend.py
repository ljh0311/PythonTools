import os
import cv2
import numpy as np
from app import ImageMerger

def test_blend_functionality():
    """Test the feature_aligned_blend functionality of the ImageMerger class."""
    # Initialize the merger
    merger = ImageMerger()
    
    # List sample images in the current directory
    sample_images = [
        "photo_2025-03-19_00-22-22.jpg",
        "photo_2025-03-19_00-22-27.jpg"
    ]
    
    # Check if all images exist
    missing_images = []
    for img_path in sample_images:
        if not os.path.exists(img_path):
            missing_images.append(img_path)
    
    if missing_images:
        print(f"Error: The following images are missing: {missing_images}")
        return False
    
    # Add images to the merger
    for img_path in sample_images:
        if not merger.add_image(img_path):
            print(f"Error: Failed to add image {img_path}")
            return False
    
    # Test feature-aligned blend with different alpha values
    alphas = [0.3, 0.5, 0.7]
    for alpha in alphas:
        print(f"Testing feature-aligned blend with alpha={alpha}...")
        result_blend = merger.feature_aligned_blend(alpha=alpha)
        if result_blend is not None:
            print(f"✓ Feature-aligned blend successful with alpha={alpha}")
            # Save result to confirm it works
            cv2.imwrite(f"test_result_blend_alpha_{alpha}.jpg", result_blend)
        else:
            print(f"✗ Feature-aligned blend failed with alpha={alpha}")
            return False
    
    return True

if __name__ == "__main__":
    print("Testing Feature-Aligned Blend functionality...")
    success = test_blend_functionality()
    
    if success:
        print("\nAll blend tests completed successfully!")
        print("You can now run the Flask application with 'python app.py' or 'run_flask.bat'")
    else:
        print("\nSome tests failed. Please check the errors above.") 