import os
import cv2
import numpy as np
import uuid
import base64
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
import logging
import json
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join('static', 'results')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['TEMP_FOLDER'] = tempfile.mkdtemp()  # Create temporary directory

@app.before_request
def cleanup_old_files():
    """Clean up old temporary files before each request"""
    try:
        # Clean files older than 1 hour
        current_time = datetime.now().timestamp()
        for folder in [app.config['TEMP_FOLDER'], app.config['UPLOAD_FOLDER'], app.config['RESULTS_FOLDER']]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath):
                        # Check if file is older than 1 hour
                        if current_time - os.path.getmtime(filepath) > 3600:
                            try:
                                os.remove(filepath)
                                logger.info(f"Cleaned up old file: {filepath}")
                            except Exception as e:
                                logger.error(f"Error cleaning up file {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")

@app.teardown_appcontext
def cleanup_temp_folder(error):
    """Clean up temporary folder when application context ends"""
    try:
        shutil.rmtree(app.config['TEMP_FOLDER'], ignore_errors=True)
    except Exception as e:
        logger.error(f"Error cleaning up temp folder: {e}")

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Custom Jinja2 filter for timestamp formatting
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to formatted datetime string"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Image merger class from the original code, without feature blend functionality
class ImageMerger:
    def __init__(self):
        self.sift = cv2.SIFT_create()
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher()
        self.images = []
        self.matches_threshold = 0.7
        self.use_orb = False  # Add a toggle for different detector
        
        # Preprocessing parameters
        self.night_threshold = 100  # Brightness threshold for night image detection
        self.night_clahe_clip_limit = 4.0  # CLAHE clip limit for night images
        self.night_clahe_grid_size = (8, 8)  # CLAHE grid size for night images
        self.normal_clahe_clip_limit = 2.0  # CLAHE clip limit for normal images
        self.normal_clahe_grid_size = (8, 8)  # CLAHE grid size for normal images
        self.night_denoise_strength = 10  # Denoising strength for night images
        self.night_denoise_template_size = 7  # Template size for denoising
        self.night_denoise_search_size = 21  # Search size for denoising
        self.night_percentile_low = 5  # Lower percentile for contrast stretching
        self.night_percentile_high = 95  # Upper percentile for contrast stretching
        self.night_canny_low = 50  # Lower threshold for Canny edge detection
        self.night_canny_high = 150  # Upper threshold for Canny edge detection
        self.night_edge_weight = 0.7  # Weight for edge enhancement

    def add_image(self, image_path):
        """Add an image to the merger with size limits for better performance."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            # Resize large images for better performance
            max_dimension = 800  # Scale down if image is too big
            height, width = img.shape[:2]

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height))
                logger.info(
                    f"Resized image from {width}x{height} to {new_width}x{new_height}"
                )

            self.images.append(img)
            return True
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return False

    def detect_features(self, img):
        """Detect SIFT features in an image with preprocessing."""
        # Use preprocessing for better feature detection
        processed = self.preprocess_for_feature_detection(img)
        
        if self.use_orb:
            # Use ORB detector
            keypoints, descriptors = self.orb.detectAndCompute(processed, None)
            
            # If we don't find enough keypoints, try more aggressive enhancement
            if len(keypoints) < 20:
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
                enhanced = clahe.apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
                keypoints, descriptors = self.orb.detectAndCompute(enhanced, None)
        else:
            # Use SIFT detector (default)
            keypoints, descriptors = self.sift.detectAndCompute(processed, None)
            
            # If we don't find enough keypoints, try more aggressive enhancement
            if len(keypoints) < 20:
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
                enhanced = clahe.apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
                keypoints, descriptors = self.sift.detectAndCompute(enhanced, None)
        
        return keypoints, descriptors

    def match_features(self, desc1, desc2):
        """Match features between two images."""
        if desc1 is None or desc2 is None:
            return []
            
        if self.use_orb:
            # For ORB, use Hamming distance
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            try:
                matches = matcher.knnMatch(desc1, desc2, k=2)
                good_matches = []
                for m, n in matches:
                    if m.distance < self.matches_threshold * n.distance:
                        good_matches.append(m)
                return good_matches
            except Exception as e:
                # Fall back to simpler matching if knnMatch fails
                logger.warning(f"ORB knnMatch failed: {e}. Falling back to simple matching.")
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = matcher.match(desc1, desc2)
                # Sort matches by distance
                matches = sorted(matches, key=lambda x: x.distance)
                # Return top 25% of matches
                return matches[:max(10, int(len(matches) * 0.25))]
        else:
            # For SIFT, use L2 distance
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

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(
            -1, 1, 2
        )
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(
            -1, 1, 2
        )

        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        return H

    def merge_images(self):
        """Merge all loaded images."""
        if len(self.images) < 2:
            return None

        try:
            # Use the first image as reference
            result = self.images[
                0
            ].copy()  # Create a copy to avoid modifying the original

            for i in range(1, len(self.images)):
                try:
                    # Detect features
                    kp1, desc1 = self.detect_features(result)
                    kp2, desc2 = self.detect_features(self.images[i])

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
                    h2, w2 = self.images[i].shape[:2]

                    corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(
                        -1, 1, 2
                    )
                    corners2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(
                        -1, 1, 2
                    )
                    corners2_transformed = cv2.perspectiveTransform(corners2, H)

                    corners = np.concatenate((corners1, corners2_transformed), axis=0)

                    [xmin, ymin] = np.int32(corners.min(axis=0).ravel() - 0.5)
                    [xmax, ymax] = np.int32(corners.max(axis=0).ravel() + 0.5)

                    t = [-xmin, -ymin]
                    Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])

                    # Warp and blend images
                    result_warped = cv2.warpPerspective(
                        result, Ht, (xmax - xmin, ymax - ymin)
                    )
                    img2_warped = cv2.warpPerspective(
                        self.images[i], Ht.dot(H), (xmax - xmin, ymax - ymin)
                    )

                    # Simple averaging blend
                    mask1 = (result_warped != 0).astype(np.float32)
                    mask2 = (img2_warped != 0).astype(np.float32)

                    result = np.zeros_like(result_warped)
                    for c in range(3):
                        result[:, :, c] = (
                            result_warped[:, :, c] * mask1[:, :, c]
                            + img2_warped[:, :, c] * mask2[:, :, c]
                        ) / (mask1[:, :, c] + mask2[:, :, c] + 1e-6)

                    result = result.astype(np.uint8)
                except Exception as e:
                    logger.error(f"Error processing image {i}: {e}")
                    # Continue with next image instead of failing completely
                    continue

            return result
        except Exception as e:
            logger.error(f"Error in merge_images: {e}")
            return None

    def remove_image(self, index):
        """Remove an image from the loaded set"""
        if 0 <= index < len(self.images):
            self.images.pop(index)

    def preprocess_for_feature_detection(self, img):
        """Process images for better feature detection, with special handling for night images"""
        # Convert to grayscale for processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect if this is a night/dark image by checking average brightness
        avg_brightness = np.mean(gray)
        is_night_image = avg_brightness < self.night_threshold  # Use configurable threshold
        
        if is_night_image:
            # For night images, use more aggressive preprocessing
            enhanced = self._enhance_night_image(gray)
            return enhanced
        else:
            # For normal images, use standard preprocessing
            enhanced = self._enhance_normal_image(gray)
            return enhanced

    def _enhance_night_image(self, gray):
        """Enhance night/dark images with optimized parameters"""
        # Increase contrast with CLAHE
        clahe = cv2.createCLAHE(
            clipLimit=self.night_clahe_clip_limit,
            tileGridSize=self.night_clahe_grid_size
        )
        enhanced = clahe.apply(gray)
        
        # Adaptive contrast stretching
        p5 = np.percentile(enhanced, self.night_percentile_low)
        p95 = np.percentile(enhanced, self.night_percentile_high)
        enhanced = np.clip((enhanced - p5) * 255.0 / (p95 - p5), 0, 255).astype(np.uint8)
        
        # Denoise with optimized parameters
        denoised = cv2.fastNlMeansDenoising(
            enhanced,
            None,
            self.night_denoise_strength,
            self.night_denoise_template_size,
            self.night_denoise_search_size
        )
        
        # Edge enhancement with configurable weights
        edges = cv2.Canny(denoised, self.night_canny_low, self.night_canny_high)
        enhanced_with_edges = cv2.addWeighted(
            denoised,
            self.night_edge_weight,
            edges,
            1 - self.night_edge_weight,
            0
        )
        
        return enhanced_with_edges

    def _enhance_normal_image(self, gray):
        """Enhance normal/bright images with optimized parameters"""
        # Increase contrast with CLAHE
        clahe = cv2.createCLAHE(
            clipLimit=self.normal_clahe_clip_limit,
            tileGridSize=self.normal_clahe_grid_size
        )
        enhanced = clahe.apply(gray)
        
        # Apply adaptive blur based on image size
        blur_size = self._calculate_adaptive_blur_size(gray.shape)
        blurred = cv2.GaussianBlur(enhanced, blur_size, 0)
        
        return blurred

    def _calculate_adaptive_blur_size(self, shape):
        """Calculate adaptive blur size based on image dimensions"""
        min_dim = min(shape)
        if min_dim < 500:
            return (3, 3)
        elif min_dim < 1000:
            return (5, 5)
        else:
            return (7, 7)

    def tune_preprocessing_parameters(self, image_set):
        """Tune preprocessing parameters based on a set of images.
        
        Args:
            image_set: List of images to analyze for parameter tuning
            
        Returns:
            dict: Dictionary containing tuned parameters and recommendations
        """
        if not image_set:
            return {
                'success': False,
                'message': 'No images provided for tuning'
            }
            
        brightness_values = []
        feature_counts = []
        contrast_values = []
        noise_levels = []
        
        # Collect statistics from image set
        for img in image_set:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate brightness
            brightness = np.mean(gray)
            brightness_values.append(brightness)
            
            # Calculate contrast
            p5 = np.percentile(gray, 5)
            p95 = np.percentile(gray, 95)
            contrast = (p95 - p5) / 255.0
            contrast_values.append(contrast)
            
            # Estimate noise level using Laplacian variance
            noise = cv2.Laplacian(gray, cv2.CV_64F).var()
            noise_levels.append(noise)
            
            # Count features with current parameters
            processed = self.preprocess_for_feature_detection(img)
            kp, _ = self.detect_features(processed)
            feature_counts.append(len(kp))
        
        # Calculate statistics
        avg_brightness = np.mean(brightness_values)
        avg_contrast = np.mean(contrast_values)
        avg_noise = np.mean(noise_levels)
        avg_features = np.mean(feature_counts)
        
        # Adjust night threshold based on brightness distribution
        self.night_threshold = np.percentile(brightness_values, 25)
        
        # Adjust CLAHE parameters based on feature detection success and contrast
        if avg_features < 100:
            # Increase contrast enhancement for low feature count
            self.night_clahe_clip_limit *= 1.2
            self.normal_clahe_clip_limit *= 1.1
        elif avg_features > 500:
            # Reduce contrast enhancement for high feature count
            self.night_clahe_clip_limit *= 0.9
            self.normal_clahe_clip_limit *= 0.95
            
        # Adjust CLAHE grid size based on image dimensions
        avg_dim = np.mean([min(img.shape[:2]) for img in image_set])
        if avg_dim < 500:
            self.night_clahe_grid_size = (4, 4)
            self.normal_clahe_grid_size = (4, 4)
        elif avg_dim < 1000:
            self.night_clahe_grid_size = (8, 8)
            self.normal_clahe_grid_size = (8, 8)
        else:
            self.night_clahe_grid_size = (16, 16)
            self.normal_clahe_grid_size = (16, 16)
            
        # Adjust denoising parameters based on noise level
        if avg_noise > 100:
            self.night_denoise_strength = 15
            self.night_denoise_template_size = 7
            self.night_denoise_search_size = 21
        else:
            self.night_denoise_strength = 10
            self.night_denoise_template_size = 7
            self.night_denoise_search_size = 21
            
        # Generate recommendations
        recommendations = []
        if avg_brightness < 50:
            recommendations.append("Consider using ORB detector for better feature detection in dark images")
        if avg_contrast < 0.3:
            recommendations.append("Images have low contrast - consider increasing CLAHE limits")
        if avg_noise > 100:
            recommendations.append("High noise detected - denoising parameters have been increased")
        if avg_features < 50:
            recommendations.append("Low feature count detected - consider using manual feature matching")
            
        # Log the tuned parameters
        logger.info(
            f"Tuned preprocessing parameters:\n"
            f"  Night threshold: {self.night_threshold:.1f}\n"
            f"  Night CLAHE: limit={self.night_clahe_clip_limit:.1f}, grid={self.night_clahe_grid_size}\n"
            f"  Normal CLAHE: limit={self.normal_clahe_clip_limit:.1f}, grid={self.normal_clahe_grid_size}\n"
            f"  Denoising: strength={self.night_denoise_strength}, template={self.night_denoise_template_size}, search={self.night_denoise_search_size}"
        )
        
        return {
            'success': True,
            'parameters': {
                'night_threshold': self.night_threshold,
                'night_clahe_clip_limit': self.night_clahe_clip_limit,
                'normal_clahe_clip_limit': self.normal_clahe_clip_limit,
                'night_clahe_grid_size': self.night_clahe_grid_size,
                'normal_clahe_grid_size': self.normal_clahe_grid_size,
                'night_denoise_strength': self.night_denoise_strength,
                'night_denoise_template_size': self.night_denoise_template_size,
                'night_denoise_search_size': self.night_denoise_search_size
            },
            'statistics': {
                'avg_brightness': avg_brightness,
                'avg_contrast': avg_contrast,
                'avg_noise': avg_noise,
                'avg_features': avg_features
            },
            'recommendations': recommendations
        }

    def show_feature_matches(self, img1_index=0, img2_index=1, max_matches=50):
        """Display feature matches between two images"""
        if len(self.images) < 2 or img1_index >= len(self.images) or img2_index >= len(self.images):
            return None

        try:
            img1 = self.images[img1_index]
            img2 = self.images[img2_index]

            kp1, desc1 = self.detect_features(img1)
            kp2, desc2 = self.detect_features(img2)

            good_matches = self.match_features(desc1, desc2)

            if len(good_matches) < 4:
                return None

            # Draw matches
            matches_to_draw = good_matches[:min(max_matches, len(good_matches))]
            match_img = cv2.drawMatches(
                img1,
                kp1,
                img2,
                kp2,
                matches_to_draw,
                None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

            return match_img
        except Exception as e:
            logger.error(f"Error in show_feature_matches: {e}")
            return None

    def get_preprocessed_image(self, img_index=0):
        """Get preprocessed version of an image"""
        if img_index >= len(self.images):
            return None

        try:
            img = self.images[img_index]
            processed = self.preprocess_for_feature_detection(img)
            
            # Convert grayscale processed image to BGR for display
            if len(processed.shape) == 2:
                processed_bgr = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            else:
                processed_bgr = processed
                
            # Create side-by-side image
            h, w = img.shape[:2]
            comparison = np.zeros((h, w*2, 3), dtype=np.uint8)
            comparison[:, :w] = img
            comparison[:, w:] = processed_bgr
            
            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(comparison, "Original", (10, 30), font, 1, (0, 255, 0), 2)
            cv2.putText(comparison, "Preprocessed", (w+10, 30), font, 1, (0, 255, 0), 2)
            
            return comparison
        except Exception as e:
            logger.error(f"Error creating preprocessed view: {e}")
            return None

    def feature_aligned_blend(self, alpha=0.5):
        """Create a feature-aligned blend of the images with adjustable transparency"""
        try:
            if len(self.images) < 2:
                return None
            
            # STEP 1: Find features and matches
            img1 = self.images[0].copy()
            img2 = self.images[1].copy()
            
            kp1, desc1 = self.detect_features(img1)
            kp2, desc2 = self.detect_features(img2)
            
            good_matches = self.match_features(desc1, desc2)
            
            if len(good_matches) < 4:
                # Not enough matches for alignment, fall back to simple overlay
                logger.warning(f"Only {len(good_matches)} matches found. Using simple overlay.")
                return self.do_simple_blend(alpha)
            
            # STEP 2: Find transformation between images
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Try to find homography
            try:
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if H is None:
                    raise ValueError("Homography is None")
            except Exception as e:
                logger.warning(f"Could not find alignment: {str(e)}. Using simple overlay.")
                return self.do_simple_blend(alpha)
            
            # STEP 3: Compute output dimensions
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            
            corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
            corners2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
            corners1_transformed = cv2.perspectiveTransform(corners1, H)
            
            # Combine all corners to find output dimensions
            all_corners = np.concatenate((corners2, corners1_transformed), axis=0)
            x_min, y_min = np.int32(all_corners.min(axis=0).ravel() - 0.5)
            x_max, y_max = np.int32(all_corners.max(axis=0).ravel() + 0.5)
            
            # Apply offset to ensure everything is in frame
            offset = [-x_min, -y_min]
            translation_matrix = np.array([
                [1, 0, offset[0]],
                [0, 1, offset[1]],
                [0, 0, 1]
            ])
            
            output_size = (x_max - x_min, y_max - y_min)
            
            # STEP 4: Warp first image to align with the second
            warped_img1 = cv2.warpPerspective(
                img1, 
                translation_matrix.dot(H),
                output_size
            )
            
            # Place second image in the expanded canvas
            expanded_img2 = np.zeros_like(warped_img1)
            expanded_img2[offset[1]:offset[1]+h2, offset[0]:offset[0]+w2] = img2
            
            # STEP 5: Blend the aligned images
            result = cv2.addWeighted(warped_img1, alpha, expanded_img2, 1.0 - alpha, 0)
            
            # Enhance contrast to make the result more visible
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2Lab)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            result = cv2.cvtColor(lab_enhanced, cv2.COLOR_Lab2BGR)
            
            # Add a frame and title
            border_size = 20
            result_with_border = cv2.copyMakeBorder(
                result, 
                border_size, border_size, border_size, border_size,
                cv2.BORDER_CONSTANT, 
                value=[0, 0, 0]
            )
            
            # Add title indicating feature-aligned blend
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = f"Feature-Aligned Blend (Alpha: {alpha:.2f}, Matches: {len(good_matches)})"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (result_with_border.shape[1] - text_size[0]) // 2
            cv2.putText(result_with_border, title, (text_x, border_size - 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return result_with_border
            
        except Exception as e:
            logger.error(f"Error during feature-aligned blend: {str(e)}")
            return self.do_simple_blend(alpha)
    
    def do_simple_blend(self, alpha=0.5):
        """Fallback method for simple overlay blend without feature alignment"""
        try:
            # Make copies of the images
            img1 = self.images[0].copy()
            img2 = self.images[1].copy()
            
            # Make sure both images are the same size for blending
            max_height = max(img1.shape[0], img2.shape[0])
            max_width = max(img1.shape[1], img2.shape[1])
            
            # Resize both images to the same dimensions
            img1_resized = np.zeros((max_height, max_width, 3), dtype=np.uint8)
            img2_resized = np.zeros((max_height, max_width, 3), dtype=np.uint8)
            
            # Place the original images centered in the new canvases
            y1_offset = (max_height - img1.shape[0]) // 2
            x1_offset = (max_width - img1.shape[1]) // 2
            img1_resized[y1_offset:y1_offset+img1.shape[0], x1_offset:x1_offset+img1.shape[1]] = img1
            
            y2_offset = (max_height - img2.shape[0]) // 2
            x2_offset = (max_width - img2.shape[1]) // 2
            img2_resized[y2_offset:y2_offset+img2.shape[0], x2_offset:x2_offset+img2.shape[1]] = img2
            
            # Apply alpha blending with the slider value
            result = cv2.addWeighted(img1_resized, alpha, img2_resized, 1.0 - alpha, 0)
            
            # Enhance contrast to make the result more visible
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2Lab)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            result = cv2.cvtColor(lab_enhanced, cv2.COLOR_Lab2BGR)
            
            # Create a better looking frame
            border_size = 20
            result_with_border = cv2.copyMakeBorder(
                result, 
                border_size, border_size, border_size, border_size,
                cv2.BORDER_CONSTANT, 
                value=[0, 0, 0]
            )
            
            # Add title
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = f"Simple Overlay Blend (Alpha: {alpha:.2f})"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (result_with_border.shape[1] - text_size[0]) // 2
            cv2.putText(result_with_border, title, (text_x, border_size - 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return result_with_border
        except Exception as e:
            logger.error(f"Error during simple blend: {str(e)}")
            return None

    def manual_feature_match(self, manual_matches):
        """Create a panorama using manually specified matching points"""
        try:
            if len(self.images) < 2:
                return None
            
            img1 = self.images[0].copy()
            img2 = self.images[1].copy()
            
            # manual_matches should be a list of pairs of points: [[[x1,y1], [x2,y2]], ...]
            if len(manual_matches) < 4:
                logger.warning("Need at least 4 point pairs for homography")
                return None
            
            # Extract source and destination points
            src_pts = np.float32([m[0] for m in manual_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([m[1] for m in manual_matches]).reshape(-1, 1, 2)
            
            # Find homography
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if H is None:
                logger.warning("Could not compute homography from manual points")
                return None
            
            # Calculate size of new image
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            
            corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
            corners2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
            corners2_transformed = cv2.perspectiveTransform(corners2, H)
            
            corners = np.concatenate((corners1, corners2_transformed), axis=0)
            
            [xmin, ymin] = np.int32(corners.min(axis=0).ravel() - 0.5)
            [xmax, ymax] = np.int32(corners.max(axis=0).ravel() + 0.5)
            
            t = [-xmin, -ymin]
            Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])
            
            # Warp and blend images
            result_warped = cv2.warpPerspective(img1, Ht, (xmax - xmin, ymax - ymin))
            img2_warped = cv2.warpPerspective(img2, Ht.dot(H), (xmax - xmin, ymax - ymin))
            
            # Simple averaging blend
            mask1 = (result_warped != 0).astype(np.float32)
            mask2 = (img2_warped != 0).astype(np.float32)
            
            result = np.zeros_like(result_warped)
            for c in range(3):
                result[:, :, c] = (
                    result_warped[:, :, c] * mask1[:, :, c] +
                    img2_warped[:, :, c] * mask2[:, :, c]
                ) / (mask1[:, :, c] + mask2[:, :, c] + 1e-6)
            
            result = result.astype(np.uint8)
            
            # Add markers for the manually selected points
            for i, (src, dst) in enumerate(manual_matches):
                # Transform source points
                src_transformed = cv2.perspectiveTransform(
                    np.float32([src]).reshape(-1, 1, 2), Ht)
                x1, y1 = src_transformed[0, 0].astype(int)
                
                # Transform destination points
                dst_transformed = cv2.perspectiveTransform(
                    np.float32([dst]).reshape(-1, 1, 2), Ht.dot(H))
                x2, y2 = dst_transformed[0, 0].astype(int)
                
                # Draw markers
                cv2.circle(result, (x1, y1), 5, (0, 0, 255), -1)  # Red for source
                cv2.circle(result, (x2, y2), 5, (0, 255, 0), -1)  # Green for dest
                cv2.line(result, (x1, y1), (x2, y2), (255, 0, 0), 1)  # Blue line
            
            return result
            
        except Exception as e:
            logger.error(f"Error in manual feature match: {e}")
            return None


# Helper functions
def allowed_file(filename):
    """Check if a file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'svg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(img, folder=None):
    """Save OpenCV image to disk and return the filename"""
    if folder is None:
        folder = app.config['RESULTS_FOLDER']
    
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(folder, filename)
    cv2.imwrite(filepath, img)
    
    return filename

