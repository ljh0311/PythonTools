import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and result directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ImageMerger:
    def __init__(self, threshold=0.7):
        self.sift = cv2.SIFT_create()
        self.matcher = cv2.BFMatcher()
        self.matches_threshold = threshold

    def detect_features(self, img):
        """Detect SIFT features in an image."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.sift.detectAndCompute(gray, None)
        return keypoints, descriptors

    def match_features(self, desc1, desc2):
        """Match features between two images."""
        matches = self.matcher.knnMatch(desc1, desc2, k=2)
        good_matches = []
        for m, n in matches:
            if m.distance < self.matches_threshold * n.distance:
                good_matches.append(m)
        return good_matches

    def find_homography(self, kp1, kp2, good_matches):
        """Find homography matrix between two images."""
        if len(good_matches) < 4:
            return None
        
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        return H

    def merge_images(self, images):
        """Merge all provided images."""
        if len(images) < 2:
            return None

        # Use the first image as reference
        result = images[0]
        
        for i in range(1, len(images)):
            # Detect features
            kp1, desc1 = self.detect_features(result)
            kp2, desc2 = self.detect_features(images[i])
            
            # Match features
            good_matches = self.match_features(desc1, desc2)
            
            if len(good_matches) < 4:
                logger.warning(f"Not enough matches found for image {i}")
                continue
                
            # Find homography
            H = self.find_homography(kp1, kp2, good_matches)
            
            if H is None:
                logger.warning(f"Could not find homography for image {i}")
                continue
            
            # Calculate size of new image
            h1, w1 = result.shape[:2]
            h2, w2 = images[i].shape[:2]
            
            corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
            corners2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
            corners2_transformed = cv2.perspectiveTransform(corners2, H)
            
            corners = np.concatenate((corners1, corners2_transformed), axis=0)
            
            [xmin, ymin] = np.int32(corners.min(axis=0).ravel() - 0.5)
            [xmax, ymax] = np.int32(corners.max(axis=0).ravel() + 0.5)
            
            t = [-xmin, -ymin]
            Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])
            
            # Warp and blend images
            result_warped = cv2.warpPerspective(result, Ht, (xmax-xmin, ymax-ymin))
            img2_warped = cv2.warpPerspective(images[i], Ht.dot(H), (xmax-xmin, ymax-ymin))
            
            # Simple averaging blend
            mask1 = (result_warped != 0).astype(np.float32)
            mask2 = (img2_warped != 0).astype(np.float32)
            
            result = np.zeros_like(result_warped)
            for c in range(3):
                result[:, :, c] = (result_warped[:, :, c] * mask1[:, :, c] + 
                                 img2_warped[:, :, c] * mask2[:, :, c]) / (
                                 mask1[:, :, c] + mask2[:, :, c] + 1e-6)
            
            result = result.astype(np.uint8)
            
        return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/merge', methods=['POST'])
def merge_images():
    if 'images' not in request.files:
        return jsonify({'success': False, 'error': 'No images uploaded'})
    
    files = request.files.getlist('images')
    if len(files) < 2:
        return jsonify({'success': False, 'error': 'Please upload at least 2 images'})

    # Get threshold value
    threshold = float(request.form.get('threshold', 0.7))
    
    # Create image merger instance
    merger = ImageMerger(threshold=threshold)
    
    # Load and process images
    images = []
    temp_files = []
    
    try:
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                temp_files.append(filepath)
                
                img = cv2.imread(filepath)
                if img is None:
                    raise ValueError(f"Could not load image: {filename}")
                images.append(img)
        
        if not images:
            return jsonify({'success': False, 'error': 'No valid images uploaded'})
        
        # Merge images
        result = merger.merge_images(images)
        
        if result is None:
            return jsonify({'success': False, 'error': 'Failed to merge images'})
        
        # Save result
        result_filename = f"merged_{uuid.uuid4().hex[:8]}.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        cv2.imwrite(result_path, result)
        
        # Clean up temporary files
        for filepath in temp_files:
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {filepath}: {e}")
        
        return jsonify({
            'success': True,
            'result_image': f"/static/results/{result_filename}"
        })
        
    except Exception as e:
        logger.error(f"Error processing images: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 