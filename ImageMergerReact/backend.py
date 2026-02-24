import os
import cv2
import numpy as np
import uuid
import base64
import tempfile
import shutil
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
import logging
import json
from datetime import datetime
from pathlib import Path
import requests
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join('static', 'results')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['TEMP_FOLDER'] = tempfile.mkdtemp()

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Helper functions (allowed_file, save_image, etc.)
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'svg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(img, folder=None, format='png', quality=95):
    if folder is None:
        folder = app.config['RESULTS_FOLDER']
    
    ext = format.lower()
    if ext == 'jpg' or ext == 'jpeg':
        ext = 'jpg'
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(folder, filename)
        cv2.imwrite(filepath, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    elif ext == 'webp':
        filename = f"{uuid.uuid4()}.webp"
        filepath = os.path.join(folder, filename)
        cv2.imwrite(filepath, img, [cv2.IMWRITE_WEBP_QUALITY, quality])
    else:  # PNG default
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(folder, filename)
        cv2.imwrite(filepath, img)
    return filename

def crop_result(img):
    """Remove black borders from result image."""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Find non-zero pixels
        coords = cv2.findNonZero(gray)
        if coords is None:
            return img
        # Get bounding box
        x, y, w, h = cv2.boundingRect(coords)
        # Crop the image
        cropped = img[y:y+h, x:x+w]
        return cropped
    except Exception as e:
        logger.error(f"Error cropping image: {e}")
        return img

class ImageMerger:
    def __init__(self, feature_count=1000, match_ratio=0.75, ransac_threshold=5.0, min_matches=4):
        self.feature_count = feature_count
        self.match_ratio = match_ratio
        self.ransac_threshold = ransac_threshold
        self.min_matches = min_matches
        self.sift = cv2.SIFT_create(nfeatures=feature_count)
        self.orb = cv2.ORB_create(nfeatures=feature_count)
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
                    if m.distance < self.match_ratio * n.distance:
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
            # For SIFT, use L2 distance with Lowe's ratio test
            matches = self.matcher.knnMatch(desc1, desc2, k=2)
            good_matches = []
            for m, n in matches:
                if m.distance < self.match_ratio * n.distance:
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

        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.ransac_threshold)
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
                    Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]], dtype=np.float32)

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
            # Ensure image is in BGR format
            if len(img.shape) == 2:  # If grayscale
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif len(img.shape) == 3 and img.shape[2] == 4:  # If RGBA
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif len(img.shape) == 3 and img.shape[2] == 1:  # If single channel
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            
            # Convert to grayscale for analysis
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
            
            if len(good_matches) < self.min_matches:
                # Not enough matches for alignment, fall back to simple overlay
                logger.warning(f"Only {len(good_matches)} matches found (need {self.min_matches}). Using simple overlay.")
                return self.do_simple_blend(alpha)
            
            # STEP 2: Find transformation between images
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Try to find homography
            try:
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.ransac_threshold)
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
            ], dtype=np.float32)
            
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

    def multi_band_blend(self, alpha=0.5, num_bands=5):
        """Multi-band blending using Laplacian pyramids for seamless blending."""
        try:
            if len(self.images) < 2:
                return None
            
            img1 = self.images[0].copy()
            img2 = self.images[1].copy()
            
            # Find features and alignment
            kp1, desc1 = self.detect_features(img1)
            kp2, desc2 = self.detect_features(img2)
            good_matches = self.match_features(desc1, desc2)
            
            if len(good_matches) < self.min_matches:
                logger.warning(f"Only {len(good_matches)} matches found. Using simple overlay.")
                return self.do_simple_blend(alpha)
            
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.ransac_threshold)
            if H is None:
                return self.do_simple_blend(alpha)
            
            # Warp images
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            corners1 = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
            corners1_transformed = cv2.perspectiveTransform(corners1, H)
            all_corners = np.concatenate((np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2), corners1_transformed), axis=0)
            x_min, y_min = np.int32(all_corners.min(axis=0).ravel() - 0.5)
            x_max, y_max = np.int32(all_corners.max(axis=0).ravel() + 0.5)
            offset = [-x_min, -y_min]
            translation_matrix = np.array([[1, 0, offset[0]], [0, 1, offset[1]], [0, 0, 1]], dtype=np.float32)
            output_size = (x_max - x_min, y_max - y_min)
            
            warped_img1 = cv2.warpPerspective(img1, translation_matrix.dot(H), output_size)
            expanded_img2 = np.zeros_like(warped_img1)
            expanded_img2[offset[1]:offset[1]+h2, offset[0]:offset[0]+w2] = img2
            
            # Create mask for blending region
            mask1 = np.zeros((output_size[1], output_size[0]), dtype=np.float32)
            mask1[warped_img1[:,:,0] > 0] = 1.0
            mask2 = np.zeros((output_size[1], output_size[0]), dtype=np.float32)
            mask2[offset[1]:offset[1]+h2, offset[0]:offset[0]+w2] = 1.0
            
            # Simple multi-band blending (simplified version)
            # For full implementation, would use Laplacian pyramids
            overlap = mask1 * mask2
            mask1_blend = mask1 - overlap * alpha
            mask2_blend = mask2 - overlap * (1 - alpha)
            
            result = np.zeros_like(warped_img1, dtype=np.float32)
            for c in range(3):
                result[:,:,c] = warped_img1[:,:,c].astype(np.float32) * mask1_blend + expanded_img2[:,:,c].astype(np.float32) * mask2_blend
            result = np.clip(result, 0, 255).astype(np.uint8)
            
            # Add border and title
            border_size = 20
            result_with_border = cv2.copyMakeBorder(result, border_size, border_size, border_size, border_size, cv2.BORDER_CONSTANT, value=[0, 0, 0])
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = f"Multi-Band Blend (Alpha: {alpha:.2f}, Matches: {len(good_matches)})"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (result_with_border.shape[1] - text_size[0]) // 2
            cv2.putText(result_with_border, title, (text_x, border_size - 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return result_with_border
        except Exception as e:
            logger.error(f"Error during multi-band blend: {str(e)}")
            return self.do_simple_blend(alpha)

    def gradient_domain_blend(self, alpha=0.5):
        """Gradient domain blending for better seam handling."""
        try:
            if len(self.images) < 2:
                return None
            
            # For now, use feature-aligned blend as base
            # Full gradient domain blending requires solving Poisson equation
            # This is a simplified version
            result = self.feature_aligned_blend(alpha)
            if result is None:
                return None
            
            # Apply additional smoothing at seams
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            kernel = np.ones((3,3), np.uint8)
            edges_dilated = cv2.dilate(edges, kernel, iterations=1)
            mask = 1.0 - (edges_dilated.astype(np.float32) / 255.0 * 0.3)
            
            result_smooth = result.astype(np.float32)
            for c in range(3):
                result_smooth[:,:,c] *= mask
            result_smooth = np.clip(result_smooth, 0, 255).astype(np.uint8)
            
            # Update title
            border_size = 20
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = "Gradient Domain Blend"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (result_smooth.shape[1] - text_size[0]) // 2
            cv2.putText(result_smooth, title, (text_x, border_size - 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return result_smooth
        except Exception as e:
            logger.error(f"Error during gradient domain blend: {str(e)}")
            return self.do_simple_blend(alpha)

    def panorama_stitch(self, alpha=0.5):
        """Panorama stitching mode."""
        try:
            # For panorama, use feature-aligned blend with cylindrical projection option
            # Simplified version - full panorama would use cylindrical/spherical warping
            result = self.feature_aligned_blend(alpha)
            if result is None:
                return None
            
            # Update title
            border_size = 20
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = "Panorama Stitch"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (result.shape[1] - text_size[0]) // 2
            cv2.putText(result, title, (text_x, border_size - 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return result
        except Exception as e:
            logger.error(f"Error during panorama stitch: {str(e)}")
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
            Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]], dtype=np.float32)
            
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

# Shared prompt and JSON extraction for AI config adjustment (Ollama and Gemini)
AI_CONFIG_SYSTEM_PROMPT = """You are a professional image editor. You are to help adjust the merge config based on the user's feedback.

Return ONLY a valid JSON dictionary with the adjusted configuration. Do not include any explanation or markdown formatting, just the JSON dictionary.

The configuration dictionary should include these keys:
- threshold (float, 0.0-1.0)
- alpha (float, 0.0-1.0)
- blend_mode (string: 'feature_aligned', 'multi_band', 'gradient_domain', 'simple_overlay', 'panorama')
- use_orb (boolean)
- ransac_threshold (float, 1.0-10.0)
- feature_count (integer, 500-5000)
- match_ratio (float, 0.5-0.9)
- min_matches (integer, 4-20)
- auto_crop (boolean)
- output_size (string: 'original', 'fit_screen', 'custom')
- output_quality (integer, 1-100)
- output_format (string: 'png', 'jpg', 'webp')
"""

def _build_config_user_prompt(prompt_text, merge_config):
    return f"""
Current merge configuration:
{json.dumps(merge_config, indent=2)}

User's feedback:
{prompt_text}

Return the adjusted configuration as a JSON dictionary only.
"""

def _extract_config_json(response_text, merge_config_fallback, log_prefix="AI"):
    """Extract and parse JSON config from LLM response text. Returns merge_config_fallback on parse failure."""
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        json_str = json_match.group(0) if json_match else response_text.strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"{log_prefix}: Failed to parse JSON from response: {e}")
        logger.error(f"Response text: {response_text}")
        return merge_config_fallback


class OllamaHelper:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = "llama3.2"
        self.ollama_temperature = 0.5
        self.ollama_max_tokens = 1024

    def ollama_help(self, prompt, merge_config):
        user_prompt = _build_config_user_prompt(prompt, merge_config)
        full_prompt = f"{AI_CONFIG_SYSTEM_PROMPT}\n\n{user_prompt}"
        url = f"{self.ollama_url}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.ollama_model,
            "prompt": full_prompt,
            "temperature": self.ollama_temperature,
            "max_tokens": self.ollama_max_tokens,
            "stream": False
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            response_text = result.get('response', '')
            return _extract_config_json(response_text, merge_config, log_prefix="Ollama")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ollama_help: {e}")
            raise


class GeminiHelper:
    """Uses Google Gemini (optionally with vision) to suggest merge config from user feedback and optionally the merged image."""
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        self.model_name = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
        self.temperature = 0.5
        self.max_tokens = 1024

    def gemini_help(self, feedback, merge_config, image_bytes=None):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required for Gemini.")
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai is required for Gemini. Install with: pip install google-generativeai")
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        user_prompt = _build_config_user_prompt(feedback, merge_config)
        full_text = f"{AI_CONFIG_SYSTEM_PROMPT}\n\n{user_prompt}"
        if image_bytes:
            full_text = "Look at the merged image below, then consider the user's feedback and current config. " + full_text
        try:
            if image_bytes:
                image_part = {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                }
                response = model.generate_content(
                    [full_text, image_part],
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                    )
                )
            else:
                response = model.generate_content(
                    full_text,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                    )
                )
            response_text = (response.text or "") if hasattr(response, "text") else ""
            return _extract_config_json(response_text, merge_config, log_prefix="Gemini")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

