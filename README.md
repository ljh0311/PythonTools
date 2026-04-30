# Python Tools Collection

A modular collection of Python and web utilities organized as independent projects. The original project intention is to keep practical tools in one repository while preserving clear project boundaries, plug-and-play development, and assistive AI workflows that support users without replacing human judgement.

## Tools Available

### [CarRS](./CarRS)
A Car Rental Recommendation System that helps users find the best rental options based on their preferences:
- Automatic data loading from CSV files
- Advanced data analysis features
- Cost breakdown (duration and fuel costs)
- User-friendly interface
- Customizable search parameters

### [Battery Monitor](./New%20folder)
A battery monitoring utility with charge-cycle logging and local AI-assisted battery analysis:
- Battery status and charge/discharge cycle tracking
- Historical logging for battery usage patterns
- Local Ollama-based analysis prompts

> Current structure note: this project is still stored under `New folder/` on `main`. Active feature work renames it to `BatteryMonitor/`, which should be completed before further scaling.

### [Image Merger](./Image_Merger)
A Flask web application for merging multiple images into panoramas:
- Upload multiple images to create panoramas
- Feature detection, matching, and blending
- Adjustable match threshold and blend transparency
- Support for different feature detectors (SIFT/ORB)
- Download merged results

### [Brightness Controller](./BrightnessController)
Automatically adjusts screen brightness based on camera input or screen content:
- Camera-based brightness control
- Screen content-based brightness control
- Smooth brightness transitions
- User-friendly GUI interface
- Configurable brightness levels

### [Time Logger](./TimeLogger)
A desktop application for tracking work hours and generating reports:
- Time logging with start/end times and break durations
- Report generation with visualizations
- Payroll period management
- Data export to multiple formats (CSV, Excel, PDF)
- Data visualization with charts

### [Aviation Operations Assistant](./flightcomp)
A tool to assist pilots and air traffic controllers with aviation communications:
- ATC instructions and readback generation for pilots
- Ground operations and tower control for controllers
- Aircraft sequencing and ATIS management
- Configurable based on experience level and aircraft type
- Active feature work is adding AI-guided debrief workflows for training support

### [3D Reconstruction](./3d_reconstruction)
A pipeline for creating 3D reconstructions from video input:
- Video frame extraction
- Feature detection and matching
- Camera pose estimation
- Dense reconstruction and mesh generation
- Texture mapping

## Repository Structure
The repository is organized by tool, with each tool in its own directory containing:
- Source code
- Documentation
- Configuration files
- Test cases (where applicable)

Weekly coordination notes are tracked in [`weekly_progress.md`](./weekly_progress.md). If a project-specific report becomes too large for the root update, that project should add its own `weekly_progress.md`.

## Contributing
Feel free to contribute by:
1. Adding new tools
2. Improving existing tools
3. Fixing bugs
4. Enhancing documentation

## License
This repository is licensed under the MIT License. See individual tool directories for specific licensing information. 