def image_to_base64(img):
    """Convert OpenCV image to base64 for embedding in HTML"""
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')


# Flask routes
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/merge', methods=['POST'])
def upload():
    """Handle image upload and processing"""
    try:
        logger.info("Starting image processing request")
        
        # Create a unique session ID if not exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # Create image merger instance
        merger = ImageMerger()
        
        # Check if files were uploaded
        if 'images' not in request.files:
            logger.error("No files were uploaded")
            return jsonify({'success': False, 'message': 'No files uploaded'})
        
        files = request.files.getlist('images')
        logger.info(f"Received {len(files)} files")
        
        if len(files) < 2:
            logger.error("Less than 2 images uploaded")
            return jsonify({'success': False, 'message': 'Please upload at least 2 images'})
        
        # Get parameters
        merge_type = request.form.get('merge_type', 'feature_merge')
        threshold = float(request.form.get('threshold', 0.7))
        use_orb = request.form.get('use_orb', 'false').lower() == 'true'
        alpha = float(request.form.get('alpha', 0.5))
        
        logger.info(f"Processing parameters: merge_type={merge_type}, threshold={threshold}, use_orb={use_orb}, alpha={alpha}")
        
        # Set merger properties
        merger.matches_threshold = threshold
        merger.use_orb = use_orb
        
        # Save uploaded files and add to merger
        uploaded_paths = []
        uploaded_info = []
        
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{session['session_id']}_{i}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                logger.info(f"Saved uploaded file {i+1}: {filename} to {file_path}")
                
                if merger.add_image(file_path):
                    uploaded_paths.append(file_path)
                    uploaded_info.append({
                        'id': i,
                        'name': filename,
                        'path': f"{app.config['UPLOAD_FOLDER']}/{unique_filename}"
                    })
                else:
                    logger.error(f"Failed to add image {filename} to merger")
        
        if len(merger.images) < 2:
            logger.error("Failed to load enough valid images")
            return jsonify({'success': False, 'message': 'Failed to load enough valid images'})
        
        # Process images based on merge type
        result_img = None
        logger.info(f"Starting image processing with merge type: {merge_type}")
        
        if merge_type == 'feature_merge':
            logger.info("Performing feature merge")
            result_img = merger.merge_images()
        elif merge_type == 'feature_aligned_blend':
            logger.info(f"Performing feature aligned blend with alpha={alpha}")
            result_img = merger.feature_aligned_blend(alpha=alpha)
            
        if result_img is None:
            logger.error("Failed to merge images - result is None")
            return jsonify({'success': False, 'message': 'Failed to merge images'})
        
        logger.info(f"Successfully created merged image with shape: {result_img.shape}")
        
        # Save the result
        result_filename = save_image(result_img)
        result_path = f"{app.config['RESULTS_FOLDER']}/{result_filename}"
        logger.info(f"Saved result image to: {result_path}")
        
        # Generate thumbnails for the uploaded images
        thumbnails = []
        for i, img in enumerate(merger.images):
            # Create a thumbnail
            max_dim = 150
            h, w = img.shape[:2]
            scale = min(max_dim / w, max_dim / h)
            new_size = (int(w * scale), int(h * scale))
            thumbnail = cv2.resize(img, new_size)
            
            # Save thumbnail
            thumb_filename = f"thumb_{session['session_id']}_{i}.jpg"
            thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)
            cv2.imwrite(thumb_path, thumbnail)
            
            thumbnails.append({
                'id': i,
                'url': f"/{app.config['UPLOAD_FOLDER']}/{thumb_filename}"
            })
        
        # Generate feature matches image if possible
        matches_url = None
        if len(merger.images) >= 2:
            matches_img = merger.show_feature_matches(0, 1)
            if matches_img is not None:
                matches_filename = f"matches_{session['session_id']}.jpg"
                matches_path = os.path.join(app.config['RESULTS_FOLDER'], matches_filename)
                cv2.imwrite(matches_path, matches_img)
                matches_url = f"/{app.config['RESULTS_FOLDER']}/{matches_filename}"
        
        # Generate preprocessed image of first image
        preproc_url = None
        preprocessed_img = merger.get_preprocessed_image(0)
        if preprocessed_img is not None:
            preproc_filename = f"preproc_{session['session_id']}.jpg"
            preproc_path = os.path.join(app.config['RESULTS_FOLDER'], preproc_filename)
            cv2.imwrite(preproc_path, preprocessed_img)
            preproc_url = f"/{app.config['RESULTS_FOLDER']}/{preproc_filename}"
        
        # Store file paths in session for cleanup later
        if 'uploaded_files' not in session:
            session['uploaded_files'] = []
        session['uploaded_files'].extend(uploaded_paths)
        
        if 'result_files' not in session:
            session['result_files'] = []
        session['result_files'].append(result_path)
        
        # Make sure we return a consistent result path format with leading slash
        return jsonify({
            'success': True,
            'result': f"/{result_path}",
            'result_image': f"/{result_path}",  # Include both formats for compatibility
            'thumbnails': thumbnails,
            'matches_url': matches_url,
            'preprocessed_url': preproc_url,
            'uploaded_count': len(merger.images)
        })
        
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a file from the results folder - handles both path formats"""
    try:
        # Remove leading slash if present
        if filename.startswith('/'):
            filename = filename[1:]
            
        # If path includes results folder, extract just the filename
        if '/' in filename:
            parts = filename.split('/')
            if app.config['RESULTS_FOLDER'] in filename:
                # Extract just the filename from the path
                filename = parts[-1]
        
        logger.info(f"Attempting to download file: {filename} from {app.config['RESULTS_FOLDER']}")
        return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error during file download: {str(e)}")
        return jsonify({'success': False, 'message': f"Error: {str(e)}"}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Remove temporary files from session"""
    try:
        if 'uploaded_files' in session:
            for file_path in session['uploaded_files']:
                if os.path.exists(file_path):
                    os.remove(file_path)
            session.pop('uploaded_files')
        
        if 'result_files' in session:
            for file_path in session['result_files']:
                if os.path.exists(file_path):
                    os.remove(file_path)
            session.pop('result_files')
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon directly"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/enhance_panorama', methods=['POST'])
def enhance_panorama():
    """Apply advanced enhancement to an existing panorama image"""
    try:
        logger.info("Starting panorama enhancement")
        
        if 'image' not in request.files:
            logger.error("No image file provided for enhancement") 
            return jsonify({'success': False, 'message': 'No image uploaded'})

        file = request.files['image']
        
        if not file or not allowed_file(file.filename):
            logger.error("Invalid file provided for enhancement")
            return jsonify({'success': False, 'message': 'Invalid file'})

        # Save the uploaded image temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"enhance_{filename}")
        file.save(filepath)
        logger.info(f"Saved image for enhancement to {filepath}")

        try:
            # Load the image
            img = cv2.imread(filepath)
            if img is None:
                raise ValueError(f"Could not load image: {filename}")

            # Apply a series of enhancements
            logger.info("Applying image enhancements")
            
            # 1. Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
            l, a, b = cv2.split(lab)
            
            # 2. Apply adaptive contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            
            # 3. Merge channels back
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_Lab2BGR)
            
            # 4. Apply intelligent sharpening
            blur = cv2.GaussianBlur(enhanced, (0, 0), 3)
            enhanced = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
            
            # 5. Enhance saturation slightly
            hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            s = cv2.multiply(s, 1.2)  # Increase saturation by 20%
            s = np.clip(s, 0, 255).astype(np.uint8)
            enhanced = cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

            # Save the enhanced result with high quality
            result_filename = f"enhanced_{uuid.uuid4()}.jpg"
            result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
            cv2.imwrite(result_path, enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])
            logger.info(f"Saved enhanced image to {result_path}")

            # Clean up temporary file
            os.remove(filepath)
            
            return jsonify({
                'success': True, 
                'result_image': f"/{app.config['RESULTS_FOLDER']}/{result_filename}",
                'message': 'Image enhanced successfully'
            })

        except Exception as e:
            logger.error(f"Error during image enhancement: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'success': False, 'message': f"Enhancement error: {str(e)}"})
            
    except Exception as e:
        logger.error(f"Error in enhance_panorama route: {str(e)}")
        return jsonify({'success': False, 'message': f"Server error: {str(e)}"})

@app.route('/feature_matches', methods=['POST'])
def show_feature_matches():
    """Display feature matches between uploaded images"""
    try:
        logger.info("Starting feature matches visualization")
        
        if 'images' not in request.files:
            return jsonify({"success": False, "message": "No images uploaded"})

        files = request.files.getlist('images')
        if len(files) < 2:
            return jsonify({"success": False, "message": "Need at least 2 images"})

        # Get parameters
        threshold = float(request.form.get("threshold", 0.7))
        use_orb = request.form.get("use_orb", "false").lower() == "true"

        # Create image merger instance
        merger = ImageMerger()
        merger.matches_threshold = threshold
        merger.use_orb = use_orb
        
        # Load the first two images
        for i, file in enumerate(files[:2]):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"match_{i}_{filename}")
                file.save(filepath)
                
                if not merger.add_image(filepath):
                    return jsonify({"success": False, "message": f"Failed to process image {i+1}"})

        # Generate matches visualization
        matches_img = merger.show_feature_matches(0, 1)
        if matches_img is None:
            return jsonify({"success": False, "message": "Could not find enough matches between images"})

        # Save and return the result
        result_filename = f"matches_{uuid.uuid4()}.jpg"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        cv2.imwrite(result_path, matches_img)
        
        return jsonify({
            "success": True,
            "result_image": f"/{app.config['RESULTS_FOLDER']}/{result_filename}",
            "match_count": len(merger.match_features(
                merger.detect_features(merger.images[0])[1],
                merger.detect_features(merger.images[1])[1]
            ))
        })
        
    except Exception as e:
        logger.error(f"Error in feature matches: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/show_preprocessed', methods=['POST'])
def show_preprocessed():
    """Show preprocessed version of an image with analysis information"""
    try:
        logger.info("Starting preprocessed image visualization")
        
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "No image uploaded"})

        file = request.files['image']
        if not file or not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Invalid image file"})

        # Save the uploaded image
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"preproc_{filename}")
        file.save(filepath)
        
        # Create merger instance and add image
        merger = ImageMerger()
        if not merger.add_image(filepath):
            return jsonify({"success": False, "message": "Failed to process image"})
        
        # Get the original image
        img = merger.images[0]
        height, width = img.shape[:2]
        
        # Analyze the image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        is_night = avg_brightness < 100
        
        # Calculate contrast
        p5 = np.percentile(gray, 5)
        p95 = np.percentile(gray, 95)
        contrast = (p95 - p5) / 255.0
        
        # Determine processing steps and recommendations
        processing_steps = []
        recommendations = []
        
        if is_night:
            processing_steps.append("Night image enhancement")
            processing_steps.append("CLAHE contrast enhancement")
            processing_steps.append("Edge enhancement")
            recommendations.append("Consider using ORB detector for better feature detection")
        else:
            processing_steps.append("Standard preprocessing")
            processing_steps.append("CLAHE contrast enhancement")
            processing_steps.append("Noise reduction")
        
        # Generate preprocessed view
        preprocessed_img = merger.get_preprocessed_image(0)
        if preprocessed_img is None:
            return jsonify({"success": False, "message": "Failed to generate preprocessed view"})
        
        # Save and return the result
        result_filename = f"preprocessed_{uuid.uuid4()}.jpg"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        cv2.imwrite(result_path, preprocessed_img)
        
        return jsonify({
            "success": True,
            "result_image": f"/{app.config['RESULTS_FOLDER']}/{result_filename}",
            "is_night": bool(is_night),
            "brightness_level": f"{avg_brightness:.1f}",
            "contrast_level": f"{contrast:.2f}",
            "width": width,
            "height": height,
            "processing_steps": ", ".join(processing_steps),
            "recommendations": ", ".join(recommendations)
        })
        
    except Exception as e:
        logger.error(f"Error in show preprocessed: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/manual_match', methods=['POST'])
def manual_match():
    """Process images with manually specified feature matches"""
    try:
        logger.info("Starting manual feature matching")
        
        # Get session ID or create new one
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            
        # Parse request data
        data = request.json
        if not data or 'matches' not in data or 'image_paths' not in data:
            return jsonify({"success": False, "message": "Missing required data"})
            
        # Get manual matches and image paths
        manual_matches = data['matches']
        image_paths = data['image_paths']
        
        if len(manual_matches) < 4:
            return jsonify({"success": False, "message": "Need at least 4 point pairs"})
            
        if len(image_paths) < 2:
            return jsonify({"success": False, "message": "Need at least 2 images"})
        
        # Create merger and add images
        merger = ImageMerger()
        for path in image_paths:
            # Strip leading slash if present
            if path.startswith('/'):
                path = path[1:]
            if not merger.add_image(path):
                return jsonify({"success": False, "message": f"Failed to load image: {path}"})
                
        # Process with manual matches
        result_img = merger.manual_feature_match(manual_matches)
        if result_img is None:
            return jsonify({"success": False, "message": "Failed to process with manual matches"})
            
        # Save the result
        result_filename = f"manual_match_{uuid.uuid4()}.jpg"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        cv2.imwrite(result_path, result_img)
        
        return jsonify({
            "success": True,
            "result_image": f"/{app.config['RESULTS_FOLDER']}/{result_filename}",
            "message": f"Successfully processed with {len(manual_matches)} manual matches"
        })
        
    except Exception as e:
        logger.error(f"Error in manual matching: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/process_manual_points', methods=['POST'])
def process_manual_points():
    """Process images with manually selected feature points"""
    try:
        logger.info("Starting manual point processing")
        
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({"success": False, "message": "Missing image files"})
            
        # Get the uploaded images
        file1 = request.files['image1']
        file2 = request.files['image2']
        
        # Get the point pairs
        if 'point_pairs' not in request.form:
            return jsonify({"success": False, "message": "No point pairs provided"})
            
        try:
            point_pairs = json.loads(request.form['point_pairs'])
        except:
            return jsonify({"success": False, "message": "Invalid point pairs format"})
            
        if len(point_pairs) < 4:
            return jsonify({"success": False, "message": "At least 4 point pairs are required"})
            
        # Generate unique filenames and save the images
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            
        filename1 = f"manual1_{session['session_id']}.jpg"
        filename2 = f"manual2_{session['session_id']}.jpg"
        
        filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
        filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
        
        file1.save(filepath1)
        file2.save(filepath2)
        
        # Load the images with OpenCV
        img1 = cv2.imread(filepath1)
        img2 = cv2.imread(filepath2)
        
        if img1 is None or img2 is None:
            return jsonify({"success": False, "message": "Failed to load images"})
            
        # Prepare source and destination points
        src_pts = np.float32([[pair['img1']['x'] * img1.shape[1], pair['img1']['y'] * img1.shape[0]] for pair in point_pairs]).reshape(-1, 1, 2)
        dst_pts = np.float32([[pair['img2']['x'] * img2.shape[1], pair['img2']['y'] * img2.shape[0]] for pair in point_pairs]).reshape(-1, 1, 2)
        
        # Find homography
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is None:
            return jsonify({"success": False, "message": "Could not compute homography"})
            
        # Calculate output dimensions
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]
        
        corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
        corners2 = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
        
        # Apply homography to img1 corners
        corners1_transformed = cv2.perspectiveTransform(corners1, H)
        
        # Find bounding box
        all_corners = np.concatenate((corners2, corners1_transformed), axis=0)
        x_min, y_min = np.int32(all_corners.min(axis=0).ravel() - 0.5)
        x_max, y_max = np.int32(all_corners.max(axis=0).ravel() + 0.5)
        
        # Create translation matrix
        translation = [-x_min, -y_min]
        T = np.array([
            [1, 0, translation[0]],
            [0, 1, translation[1]],
            [0, 0, 1]
        ])
        
        # Define output size
        output_size = (x_max - x_min, y_max - y_min)
        
        # Warp images
        img1_warped = cv2.warpPerspective(img1, T.dot(H), output_size)
        
        # Create a blank canvas for img2
        img2_placed = np.zeros((output_size[1], output_size[0], 3), dtype=np.uint8)
        
        # Place img2 on the canvas with the translation offset
        y_off, x_off = max(0, translation[1]), max(0, translation[0])
        img2_placed[y_off:y_off+h2, x_off:x_off+w2] = img2
        
        # Create masks for blending
        mask1 = (img1_warped != 0).astype(np.float32)
        mask2 = (img2_placed != 0).astype(np.float32)
        
        # Blend the images
        result = np.zeros_like(img1_warped, dtype=np.float32)
        for c in range(3):
            result[:,:,c] = (
                img1_warped[:,:,c] * mask1[:,:,c] +
                img2_placed[:,:,c] * mask2[:,:,c]
            ) / (mask1[:,:,c] + mask2[:,:,c] + 1e-10)
        
        result = result.astype(np.uint8)
        
        # Draw the manually selected points on the result
        for i, pair in enumerate(point_pairs):
            # Transform img1 points
            pt1 = np.array([[pair['img1']['x'] * img1.shape[1], pair['img1']['y'] * img1.shape[0]]], dtype=np.float32).reshape(-1, 1, 2)
            pt1_transformed = cv2.perspectiveTransform(pt1, T.dot(H))[0][0].astype(int)
            
            # Get img2 points with offset
            pt2 = (int(pair['img2']['x'] * img2.shape[1] + x_off), int(pair['img2']['y'] * img2.shape[0] + y_off))
            
            # Draw circles and lines
            color = (0, 0, 255)  # Red for img1
            cv2.circle(result, tuple(pt1_transformed), 5, color, -1)
            cv2.putText(result, str(i+1), tuple(pt1_transformed), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            color = (0, 255, 0)  # Green for img2
            cv2.circle(result, pt2, 5, color, -1)
            cv2.putText(result, str(i+1), pt2, 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw line connecting points
            cv2.line(result, tuple(pt1_transformed), pt2, (255, 0, 0), 1)
        
        # Save the result
        result_filename = f"manual_result_{uuid.uuid4()}.jpg"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        cv2.imwrite(result_path, result)
        
        return jsonify({
            "success": True,
            "result_image": f"/{app.config['RESULTS_FOLDER']}/{result_filename}",
            "message": f"Successfully processed with {len(point_pairs)} manual points"
        })
        
    except Exception as e:
        logger.error(f"Error in manual point processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/delete_files', methods=['POST'])
def delete_files():
    """Delete multiple files from the uploads or results folder"""
    try:
        file_paths = request.json.get('file_paths', [])
        if not file_paths:
            return jsonify({"success": False, "message": "No files selected"})
        
        results = {
            "success": True,
            "deleted": [],
            "failed": []
        }
        
        for file_path in file_paths:
            try:
                # Remove leading slash if present
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                
                # Security check
                if not (file_path.startswith(app.config['UPLOAD_FOLDER']) or 
                        file_path.startswith(app.config['RESULTS_FOLDER']) or
                        file_path.startswith(app.config['TEMP_FOLDER'])):
                    results["failed"].append({"path": file_path, "error": "Invalid path"})
                    continue
                
                # Check if file exists
                if not os.path.exists(file_path):
                    results["failed"].append({"path": file_path, "error": "File not found"})
                    continue
                
                # Delete the file
                os.remove(file_path)
                results["deleted"].append(file_path)
                logger.info(f"Deleted file: {file_path}")
                
            except Exception as e:
                results["failed"].append({"path": file_path, "error": str(e)})
        
        if not results["deleted"] and results["failed"]:
            results["success"] = False
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in batch deletion: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}",
            "deleted": [],
            "failed": []
        })

@app.route('/view_files')
def view_files():
    """View files in uploads and results folders"""
    try:
        # Get files from uploads folder
        uploads_path = app.config['UPLOAD_FOLDER']
        results_path = app.config['RESULTS_FOLDER']
        
        uploads = []
        results = []
        
        # List uploads
        if os.path.exists(uploads_path):
            for file in os.listdir(uploads_path):
                file_path = os.path.join(uploads_path, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    modified = os.path.getmtime(file_path)
                    uploads.append({
                        'name': file,
                        'path': f"/{uploads_path}/{file}",
                        'size': size,
                        'modified': modified
                    })
        
        # List results
        if os.path.exists(results_path):
            for file in os.listdir(results_path):
                file_path = os.path.join(results_path, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    modified = os.path.getmtime(file_path)
                    results.append({
                        'name': file,
                        'path': f"/{results_path}/{file}",
                        'size': size,
                        'modified': modified
                    })
        
        # Sort files by modification time (newest first)
        uploads.sort(key=lambda x: x['modified'], reverse=True)
        results.sort(key=lambda x: x['modified'], reverse=True)
        
        return render_template('view_files.html', uploads=uploads, results=results)
        
    except Exception as e:
        logger.error(f"Error viewing files: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/maintenance')
def maintenance():
    """Render the maintenance page."""
    return render_template('maintenance.html')

@app.route('/run_tests')
def run_tests():
    """Run all tests and return results."""
    from test_app import main as run_test_suite
    try:
        success = run_test_suite()
        # Get the latest test results file
        results_dir = Path('.')
        test_files = list(results_dir.glob('test_results_*.json'))
        if not test_files:
            return jsonify({'success': False, 'error': 'No test results found'})
        
        latest_file = max(test_files, key=lambda x: x.stat().st_mtime)
        with open(latest_file) as f:
            results = json.load(f)
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/run_cleanup')
def run_cleanup():
    """Run cleanup operations on the results folder."""
    try:
        results_dir = Path(app.config['RESULTS_FOLDER'])
        uploads_dir = Path(app.config['UPLOAD_FOLDER'])
        moved = 0
        errors = 0
        initial_size = get_directory_size(results_dir) + get_directory_size(uploads_dir)

        # Create category folders if they don't exist
        categories = ['feature_merge', 'blend', 'side_by_side', 'enhanced', 'matches', 'preprocessed', 'archive']
        for category in categories:
            category_dir = results_dir / category
            category_dir.mkdir(exist_ok=True)

        # Move files to appropriate folders
        for file in results_dir.glob('*.*'):
            if file.is_file():
                try:
                    if file.name.startswith('feature_'):
                        shutil.move(str(file), str(results_dir / 'feature_merge' / file.name))
                        moved += 1
                    elif file.name.startswith('blend_'):
                        shutil.move(str(file), str(results_dir / 'blend' / file.name))
                        moved += 1
                    elif file.name.startswith('sidebyside_'):
                        shutil.move(str(file), str(results_dir / 'side_by_side' / file.name))
                        moved += 1
                    elif file.name.startswith('enhanced_'):
                        shutil.move(str(file), str(results_dir / 'enhanced' / file.name))
                        moved += 1
                    elif file.name.startswith('matches_'):
                        shutil.move(str(file), str(results_dir / 'matches' / file.name))
                        moved += 1
                    elif file.name.startswith('preprocessed_'):
                        shutil.move(str(file), str(results_dir / 'preprocessed' / file.name))
                        moved += 1
                    else:
                        shutil.move(str(file), str(results_dir / 'archive' / file.name))
                        moved += 1
                except Exception:
                    errors += 1

        # Calculate space freed
        final_size = get_directory_size(results_dir) + get_directory_size(uploads_dir)
        freed = (initial_size - final_size) / (1024 * 1024)  # Convert to MB

        # Get current storage usage
        storage = get_storage_usage()

        return jsonify({
            'success': True,
            'moved': moved,
            'errors': errors,
            'freed': round(freed, 2),
            'storage': storage
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/storage_usage')
def storage_usage():
    """Get current storage usage statistics."""
    return jsonify(get_storage_usage())

def get_directory_size(directory):
    """Calculate total size of a directory in bytes."""
    total = 0
    for entry in Path(directory).rglob('*'):
        if entry.is_file():
            total += entry.stat().st_size
    return total

def get_storage_usage():
    """Get storage usage statistics."""
    results_dir = Path(app.config['RESULTS_FOLDER'])
    uploads_dir = Path(app.config['UPLOAD_FOLDER'])
    
    used = (get_directory_size(results_dir) + get_directory_size(uploads_dir)) / (1024 * 1024)  # Convert to MB
    total = 1000  # Set limit to 1GB
    
    return {
        'used': round(used, 2),
        'total': total
    }

if __name__ == '__main__':
    app.run(debug=True)