# Example endpoint for file listing
@app.route('/api/view_files')
def api_view_files():
    try:
        uploads_path = app.config['UPLOAD_FOLDER']
        results_path = app.config['RESULTS_FOLDER']
        uploads = []
        results = []
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
        uploads.sort(key=lambda x: x['modified'], reverse=True)
        results.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'uploads': uploads, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/scan', methods=['POST'])
def scan():
    """Scan uploaded images and return match counts for all pairs."""
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'message': 'No images uploaded'})
        files = request.files.getlist('images')
        if len(files) < 2:
            return jsonify({'success': False, 'message': 'Please upload at least 2 images'})
        threshold = float(request.form.get('threshold', 0.7))
        use_orb = request.form.get('use_orb', 'false').lower() == 'true'
        min_matches = int(request.form.get('min_matches', 4))
        merger = ImageMerger()
        merger.matches_threshold = threshold
        merger.match_ratio = threshold
        merger.use_orb = use_orb
        image_names = []
        original_indices = []
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"scan_{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                if merger.add_image(file_path):
                    image_names.append(filename)
                    original_indices.append(i)
        if len(merger.images) < 2:
            return jsonify({'success': False, 'message': 'Failed to load enough valid images'})
        pairs = []
        pair_set = set()  # (min_oi, max_oi) in original index space for mergeable pairs
        n = len(merger.images)
        for i in range(n):
            for j in range(i + 1, n):
                kp1, desc1 = merger.detect_features(merger.images[i])
                kp2, desc2 = merger.detect_features(merger.images[j])
                good_matches = merger.match_features(desc1, desc2)
                match_count = len(good_matches)
                if match_count >= min_matches:
                    oi, oj = original_indices[i], original_indices[j]
                    pairs.append({
                        'indices': [oi, oj],
                        'match_count': match_count
                    })
                    pair_set.add((min(oi, oj), max(oi, oj)))
        # Consecutive mergeable groups (3+ images) in original index space
        num_orig = len(files)
        groups = []
        start = 0
        while start <= num_orig - 3:
            end = start
            while end + 1 < num_orig and (end, end + 1) in pair_set:
                end += 1
            if end - start + 1 >= 3:
                groups.append({'indices': list(range(start, end + 1))})
            start = end + 1
        return jsonify({
            'success': True,
            'pairs': pairs,
            'groups': groups,
            'image_names': image_names
        })
    except Exception as e:
        logger.error(f"Error in scan: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/merge', methods=['POST'])
def merge():
    import time
    start_time = time.time()
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'message': 'No files uploaded'})
        files = request.files.getlist('images')
        if len(files) < 2:
            return jsonify({'success': False, 'message': 'Please upload at least 2 images'})
        
        # Get parameters
        threshold = float(request.form.get('threshold', 0.7))
        use_orb = request.form.get('use_orb', 'false').lower() == 'true'
        alpha = float(request.form.get('alpha', 0.5))
        blend_mode = request.form.get('blend_mode', 'feature_aligned')
        ransac_threshold = float(request.form.get('ransac_threshold', 5.0))
        feature_count = int(request.form.get('feature_count', 1000))
        match_ratio = float(request.form.get('match_ratio', 0.75))
        min_matches = int(request.form.get('min_matches', 4))
        auto_crop = request.form.get('auto_crop', 'false').lower() == 'true'
        output_size = request.form.get('output_size', 'original')
        output_quality = int(request.form.get('output_quality', 95))
        output_format = request.form.get('output_format', 'png')
        
        # Create merger with parameters
        merger = ImageMerger(
            feature_count=feature_count,
            match_ratio=match_ratio,
            ransac_threshold=ransac_threshold,
            min_matches=min_matches
        )
        merger.matches_threshold = threshold
        merger.use_orb = use_orb
        
        uploaded_paths = []
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                merger.add_image(file_path)
                uploaded_paths.append(file_path)
        
        if len(merger.images) < 2:
            return jsonify({'success': False, 'message': 'Failed to load enough valid images'})
        
        # Call appropriate blend method
        matches_count = 0
        if len(merger.images) > 2:
            # Sequential panorama-style merge for 3+ images
            result_img = merger.merge_images()
            try:
                kp1, desc1 = merger.detect_features(merger.images[0])
                kp2, desc2 = merger.detect_features(merger.images[1])
                matches = merger.match_features(desc1, desc2)
                matches_count = len(matches)
            except Exception:
                pass
        elif blend_mode == 'multi_band':
            result_img = merger.multi_band_blend(alpha=alpha)
        elif blend_mode == 'gradient_domain':
            result_img = merger.gradient_domain_blend(alpha=alpha)
        elif blend_mode == 'panorama':
            result_img = merger.panorama_stitch(alpha=alpha)
        elif blend_mode == 'simple_overlay':
            result_img = merger.do_simple_blend(alpha=alpha)
        else:  # feature_aligned (default)
            result_img = merger.feature_aligned_blend(alpha=alpha)
            # Try to get match count from feature detection
            try:
                kp1, desc1 = merger.detect_features(merger.images[0])
                kp2, desc2 = merger.detect_features(merger.images[1])
                matches = merger.match_features(desc1, desc2)
                matches_count = len(matches)
            except Exception:
                pass
        
        if result_img is None:
            return jsonify({'success': False, 'message': 'Failed to merge images'})
        
        # Apply auto crop if requested
        if auto_crop:
            result_img = crop_result(result_img)
        
        # Handle output size (for now, just original - custom size can be added later)
        if output_size == 'fit_screen':
            # Resize to fit common screen sizes (simplified)
            max_dimension = 1920
            h, w = result_img.shape[:2]
            if max(h, w) > max_dimension:
                scale = max_dimension / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                result_img = cv2.resize(result_img, (new_w, new_h))
        
        processing_time = time.time() - start_time
        result_filename = save_image(result_img, format=output_format, quality=output_quality)
        result_path = f"/static/results/{result_filename}"
        
        return jsonify({
            'success': True,
            'result_image': result_path,
            'matches': matches_count if matches_count > 0 else None,
            'processing_time': processing_time
        })
    except Exception as e:
        logger.error(f"Error in merge: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/run_tests')
def run_tests():
    # Dummy implementation for now
    # Replace with your real test logic
    try:
        # Simulate test results
        results = [
            {'name': 'Test 1', 'success': True, 'duration': 1.2},
            {'name': 'Test 2', 'success': False, 'duration': 0.8, 'error': 'Some error'},
        ]
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/storage_info')
def storage_info():
    """Return storage usage without running cleanup. used/total in MB."""
    try:
        total, used, free = shutil.disk_usage(os.path.abspath('.'))
        mb = 1024 * 1024
        storage = {'used': round(used / mb, 2), 'total': round(total / mb, 2)}
        return jsonify({'success': True, 'storage': storage})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/run_cleanup')
def run_cleanup():
    # Dummy implementation for now
    # Replace with your real cleanup logic
    try:
        moved = 5
        errors = 0
        freed = 12.3
        total, used, _ = shutil.disk_usage(os.path.abspath('.'))
        mb = 1024 * 1024
        storage = {'used': round(used / mb, 2), 'total': round(total / mb, 2)}
        return jsonify({'success': True, 'moved': moved, 'errors': errors, 'freed': freed, 'storage': storage})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_files', methods=['POST'])
def delete_files():
    try:
        file_paths = request.json.get('file_paths', [])
        deleted = []
        failed = []
        for file_path in file_paths:
            try:
                # Remove leading slash if present
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted.append(file_path)
                else:
                    failed.append({'path': file_path, 'error': 'File not found'})
            except Exception as e:
                failed.append({'path': file_path, 'error': str(e)})
        return jsonify({'success': True, 'deleted': deleted, 'failed': failed})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/static/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/results/<filename>')
def serve_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

@app.route('/manual_match', methods=['POST'])
def manual_match():
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'message': 'No files uploaded'})
        files = request.files.getlist('images')
        if len(files) < 2:
            return jsonify({'success': False, 'message': 'Please upload at least 2 images'})
        # Try multi-step manual matches first
        multi_manual_matches = request.form.get('multi_manual_matches')
        if multi_manual_matches:
            multi_manual_matches = json.loads(multi_manual_matches)
            if len(multi_manual_matches) != len(files) - 1:
                return jsonify({'success': False, 'message': 'Number of match sets must be N-1 for N images'})
            # Load all images
            merger = ImageMerger(feature_count=1000, match_ratio=0.75, ransac_threshold=5.0, min_matches=4)
            image_paths = []
            for i, file in enumerate(files):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    image_paths.append(file_path)
            # Start with first image
            base_img = cv2.imread(image_paths[0])
            for idx, matches in enumerate(multi_manual_matches):
                next_img = cv2.imread(image_paths[idx + 1])
                if base_img is None or next_img is None:
                    return jsonify({'success': False, 'message': f'Failed to load image for step {idx+1}'})
                if len(matches) < 4:
                    return jsonify({'success': False, 'message': f'At least 4 matching points required for step {idx+1}'})
                # Use manual_feature_match logic for this pair
                temp_merger = ImageMerger(feature_count=1000, match_ratio=0.75, ransac_threshold=5.0, min_matches=4)
                temp_merger.images = [base_img, next_img]
                result_img = temp_merger.manual_feature_match(matches)
                if result_img is None:
                    return jsonify({'success': False, 'message': f'Failed to merge images at step {idx+1}'})
                base_img = result_img
            result_filename = save_image(base_img)
            result_path = f"/static/results/{result_filename}"
            return jsonify({'success': True, 'result_image': result_path})
        # Fallback: single pair (legacy)
        manual_matches = json.loads(request.form.get('manual_matches', '[]'))
        if len(manual_matches) < 4:
            return jsonify({'success': False, 'message': 'At least 4 matching points are required'})
        merger = ImageMerger(feature_count=1000, match_ratio=0.75, ransac_threshold=5.0, min_matches=4)
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                merger.add_image(file_path)
        if len(merger.images) < 2:
            return jsonify({'success': False, 'message': 'Failed to load enough valid images'})
        result_img = merger.manual_feature_match(manual_matches)
        if result_img is None:
            return jsonify({'success': False, 'message': 'Failed to merge images with manual features'})
        result_filename = save_image(result_img)
        result_path = f"/static/results/{result_filename}"
        return jsonify({'success': True, 'result_image': result_path})
    except Exception as e:
        logger.error(f"Error in manual_match: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

def _resolve_result_image_to_bytes(result_image_value, results_folder):
    """Resolve result_image (path or filename) to image bytes. Returns (bytes or None, error_message or None)."""
    if not result_image_value or not isinstance(result_image_value, str):
        return None, None
    s = result_image_value.strip()
    if not s:
        return None, None
    # Accept "/static/results/xxx.png" or "xxx.png"
    if s.startswith("/"):
        s = s.lstrip("/")
    if "results" in s and (s.startswith("static/") or s.startswith("results/")):
        parts = s.replace("\\", "/").split("/")
        filename = parts[-1] if parts else s
    else:
        filename = s
    file_path = os.path.join(results_folder, filename)
    if not os.path.isfile(file_path):
        return None, "Result image file not found. Please merge an image first so Gemini can analyze it."
    try:
        with open(file_path, "rb") as f:
            return f.read(), None
    except Exception as e:
        logger.error(f"Failed to read result image: {e}")
        return None, "Could not read the result image file."


@app.route('/adjust_config', methods=['POST'])
def adjust_config():
    """Adjust merge configuration based on user feedback using Ollama or Gemini (vision)."""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
        
        feedback = data.get('feedback', '').strip()
        merge_config = data.get('merge_config', {})
        result_image = data.get('result_image')
        
        if not feedback:
            return jsonify({'success': False, 'message': 'Feedback is required'})
        
        if not merge_config:
            return jsonify({'success': False, 'message': 'Merge configuration is required'})
        
        # Validate merge_config has required keys
        required_keys = [
            'threshold', 'alpha', 'blend_mode', 'use_orb', 'ransac_threshold',
            'feature_count', 'match_ratio', 'min_matches', 'auto_crop',
            'output_size', 'output_quality', 'output_format'
        ]
        missing_keys = [key for key in required_keys if key not in merge_config]
        if missing_keys:
            return jsonify({
                'success': False,
                'message': f'Missing required config keys: {", ".join(missing_keys)}'
            })
        
        ai_provider = (os.environ.get('AI_PROVIDER') or 'ollama').strip().lower()
        image_bytes = None
        if ai_provider == 'gemini':
            image_bytes, img_error = _resolve_result_image_to_bytes(result_image, app.config['RESULTS_FOLDER'])
            if img_error:
                return jsonify({'success': False, 'message': img_error})
            if not image_bytes:
                return jsonify({
                    'success': False,
                    'message': 'Please merge an image first so Gemini can analyze it. Send result_image with the merged result path.'
                })
        
        if ai_provider == 'gemini':
            try:
                gemini_helper = GeminiHelper()
                adjusted_config = gemini_helper.gemini_help(feedback, merge_config, image_bytes=image_bytes)
            except ValueError as e:
                return jsonify({'success': False, 'message': str(e)})
            except ImportError as e:
                return jsonify({'success': False, 'message': str(e)})
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return jsonify({'success': False, 'message': f'Gemini error: {str(e)}'})
        else:
            ollama_helper = OllamaHelper()
            adjusted_config = ollama_helper.ollama_help(feedback, merge_config)
        
        # Validate adjusted config
        if not isinstance(adjusted_config, dict):
            return jsonify({
                'success': False,
                'message': 'Invalid response from AI: expected dictionary'
            })
        
        # Ensure all required keys are present in adjusted config
        for key in required_keys:
            if key not in adjusted_config:
                adjusted_config[key] = merge_config.get(key)
        
        # Validate value ranges
        validations = {
            'threshold': (0.0, 1.0),
            'alpha': (0.0, 1.0),
            'ransac_threshold': (1.0, 10.0),
            'feature_count': (500, 5000),
            'match_ratio': (0.5, 0.9),
            'min_matches': (4, 20),
            'output_quality': (1, 100)
        }
        
        for key, (min_val, max_val) in validations.items():
            if key in adjusted_config:
                try:
                    val = float(adjusted_config[key]) if key != 'feature_count' and key != 'min_matches' else int(adjusted_config[key])
                    adjusted_config[key] = max(min_val, min(max_val, val))
                except (ValueError, TypeError):
                    adjusted_config[key] = merge_config.get(key)
        
        # Validate blend_mode
        valid_blend_modes = ['feature_aligned', 'multi_band', 'gradient_domain', 'simple_overlay', 'panorama']
        if adjusted_config.get('blend_mode') not in valid_blend_modes:
            adjusted_config['blend_mode'] = merge_config.get('blend_mode', 'feature_aligned')
        
        # Validate output_size
        valid_output_sizes = ['original', 'fit_screen', 'custom']
        if adjusted_config.get('output_size') not in valid_output_sizes:
            adjusted_config['output_size'] = merge_config.get('output_size', 'original')
        
        # Validate output_format
        valid_output_formats = ['png', 'jpg', 'webp']
        if adjusted_config.get('output_format') not in valid_output_formats:
            adjusted_config['output_format'] = merge_config.get('output_format', 'png')
        
        # Ensure boolean values
        for bool_key in ['use_orb', 'auto_crop']:
            if bool_key in adjusted_config:
                adjusted_config[bool_key] = bool(adjusted_config[bool_key])
        
        return jsonify({
            'success': True,
            'adjusted_config': adjusted_config
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama connection error: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to connect to Ollama: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Error in adjust_config: {e}")
        return jsonify({
            'success': False,
            'message': f'Error adjusting config: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True) 