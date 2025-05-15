import os
import cv2
import numpy as np
from app import save_image, app

def test_path_generation():
    """Test that image paths are being generated correctly."""
    # Create a simple test image
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    test_img[:50, :50] = [0, 0, 255]  # Red square
    test_img[50:, 50:] = [0, 255, 0]  # Green square
    
    # Reset Flask app context
    with app.app_context():
        # Test save_image function
        result_filename = save_image(test_img)
        result_path = f"{app.config['RESULTS_FOLDER']}/{result_filename}"
        
        # Print paths for debugging
        print("Generated filename:", result_filename)
        print("Full result path:", result_path)
        print("Path with leading slash:", f"/{result_path}")
        
        # Check if file exists
        full_path = os.path.join(os.getcwd(), result_path)
        print("Absolute path:", full_path)
        print("File exists:", os.path.exists(full_path))
        
        # Test other path formats
        web_path = f"/{result_path}"
        print("Web path:", web_path)
        
        # The path that would be used in HTML
        html_path = f"<img src='{web_path}'>"
        print("HTML usage:", html_path)
        
        return result_path

if __name__ == "__main__":
    print("Testing image path generation...")
    path = test_path_generation()
    print("\nTest completed. Path generated:", path) 