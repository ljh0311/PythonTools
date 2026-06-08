"""
Metadata Management System for SmartCam

Provides functionality to store, retrieve, search, and analyze image metadata
including tags, scene classifications, and detection information.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages metadata storage and retrieval for captured images."""
    
    def __init__(self, base_dir: str = "captures"):
        """
        Initialize metadata manager.
        
        Args:
            base_dir: Base directory for captures
        """
        self.base_dir = base_dir
        self.metadata_index = {}  # In-memory index for fast searching
        self._load_index()
    
    def save_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Save metadata for an image.
        
        Args:
            image_path: Path to the image file
            metadata: Metadata dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create metadata file path (same name as image but .json)
            image_path_obj = Path(image_path)
            metadata_path = image_path_obj.with_suffix('.json')
            
            # Add file path and timestamp if not present
            if 'file_path' not in metadata:
                metadata['file_path'] = str(image_path)
            if 'metadata_saved_at' not in metadata:
                metadata['metadata_saved_at'] = datetime.now().isoformat()
            
            # Save metadata to JSON file
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update index
            self.metadata_index[str(image_path)] = {
                'metadata_path': str(metadata_path),
                'tags': metadata.get('tags', []),
                'scene': metadata.get('scene_classification', {}),
                'event_type': metadata.get('event_type', 'unknown'),
                'timestamp': metadata.get('timestamp', ''),
                'is_anomaly': metadata.get('is_anomaly', False)
            }
            
            logger.debug(f"Metadata saved: {metadata_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return False
    
    def load_metadata(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Load metadata for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            image_path_obj = Path(image_path)
            metadata_path = image_path_obj.with_suffix('.json')
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None
    
    def search_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """
        Search for images by tags.
        
        Args:
            tags: List of tags to search for
            match_all: If True, image must have all tags. If False, any tag matches.
            
        Returns:
            List of image paths matching the tags
        """
        matching_images = []
        
        for image_path, index_data in self.metadata_index.items():
            image_tags = index_data.get('tags', [])
            
            if match_all:
                if all(tag in image_tags for tag in tags):
                    matching_images.append(image_path)
            else:
                if any(tag in image_tags for tag in tags):
                    matching_images.append(image_path)
        
        return matching_images
    
    def search_by_scene(self, scene_type: str, scene_value: str) -> List[str]:
        """
        Search for images by scene classification.
        
        Args:
            scene_type: Type of scene classification (location, time_of_day, crowd_level, activity)
            scene_value: Value to match (e.g., 'indoor', 'day', 'crowded')
            
        Returns:
            List of image paths matching the scene
        """
        matching_images = []
        
        for image_path, index_data in self.metadata_index.items():
            scene = index_data.get('scene', {})
            if isinstance(scene, dict) and scene.get(scene_type) == scene_value:
                matching_images.append(image_path)
        
        return matching_images
    
    def search_anomalies(self) -> List[str]:
        """
        Search for images with detected anomalies.
        
        Returns:
            List of image paths with anomalies
        """
        return [path for path, data in self.metadata_index.items() 
                if data.get('is_anomaly', False)]
    
    def get_tag_statistics(self) -> Dict[str, int]:
        """
        Get statistics about tag usage.
        
        Returns:
            Dictionary mapping tags to their frequency
        """
        tag_counts = {}
        
        for index_data in self.metadata_index.values():
            tags = index_data.get('tags', [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_scene_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about scene classifications.
        
        Returns:
            Dictionary with scene type statistics
        """
        scene_stats = {
            'location': {},
            'time_of_day': {},
            'crowd_level': {},
            'activity': {}
        }
        
        for index_data in self.metadata_index.values():
            scene = index_data.get('scene', {})
            if isinstance(scene, dict):
                for scene_type in scene_stats.keys():
                    value = scene.get(scene_type)
                    if value:
                        scene_stats[scene_type][value] = scene_stats[scene_type].get(value, 0) + 1
        
        return scene_stats
    
    def get_event_type_statistics(self) -> Dict[str, int]:
        """
        Get statistics about event types.
        
        Returns:
            Dictionary mapping event types to their frequency
        """
        event_counts = {}
        
        for index_data in self.metadata_index.values():
            event_type = index_data.get('event_type', 'unknown')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return dict(sorted(event_counts.items(), key=lambda x: x[1], reverse=True))
    
    def export_metadata(self, output_path: str, format: str = 'json') -> bool:
        """
        Export all metadata to a file.
        
        Args:
            output_path: Path to save exported data
            format: Export format ('json' or 'csv')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if format == 'json':
                # Export as JSON
                all_metadata = {}
                for image_path in self.metadata_index.keys():
                    metadata = self.load_metadata(image_path)
                    if metadata:
                        all_metadata[image_path] = metadata
                
                with open(output_path, 'w') as f:
                    json.dump(all_metadata, f, indent=2)
            
            elif format == 'csv':
                # Export as CSV
                import csv
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    # Header
                    writer.writerow(['Image Path', 'Event Type', 'Tags', 'Scene', 
                                   'Timestamp', 'Is Anomaly'])
                    
                    # Data rows
                    for image_path, index_data in self.metadata_index.items():
                        writer.writerow([
                            image_path,
                            index_data.get('event_type', 'unknown'),
                            ', '.join(index_data.get('tags', [])),
                            str(index_data.get('scene', {})),
                            index_data.get('timestamp', ''),
                            index_data.get('is_anomaly', False)
                        ])
            
            logger.info(f"Metadata exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")
            return False
    
    def _load_index(self):
        """Load metadata index from disk."""
        try:
            # Scan for metadata files
            base_path = Path(self.base_dir)
            if not base_path.exists():
                return
            
            # Find all JSON metadata files
            for json_file in base_path.rglob('*.json'):
                try:
                    with open(json_file, 'r') as f:
                        metadata = json.load(f)
                    
                    image_path = metadata.get('file_path', '')
                    if image_path and Path(image_path).exists():
                        self.metadata_index[image_path] = {
                            'metadata_path': str(json_file),
                            'tags': metadata.get('tags', []),
                            'scene': metadata.get('scene_classification', {}),
                            'event_type': metadata.get('event_type', 'unknown'),
                            'timestamp': metadata.get('timestamp', ''),
                            'is_anomaly': metadata.get('is_anomaly', False)
                        }
                except Exception as e:
                    logger.warning(f"Failed to load metadata from {json_file}: {e}")
            
            logger.info(f"Loaded {len(self.metadata_index)} metadata entries")
            
        except Exception as e:
            logger.error(f"Failed to load metadata index: {e}")
    
    def rebuild_index(self):
        """Rebuild the metadata index from disk."""
        self.metadata_index = {}
        self._load_index()

