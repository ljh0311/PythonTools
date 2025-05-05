import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QScrollArea,
    QSlider,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageMerger:
    def __init__(self):
        self.sift = cv2.SIFT_create()
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher()
        self.images = []
        self.matches_threshold = 0.7
        self.use_orb = False  # Add a toggle for different detector

    def add_image(self, image_path):
        """Add an image to the merger with size limits for better performance."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            # Resize large images for better performance
            max_dimension = 1200  # Reasonable size limit
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
        is_night_image = avg_brightness < 100  # Threshold for night images
        
        if is_night_image:
            # For night images, use more aggressive preprocessing
            
            # Increase contrast with CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Additional contrast stretching
            p5 = np.percentile(enhanced, 5)
            p95 = np.percentile(enhanced, 95)
            enhanced = np.clip((enhanced - p5) * 255.0 / (p95 - p5), 0, 255).astype(np.uint8)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # Edge enhancement
            edges = cv2.Canny(denoised, 50, 150)
            enhanced_with_edges = cv2.addWeighted(denoised, 0.7, edges, 0.3, 0)
            
            return enhanced_with_edges
        else:
            # For normal images, use standard preprocessing
            # Increase contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Apply slight blur to reduce noise
            blurred = cv2.GaussianBlur(enhanced, (3,3), 0)
            
            return blurred

    def side_by_side_merge_with_blend(self):
        """Improved side-by-side merge with blending for better visual results"""
        try:
            if len(self.images) < 2:
                return None
                
            # Get the maximum height of all images
            max_height = max(img.shape[0] for img in self.images)
            
            # Calculate total width, including overlap
            overlap = 50  # pixels of overlap between images
            total_width = sum(img.shape[1] for img in self.images) - (len(self.images) - 1) * overlap
            
            # Create a new image to hold all the images side by side
            result = np.zeros((max_height, total_width, 3), dtype=np.uint8)
            
            # Position to place the next image
            x_offset = 0
            
            # Add each image to the result with blending
            for i, img in enumerate(self.images):
                h, w = img.shape[:2]
                
                # Center vertically if shorter than max height
                y_offset = (max_height - h) // 2
                
                # For all images except the first one, create a blended overlap region
                if i > 0:
                    # Calculate the overlap region
                    overlap_left = x_offset
                    overlap_right = x_offset + w
                    
                    # Create alpha mask for smooth transition (linear gradient)
                    alpha_mask = np.zeros((h, w, 3), dtype=np.float32)
                    for x in range(overlap):
                        alpha = x / overlap  # 0.0 to 1.0 from left to right
                        alpha_mask[:, x, :] = alpha
                    
                    # Blend in the overlap region
                    for y in range(min(h, max_height - y_offset)):
                        for x in range(overlap):
                            if x_offset + x < total_width and y_offset + y < max_height:
                                blend_x = x_offset + x
                                
                                # Get current pixel value from result image
                                current = result[y_offset + y, blend_x].astype(np.float32)
                                
                                # Get new pixel value from this image
                                new_val = img[y, x].astype(np.float32)
                                
                                # Blend based on position in overlap region
                                alpha = alpha_mask[y, x, 0]
                                blended = (1 - alpha) * current + alpha * new_val
                                
                                # Update result
                                result[y_offset + y, blend_x] = blended.astype(np.uint8)
                
                # Copy the non-overlapping part of the image
                non_overlap_width = w - (overlap if i > 0 else 0)
                start_x = overlap if i > 0 else 0
                end_x = w
                
                # Copy region
                non_overlap_region = img[:, start_x:end_x]
                nh, nw = non_overlap_region.shape[:2]
                
                # Make sure we don't copy outside the bounds of result image
                copy_width = min(nw, total_width - x_offset)
                copy_height = min(nh, max_height - y_offset)
                
                # Copy the non-overlapping part
                result[y_offset:y_offset+copy_height, x_offset:x_offset+copy_width] = \
                    non_overlap_region[:copy_height, :copy_width]
                
                # Add a subtle vertical line separator
                if i > 0:
                    cv2.line(result, (x_offset + 5, 0), (x_offset + 5, max_height), (180, 180, 180), 1, cv2.LINE_AA)
                
                # Update the x_offset for the next image (accounting for overlap)
                x_offset += (w - overlap if i > 0 else w)
            
            # Add a border and title
            border_size = 20
            with_border = cv2.copyMakeBorder(
                result, 
                border_size, border_size, border_size, border_size,
                cv2.BORDER_CONSTANT, 
                value=[0, 0, 0]
            )
            
            # Add title
            font = cv2.FONT_HERSHEY_SIMPLEX
            title = "Side-by-Side Merge"
            text_size, _ = cv2.getTextSize(title, font, 1, 2)
            text_x = (with_border.shape[1] - text_size[0]) // 2
            cv2.putText(with_border, title, (text_x, border_size + 5), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            return with_border
        except Exception as e:
            logger.error(f"Error in side_by_side_merge_with_blend: {e}")
            # Fallback to simpler side by side merge
            return self.side_by_side_merge()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_merger = ImageMerger()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Image Feature Merger")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget with grid layout instead of vertical only
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add descriptive title/instructions
        title_label = QLabel("Load multiple images to merge them into a panorama")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)

        # Create two-panel layout
        panels_layout = QHBoxLayout()

        # Left panel: Input images
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Input Images:"))

        # Create scrollable thumbnail view for input images
        self.thumbnails_area = QScrollArea()
        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QHBoxLayout(self.thumbnails_container)
        self.thumbnails_area.setWidget(self.thumbnails_container)
        self.thumbnails_area.setWidgetResizable(True)
        self.thumbnails_area.setMinimumHeight(200)
        left_layout.addWidget(self.thumbnails_area)

        # Right panel: Merged result
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Merged Result:"))

        # Existing scroll area for main image
        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(400, 400)
        right_layout.addWidget(self.scroll_area)

        # Add panels to main layout
        panels_layout.addWidget(left_panel)
        panels_layout.addWidget(right_panel)
        main_layout.addLayout(panels_layout)

        # Improved button layout with icons and tooltips
        button_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load Images")
        self.merge_btn = QPushButton("Merge")
        self.side_by_side_btn = QPushButton("Side-by-Side Merge")
        self.feature_aligned_blend_btn = QPushButton("Feature-Aligned Blend")
        self.save_btn = QPushButton("Save")

        self.load_btn.clicked.connect(self.load_images)
        self.merge_btn.clicked.connect(self.merge_images)
        self.side_by_side_btn.clicked.connect(self.side_by_side_merge)
        self.feature_aligned_blend_btn.clicked.connect(self.feature_aligned_blend)
        self.save_btn.clicked.connect(self.save_result)

        self.load_btn.setToolTip("Select multiple image files to load")
        self.merge_btn.setToolTip("Merge loaded images into one panorama")
        self.side_by_side_btn.setToolTip("Arrange images side by side (better for night images)")
        self.feature_aligned_blend_btn.setToolTip("Create a blend by aligning and merging images based on matching features")
        self.save_btn.setToolTip("Save the merged result")

        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.merge_btn)
        button_layout.addWidget(self.side_by_side_btn)
        button_layout.addWidget(self.feature_aligned_blend_btn)
        button_layout.addWidget(self.save_btn)
        main_layout.addLayout(button_layout)

        # Better labeled slider with current value display
        slider_layout = QHBoxLayout()
        slider_label = QLabel("Match Threshold:")
        self.threshold_value = QLabel("0.7")  # Display current value
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(99)
        self.threshold_slider.setValue(70)
        self.threshold_slider.valueChanged.connect(self.update_threshold_display)

        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.threshold_slider, 1)  # Give slider more space
        slider_layout.addWidget(self.threshold_value)
        main_layout.addLayout(slider_layout)

        # Add more functionality buttons
        advanced_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_app)
        self.reset_btn.setToolTip("Clear all loaded images and results")

        self.show_matches_btn = QPushButton("Show Matches")
        self.show_matches_btn.clicked.connect(self.show_feature_matches)
        self.show_matches_btn.setToolTip("Visualize feature matches between images")

        self.detector_btn = QPushButton("Use ORB Detector")
        self.detector_btn.clicked.connect(self.toggle_detector)
        self.detector_btn.setToolTip("Switch between SIFT and ORB feature detectors")

        self.show_preprocessed_btn = QPushButton("Show Preprocessed")
        self.show_preprocessed_btn.clicked.connect(self.show_preprocessed_images)
        self.show_preprocessed_btn.setToolTip("Show how images look after preprocessing")

        advanced_layout.addWidget(self.reset_btn)
        advanced_layout.addWidget(self.show_matches_btn)
        advanced_layout.addWidget(self.detector_btn)
        advanced_layout.addWidget(self.show_preprocessed_btn)
        main_layout.addLayout(advanced_layout)

        # Add transparency slider for feature-aligned blend
        transparency_layout = QHBoxLayout()
        transparency_label = QLabel("Blend Transparency:")
        self.transparency_value = QLabel("0.5")  # Display current value
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setMinimum(1)
        self.transparency_slider.setMaximum(99)
        self.transparency_slider.setValue(50)
        self.transparency_slider.valueChanged.connect(self.update_transparency_display)

        transparency_layout.addWidget(transparency_label)
        transparency_layout.addWidget(self.transparency_slider, 1)  # Give slider more space
        transparency_layout.addWidget(self.transparency_value)
        main_layout.addLayout(transparency_layout)

        # Status bar for feedback
        self.statusBar().showMessage("Ready. Load images to begin.")

        self.merged_result = None

    def update_threshold_display(self):
        value = self.threshold_slider.value() / 100
        self.threshold_value.setText(f"{value:.2f}")
        self.image_merger.matches_threshold = value

    def load_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_names:
            self.image_merger.images = []
            for file_name in file_names:
                if self.image_merger.add_image(file_name):
                    logger.info(f"Loaded image: {file_name}")
                else:
                    QMessageBox.critical(
                        self, "Error", f"Failed to load image: {file_name}"
                    )

            # Display loaded images
            if len(self.image_merger.images) > 0:
                self.display_loaded_images()

    def display_loaded_images(self):
        # Clear existing thumbnails
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Create thumbnails for each loaded image
        for i, img in enumerate(self.image_merger.images):
            thumbnail = self.create_thumbnail(img, f"Image {i+1}", i)
            self.thumbnails_layout.addWidget(thumbnail)

        # Update status bar
        self.statusBar().showMessage(
            f"Loaded {len(self.image_merger.images)} images. Ready to merge."
        )

        # Display first image in main view
        if len(self.image_merger.images) > 0:
            self.display_image(self.image_merger.images[0])
        else:
            self.image_label.clear()

    def create_thumbnail(self, img, label_text, image_index):
        # Create widget to hold thumbnail
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Create scaled thumbnail (150x150 pixels)
        height, width = img.shape[:2]
        thumbnail_size = 150
        scale = min(thumbnail_size/width, thumbnail_size/height)
        new_size = (int(width*scale), int(height*scale))
        thumbnail_img = cv2.resize(img, new_size)
        
        # Convert to QImage/QPixmap
        bytes_per_line = 3 * new_size[0]
        q_img = QImage(thumbnail_img.data, new_size[0], new_size[1], 
                     bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_img)
        
        # Create label for thumbnail
        img_label = QLabel()
        img_label.setPixmap(pixmap)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(thumbnail_size, thumbnail_size)
        img_label.setStyleSheet("border: 1px solid #CCCCCC; background-color: #EEEEEE;")
        img_label.setCursor(Qt.CursorShape.PointingHandCursor)  # Change cursor to indicate clickable
        
        # Make the thumbnail clickable
        img_label.mousePressEvent = lambda event: self.display_image(self.image_merger.images[image_index])
        
        # Add remove button
        remove_btn = QPushButton("×")
        remove_btn.setMaximumWidth(20)
        remove_btn.clicked.connect(lambda: self.remove_image(image_index))
        
        # Add thumbnail, text and remove button to container
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(label_text))
        header_layout.addWidget(remove_btn)
        layout.addLayout(header_layout)
        layout.addWidget(img_label)
        
        return container

    def merge_images(self):
        if len(self.image_merger.images) < 2:
            QMessageBox.warning(self, "Warning", "Please load at least 2 images")
            return

        # Show progress indicator
        self.statusBar().showMessage("Merging images... Please wait.")
        QApplication.processEvents()  # Ensure UI updates

        try:
            self.merged_result = self.image_merger.merge_images()
            if self.merged_result is not None:
                self.display_image(self.merged_result)
                self.statusBar().showMessage(
                    "Merge complete! You can now save the result."
                )

                # Highlight the result
                self.scroll_area.setStyleSheet("border: 2px solid green;")
            else:
                QMessageBox.critical(
                    self, "Error", "Failed to merge images - result was None"
                )
                self.statusBar().showMessage(
                    "Merge failed. Try adjusting the threshold or using different images."
                )
        except Exception as e:
            error_message = f"Error during merge: {str(e)}"
            logger.error(error_message)
            QMessageBox.critical(self, "Merge Error", error_message)
            self.statusBar().showMessage("Merge failed due to an error.")

    def display_image(self, img):
        height, width = img.shape[:2]
        bytes_per_line = 3 * width
        image = QImage(
            img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        ).rgbSwapped()

        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            self.scroll_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

    def save_result(self):
        if self.merged_result is None:
            QMessageBox.warning(self, "Warning", "No merged result to save")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg)"
        )

        if file_name:
            cv2.imwrite(file_name, self.merged_result)
            logger.info(f"Saved merged result to: {file_name}")

    def reset_app(self):
        """Clear all loaded and merged images"""
        self.image_merger.images = []
        self.merged_result = None
        self.image_label.clear()

        # Clear thumbnails
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.scroll_area.setStyleSheet("")
        self.statusBar().showMessage("Reset complete. Load new images to begin.")

    def show_feature_matches(self):
        """Display feature matches between consecutive images"""
        if len(self.image_merger.images) < 2:
            QMessageBox.warning(
                self, "Warning", "Need at least 2 images to show matches"
            )
            return

        # Just showing matches between first two images for simplicity
        img1 = self.image_merger.images[0]
        img2 = self.image_merger.images[1]

        try:
            kp1, desc1 = self.image_merger.detect_features(img1)
            kp2, desc2 = self.image_merger.detect_features(img2)

            good_matches = self.image_merger.match_features(desc1, desc2)

            # Draw matches
            match_img = cv2.drawMatches(
                img1,
                kp1,
                img2,
                kp2,
                good_matches[:50],
                None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )

            # Display match image
            self.display_image(match_img)
            self.statusBar().showMessage(
                f"Showing {len(good_matches)} feature matches between images 1 and 2"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not show matches: {str(e)}")

    def remove_image(self, index):
        """Remove an image from the loaded set"""
        if 0 <= index < len(self.image_merger.images):
            self.image_merger.images.pop(index)
            self.display_loaded_images()
            self.statusBar().showMessage(
                f"Image removed. {len(self.image_merger.images)} images remaining."
            )

    def toggle_detector(self):
        """Toggle between SIFT and ORB feature detectors"""
        self.image_merger.use_orb = not self.image_merger.use_orb
        if self.image_merger.use_orb:
            self.detector_btn.setText("Use SIFT Detector")
            self.statusBar().showMessage("Using ORB detector - better for some night images")
        else:
            self.detector_btn.setText("Use ORB Detector")
            self.statusBar().showMessage("Using SIFT detector - better for general images")

    def show_preprocessed_images(self):
        """Display preprocessed versions of the images"""
        if len(self.image_merger.images) < 1:
            QMessageBox.warning(self, "Warning", "Load at least one image first")
            return
            
        # Get the first image and its preprocessed version
        img = self.image_merger.images[0]
        processed = self.image_merger.preprocess_for_feature_detection(img)
        
        # Create a side-by-side comparison
        h, w = img.shape[:2]
        # Convert grayscale processed image to BGR for display
        if len(processed.shape) == 2:
            processed_bgr = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        else:
            processed_bgr = processed
            
        # Create side-by-side image
        comparison = np.zeros((h, w*2, 3), dtype=np.uint8)
        comparison[:, :w] = img
        comparison[:, w:] = processed_bgr
        
        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(comparison, "Original", (10, 30), font, 1, (0, 255, 0), 2)
        cv2.putText(comparison, "Preprocessed", (w+10, 30), font, 1, (0, 255, 0), 2)
        
        # Display the comparison
        self.display_image(comparison)
        self.statusBar().showMessage("Showing original vs preprocessed image")

    def side_by_side_merge(self):
        """Directly create a side-by-side merge of the images"""
        if len(self.image_merger.images) < 2:
            QMessageBox.warning(self, "Warning", "Please load at least 2 images")
            return
            
        # Show progress indicator
        self.statusBar().showMessage("Creating side-by-side image... Please wait.")
        QApplication.processEvents()  # Ensure UI updates
        
        try:
            # Call the improved side-by-side merge from the ImageMerger class
            self.merged_result = self.image_merger.side_by_side_merge_with_blend()
            
            if self.merged_result is not None:
                self.display_image(self.merged_result)
                self.statusBar().showMessage("Side-by-side merge complete! You can now save the result.")
                
                # Highlight the result
                self.scroll_area.setStyleSheet("border: 2px solid green;")
            else:
                QMessageBox.critical(self, "Error", "Failed to create side-by-side image")
        except Exception as e:
            error_message = f"Error during side-by-side merge: {str(e)}"
            logger.error(error_message)
            QMessageBox.critical(self, "Merge Error", error_message)
            self.statusBar().showMessage("Merge failed due to an error.")

    def update_transparency_display(self):
        """Update transparency value display when slider changes"""
        value = self.transparency_slider.value() / 100
        self.transparency_value.setText(f"{value:.2f}")
        # This will be used in feature_aligned_blend method

    def feature_aligned_blend(self):
        """Create a feature-aligned blend of the images with adjustable transparency"""
        if len(self.image_merger.images) < 2:
            QMessageBox.warning(self, "Warning", "Please load at least 2 images")
            return
        
        # Show progress indicator
        self.statusBar().showMessage("Creating feature-aligned blend... Please wait.")
        QApplication.processEvents()  # Ensure UI updates
        
        try:
            # Get transparency value from slider
            alpha = self.transparency_slider.value() / 100
            
            # STEP 1: Find features and matches
            img1 = self.image_merger.images[0].copy()
            img2 = self.image_merger.images[1].copy()
            
            kp1, desc1 = self.image_merger.detect_features(img1)
            kp2, desc2 = self.image_merger.detect_features(img2)
            
            good_matches = self.image_merger.match_features(desc1, desc2)
            
            if len(good_matches) < 4:
                # Not enough matches for alignment, fall back to simple overlay
                self.statusBar().showMessage(f"Only {len(good_matches)} matches found. Using simple overlay.")
                QApplication.processEvents()
                self.do_simple_blend(alpha)
                return
            
            # STEP 2: Find transformation between images
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Try to find homography
            try:
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if H is None:
                    raise ValueError("Homography is None")
            except Exception as e:
                self.statusBar().showMessage(f"Could not find alignment: {str(e)}. Using simple overlay.")
                QApplication.processEvents()
                self.do_simple_blend(alpha)
                return
            
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
            
            # Set the result and display it
            self.merged_result = result_with_border
            self.display_image(self.merged_result)
            self.statusBar().showMessage(f"Feature-aligned blend complete with {len(good_matches)} matches! You can now save the result.")
            
            # Highlight the result
            self.scroll_area.setStyleSheet("border: 2px solid green;")
            
        except Exception as e:
            error_message = f"Error during feature-aligned blend: {str(e)}"
            logger.error(error_message)
            QMessageBox.critical(self, "Blend Error", error_message)
            self.statusBar().showMessage("Blend failed, trying simple overlay...")
            self.do_simple_blend(alpha)
    
    def do_simple_blend(self, alpha):
        """Fallback method for simple overlay blend without feature alignment"""
        try:
            # Make copies of the images
            img1 = self.image_merger.images[0].copy()
            img2 = self.image_merger.images[1].copy()
            
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
            
            # Set the result and display it
            self.merged_result = result_with_border
            self.display_image(self.merged_result)
            self.statusBar().showMessage("Simple overlay blend complete! You can now save the result.")
            
            # Highlight the result
            self.scroll_area.setStyleSheet("border: 2px solid green;")
        except Exception as e:
            error_message = f"Error during simple blend: {str(e)}"
            logger.error(error_message)
            QMessageBox.critical(self, "Blend Error", error_message)
            self.statusBar().showMessage("All blend methods failed.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
