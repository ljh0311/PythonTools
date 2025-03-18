import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QFileDialog,
                           QScrollArea, QSlider)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageMerger:
    def __init__(self):
        self.sift = cv2.SIFT_create()
        self.matcher = cv2.BFMatcher()
        self.images = []
        self.matches_threshold = 0.7

    def add_image(self, image_path):
        """Add an image to the merger."""
        img = cv2.imread(image_path)
        if img is not None:
            self.images.append(img)
            return True
        return False

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

    def merge_images(self):
        """Merge all loaded images."""
        if len(self.images) < 2:
            return None

        # Use the first image as reference
        result = self.images[0]
        
        for i in range(1, len(self.images)):
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
            img2_warped = cv2.warpPerspective(self.images[i], Ht.dot(H), (xmax-xmin, ymax-ymin))
            
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_merger = ImageMerger()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Image Feature Merger')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create buttons
        button_layout = QHBoxLayout()
        self.load_btn = QPushButton('Load Images')
        self.merge_btn = QPushButton('Merge')
        self.save_btn = QPushButton('Save')
        
        self.load_btn.clicked.connect(self.load_images)
        self.merge_btn.clicked.connect(self.merge_images)
        self.save_btn.clicked.connect(self.save_result)
        
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.merge_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)

        # Create image display area
        self.scroll_area = QScrollArea()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        # Add threshold slider
        slider_layout = QHBoxLayout()
        slider_label = QLabel('Match Threshold:')
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(99)
        self.threshold_slider.setValue(70)
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.threshold_slider)
        layout.addLayout(slider_layout)

        self.merged_result = None

    def update_threshold(self):
        self.image_merger.matches_threshold = self.threshold_slider.value() / 100

    def load_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_names:
            self.image_merger.images = []
            for file_name in file_names:
                if self.image_merger.add_image(file_name):
                    logger.info(f"Loaded image: {file_name}")
                else:
                    logger.error(f"Failed to load image: {file_name}")

    def merge_images(self):
        if len(self.image_merger.images) < 2:
            logger.warning("Please load at least 2 images")
            return

        self.merged_result = self.image_merger.merge_images()
        if self.merged_result is not None:
            self.display_image(self.merged_result)
        else:
            logger.error("Failed to merge images")

    def display_image(self, img):
        height, width = img.shape[:2]
        bytes_per_line = 3 * width
        image = QImage(
            img.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        ).rgbSwapped()
        
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            self.scroll_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def save_result(self):
        if self.merged_result is None:
            logger.warning("No merged result to save")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        
        if file_name:
            cv2.imwrite(file_name, self.merged_result)
            logger.info(f"Saved merged result to: {file_name}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 