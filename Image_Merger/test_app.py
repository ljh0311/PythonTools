import os
import cv2
import numpy as np
from app import ImageMerger
import json
import datetime

def run_test(test_name, test_func):
    """Run a test and return its results in a structured format."""
    print(f"\nRunning {test_name}...")
    start_time = datetime.datetime.now()
    try:
        result = test_func()
        success = True if result else False
        error = None
    except Exception as e:
        success = False
        error = str(e)
    
    duration = (datetime.datetime.now() - start_time).total_seconds()
    
    return {
        "name": test_name,
        "success": success,
        "error": error,
        "duration": duration
    }

def test_image_merging():
    """Test the ImageMerger class with sample images."""
    merger = ImageMerger()
    results = []
    
    # List sample images in the current directory
    sample_images = [
        "photo_2025-03-19_00-22-22.jpg",
        "photo_2025-03-19_00-22-27.jpg",
        "photo_2025-05-05_11-37-36.jpg",
        "photo_2025-05-05_11-37-53.jpg"
    ]
    
    # Check if all images exist
    missing_images = []
    for img_path in sample_images:
        if not os.path.exists(img_path):
            missing_images.append(img_path)
    
    if missing_images:
        raise Exception(f"Missing images: {missing_images}")
    
    # Add images to the merger
    for img_path in sample_images[:2]:
        if not merger.add_image(img_path):
            raise Exception(f"Failed to add image {img_path}")
    
    # Test feature merge
    result_feature = merger.merge_images()
    if result_feature is None:
        raise Exception("Feature merge failed")
    cv2.imwrite("test_result_feature_merge.jpg", result_feature)
    
    # Test feature matches visualization
    result_matches = merger.show_feature_matches(0, 1)
    if result_matches is None:
        raise Exception("Feature matches visualization failed")
    cv2.imwrite("test_result_matches.jpg", result_matches)
    
    return True

def save_test_results(results):
    """Save test results to a JSON file."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    return filename

def main():
    """Run all tests and save results."""
    all_tests = [
        ("Image Merging", test_image_merging),
    ]
    
    results = []
    for test_name, test_func in all_tests:
        result = run_test(test_name, test_func)
        results.append(result)
        
        # Print immediate feedback
        status = "✓" if result["success"] else "✗"
        print(f"{status} {test_name} ({result['duration']:.2f}s)")
        if not result["success"]:
            print(f"  Error: {result['error']}")
    
    # Save results
    results_file = save_test_results(results)
    print(f"\nTest results saved to {results_file}")
    
    # Return overall success
    return all(r["success"] for r in results)

if __name__ == "__main__":
    success = main()
    if success:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed. Check the results file for details.")
        exit(1) 