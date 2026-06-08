"""
AnyLogic Data Loader

This module handles loading and parsing AnyLogic simulation CSV files
for comparison with historical clinic data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import os

from app.utils.logger import get_logger


class AnyLogicDataLoader:
    """
    Loads and processes AnyLogic simulation CSV files.
    
    This class handles:
    - CSV file parsing and validation
    - Data type conversion and cleaning
    - Process name standardization
    - Error handling and logging
    """

    def __init__(self):
        """Initialize the AnyLogic data loader."""
        self.logger = get_logger(__name__)
        self.data = None
        self.file_path = None
        self.metadata = {}

    def load_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse an AnyLogic CSV file.
        
        Args:
            file_path: Path to the AnyLogic CSV file
            
        Returns:
            Dict containing parsed data and metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
            Exception: For other parsing errors
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"AnyLogic file not found: {file_path}")
            
            # Read CSV file
            self.logger.info(f"Loading AnyLogic data from: {file_path}")
            raw_data = pd.read_csv(file_path)
            
            # Clean column names (strip whitespace)
            raw_data.columns = raw_data.columns.str.strip()
            
            # Validate required columns
            self._validate_columns(raw_data)
            
            # Clean and process data
            processed_data = self._process_data(raw_data)
            
            # Store results
            self.data = processed_data
            self.file_path = file_path
            self.metadata = self._extract_metadata(raw_data, file_path)
            
            self.logger.info(f"Successfully loaded {len(processed_data)} processes from AnyLogic file")
            
            return {
                'data': processed_data,
                'metadata': self.metadata,
                'file_path': file_path
            }
            
        except Exception as e:
            self.logger.error(f"Error loading AnyLogic file {file_path}: {e}")
            raise

    def _validate_columns(self, data: pd.DataFrame) -> None:
        """
        Validate that the CSV has required columns.
        
        Args:
            data: Raw DataFrame from CSV
            
        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ['Process', 'Mean (mins)', 'Median (mins)']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check for empty data
        if len(data) == 0:
            raise ValueError("AnyLogic file contains no data")

    def _process_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and process the raw AnyLogic data.
        
        Args:
            raw_data: Raw DataFrame from CSV
            
        Returns:
            Cleaned and processed DataFrame
        """
        # Make a copy to avoid modifying original
        data = raw_data.copy()
        
        # Clean process names (strip whitespace, handle empty values)
        data['Process'] = data['Process'].astype(str).str.strip()
        data = data[data['Process'] != '']  # Remove empty process names
        data = data[data['Process'] != 'nan']  # Remove NaN process names
        
        # Convert numeric columns and handle errors
        numeric_columns = ['Mean (mins)', 'Median (mins)']
        for col in numeric_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Remove rows with invalid numeric data
        data = data.dropna(subset=numeric_columns)
        
        # Remove negative durations (invalid)
        for col in numeric_columns:
            data = data[data[col] >= 0]
        
        # Sort by mean duration for consistent ordering
        data = data.sort_values('Mean (mins)', ascending=False).reset_index(drop=True)
        
        # Add calculated fields
        data['Duration_Range'] = data['Mean (mins)'] - data['Median (mins)']
        data['Efficiency_Score'] = data['Median (mins)'] / data['Mean (mins)']
        
        self.logger.debug(f"Processed AnyLogic data: {len(data)} valid processes")
        
        return data

    def _extract_metadata(self, raw_data: pd.DataFrame, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from the loaded file.
        
        Args:
            raw_data: Raw DataFrame
            file_path: Path to the file
            
        Returns:
            Dictionary containing metadata
        """
        return {
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'total_processes': len(self.data) if self.data is not None else 0,
            'original_rows': len(raw_data),
            'mean_duration_avg': float(self.data['Mean (mins)'].mean()) if self.data is not None else 0,
            'median_duration_avg': float(self.data['Median (mins)'].mean()) if self.data is not None else 0,
            'duration_range': {
                'min_mean': float(self.data['Mean (mins)'].min()) if self.data is not None else 0,
                'max_mean': float(self.data['Mean (mins)'].max()) if self.data is not None else 0,
                'min_median': float(self.data['Median (mins)'].min()) if self.data is not None else 0,
                'max_median': float(self.data['Median (mins)'].max()) if self.data is not None else 0,
            },
            'loaded_at': pd.Timestamp.now().isoformat()
        }

    def get_process_names(self) -> List[str]:
        """
        Get list of all process names in the loaded data.
        
        Returns:
            List of process names
        """
        if self.data is None:
            return []
        
        return self.data['Process'].tolist()

    def get_process_data(self, process_name: str) -> Optional[Dict[str, float]]:
        """
        Get data for a specific process.
        
        Args:
            process_name: Name of the process to retrieve
            
        Returns:
            Dictionary with process metrics or None if not found
        """
        if self.data is None:
            return None
        
        process_row = self.data[self.data['Process'] == process_name]
        
        if len(process_row) == 0:
            return None
        
        row = process_row.iloc[0]
        return {
            'mean_mins': float(row['Mean (mins)']),
            'median_mins': float(row['Median (mins)']),
            'duration_range': float(row['Duration_Range']),
            'efficiency_score': float(row['Efficiency_Score'])
        }

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for the loaded AnyLogic data.
        
        Returns:
            Dictionary with summary statistics
        """
        if self.data is None:
            return {}
        
        return {
            'total_processes': len(self.data),
            'mean_duration_stats': {
                'mean': float(self.data['Mean (mins)'].mean()),
                'median': float(self.data['Mean (mins)'].median()),
                'std': float(self.data['Mean (mins)'].std()),
                'min': float(self.data['Mean (mins)'].min()),
                'max': float(self.data['Mean (mins)'].max())
            },
            'median_duration_stats': {
                'mean': float(self.data['Median (mins)'].mean()),
                'median': float(self.data['Median (mins)'].median()),
                'std': float(self.data['Median (mins)'].std()),
                'min': float(self.data['Median (mins)'].min()),
                'max': float(self.data['Median (mins)'].max())
            },
            'efficiency_stats': {
                'mean': float(self.data['Efficiency_Score'].mean()),
                'median': float(self.data['Efficiency_Score'].median()),
                'std': float(self.data['Efficiency_Score'].std())
            }
        }

    def export_processed_data(self, output_path: str) -> None:
        """
        Export processed data to CSV.
        
        Args:
            output_path: Path to save the processed data
        """
        if self.data is None:
            raise ValueError("No data loaded to export")
        
        self.data.to_csv(output_path, index=False)
        self.logger.info(f"Exported processed AnyLogic data to: {output_path}")

    def has_data(self) -> bool:
        """Check if data is loaded."""
        return self.data is not None and len(self.data) > 0

    def clear(self) -> None:
        """Clear loaded data."""
        self.data = None
        self.file_path = None
        self.metadata = {}
        self.logger.debug("Cleared AnyLogic data") 