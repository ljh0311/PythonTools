# Minecraft Mod Handler - Web Application

A modern web-based application for managing Minecraft mods and analyzing crash logs with AI-powered assistance using Ollama.

## 🌟 Features

- **🌐 Web Interface**: Access from any browser, no installation needed
- **🤖 AI-Powered Analysis**: Intelligent crash log analysis using Ollama
- **🔧 Mod Management**: Easy mod enable/disable, backup, and organization
- **✅ Compatibility Checking**: Detect conflicts and missing dependencies
- **📱 Responsive Design**: Works on desktop, tablet, and mobile
- **🎨 Modern UI**: Beautiful, intuitive interface with Bootstrap 5

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Ollama installed and running
- Minecraft with mods installed

### Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Ollama:**

   ```bash
   # Install Ollama (if not already installed)
   # Visit https://ollama.ai for installation instructions
   
   # Pull a model (e.g., llama3.2)
   ollama pull llama3.2
   
   # Start Ollama service
   ollama serve
   ```

4. **Run the web application:**

   ```bash
   python app.py
   ```

5. **Open your browser and navigate to:**

   ```
   http://localhost:5000
   ```

## 📖 Usage Guide

### Dashboard

- Overview of your mod collection
- Quick access to all features
- Real-time Ollama connection status

### Mod Management

1. Enter your Minecraft directory path
2. Click "Load Mods" to scan for installed mods
3. View mod details (name, version, author, size)
4. Enable/disable mods individually or in bulk
5. Create backups before making changes
6. Get AI suggestions for problematic mods

### Crash Log Analysis

1. Upload a crash log file (.log or .txt)
2. Click "Analyze with AI" to get intelligent analysis
3. Review detailed insights and solutions
4. Copy results for sharing or documentation

### Compatibility Check

1. Enter your Minecraft directory path
2. Click "Check Compatibility" to scan for issues
3. Review conflicts, version mismatches, and missing dependencies
4. Get actionable recommendations

### Settings

- Configure Ollama connection
- Set default directories
- Customize application preferences
- View system information

## 🔧 Configuration

### Ollama Setup

- **Default URL**: `http://localhost:11434`
- **Recommended Models**: `llama3.2`, `codellama`, `mistral`
- **Model Selection**: Choose from available models in settings

### File Upload Limits

- **Max file size**: 16MB (configurable)
- **Supported formats**: .log, .txt
- **Auto-cleanup**: Uploaded files are automatically removed after analysis

## 🛠️ Development

### Project Structure

```
McHandler/
├── app.py                 # Flask web application
├── mod_manager.py         # Mod management logic
├── crash_analyzer.py      # AI-powered crash analysis
├── compatibility_checker.py # Compatibility checking
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Dashboard
│   ├── mods.html         # Mod management
│   ├── crash_analysis.html # Crash analysis
│   ├── compatibility.html # Compatibility check
│   └── settings.html     # Settings
├── static/               # Static assets
│   ├── style.css        # Custom styles
│   └── app.js           # JavaScript functions
└── requirements.txt      # Python dependencies
```

### API Endpoints

- `GET /` - Dashboard
- `GET /mods` - Mod management page
- `POST /api/mods/load` - Load mods from directory
- `POST /api/mods/backup` - Create mod backup
- `POST /api/mods/toggle` - Enable/disable mod
- `POST /api/crash/analyze` - Analyze crash log
- `POST /api/compatibility/check` - Check compatibility
- `GET /api/ollama/status` - Check Ollama status
- `POST /api/ollama/suggest` - Get AI suggestions

## 🔒 Security Notes

- The application runs locally by default
- File uploads are restricted to specific types and sizes
- Uploaded files are automatically cleaned up
- No sensitive data is stored permanently

## 🐛 Troubleshooting

### Common Issues

**Ollama Connection Failed**

- Ensure Ollama is running: `ollama serve`
- Check if the URL is correct in settings
- Verify at least one model is installed: `ollama list`

**Mods Not Loading**

- Verify the Minecraft directory path is correct
- Check that the `mods` folder exists
- Ensure you have read permissions for the directory

**File Upload Issues**

- Check file size (max 16MB)
- Ensure file format is .log or .txt
- Verify file is not corrupted

**Performance Issues**

- Large mod collections may take time to load
- Consider reducing the number of mods
- Ensure adequate system resources

### Getting Help

1. Check the browser console for JavaScript errors
2. Verify Ollama is running and accessible
3. Check Python console for server errors
4. Ensure all dependencies are installed correctly

## 🚀 Deployment

### Local Network Access

To access from other devices on your network:

```bash
python app.py --host 0.0.0.0 --port 5000
```

### Production Deployment

For production use, consider:

- Using a WSGI server like Gunicorn
- Setting up a reverse proxy with Nginx
- Implementing proper authentication
- Using HTTPS for secure connections

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

---

**Enjoy managing your Minecraft mods with AI assistance! 🎮✨**
