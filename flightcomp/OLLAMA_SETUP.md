# Ollama AI Integration Setup Guide

This guide explains how to set up and use the Ollama AI integration for intelligent ATC responses in the Aviation Assistant.

## Prerequisites

1. **Python Dependencies**: Make sure you have the required Python packages installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ollama Installation**: Install Ollama on your system:
   - **Windows**: Download from [ollama.ai](https://ollama.ai)
   - **macOS**: `brew install ollama`
   - **Linux**: `curl -fsSL https://ollama.ai/install.sh | sh`

## Setup Instructions

### 1. Install Ollama Models

After installing Ollama, you need to download at least one language model. The recommended models for ATC responses are:

```bash
# Download Llama 2 (recommended)
ollama pull llama2

# Alternative models you can try:
ollama pull llama2:7b
ollama pull llama2:13b
ollama pull codellama
ollama pull mistral
```

### 2. Start Ollama Service

Start the Ollama service:

```bash
ollama serve
```

The service will run on `http://localhost:11434` by default.

### 3. Configure AI Settings

1. Launch the Aviation Assistant
2. Select "ATC" role
3. Click the "AI Settings" button in the header
4. Configure the following settings:
   - **Enable AI-powered responses**: Check to enable AI
   - **Ollama URL**: `http://localhost:11434` (default)
   - **Model**: Select your preferred model (e.g., `llama2`)
   - **Temperature**: Adjust creativity (0.0-1.0, default: 0.7)
   - **Max History**: Number of messages to remember (default: 20)
   - **Timeout**: API timeout in seconds (default: 30)

5. Click "Test Connection" to verify Ollama is working
6. Click "Save Settings"

## Using AI Responses

### Ground Control AI Responses

1. **Select an Aircraft**: Click on an aircraft in the "Aircraft on Ground" list
2. **Enter Pilot Message**: Type a pilot message in the "AI Response" field
3. **Send AI Response**: Click "Send AI Response" or press Enter
4. **View Response**: The AI-generated ATC response will appear in the communications log

### Example Pilot Messages

Try these example pilot messages to test the AI:

- "Request taxi clearance to runway 27"
- "Ready for departure"
- "Request pushback"
- "Holding short of runway 27"
- "Request landing clearance"
- "Contact ground for taxi instructions"

### AI-Generated ATIS

1. Go to the "ATIS Management" tab
2. Click "Generate AI ATIS"
3. The AI will create a comprehensive ATIS message based on current weather and airport conditions

## Features

### Intelligent Context Awareness

The AI considers:
- Aircraft type and callsign
- Current location and status
- Airport configuration (runways, taxiways)
- Weather conditions
- Recent communication history

### Fallback Responses

If Ollama is not available, the system provides intelligent fallback responses based on:
- Message keywords
- Aircraft information
- Standard ATC phraseology

### Asynchronous Processing

AI responses are generated asynchronously to prevent UI blocking:
1. Immediate acknowledgment is provided
2. AI processes the request in the background
3. Full response is generated and displayed

## Troubleshooting

### Connection Issues

1. **Ollama not running**: Start Ollama with `ollama serve`
2. **Wrong URL**: Verify Ollama URL in AI Settings
3. **Model not found**: Download the model with `ollama pull <model_name>`

### Performance Issues

1. **Slow responses**: Try a smaller model (e.g., `llama2:7b`)
2. **High memory usage**: Close other applications or use a smaller model
3. **Timeout errors**: Increase timeout in AI Settings

### Response Quality

1. **Poor responses**: Adjust temperature setting
2. **Inconsistent responses**: Lower temperature for more consistent output
3. **Generic responses**: Increase temperature for more creative responses

## Advanced Configuration

### Custom Models

You can use custom fine-tuned models:
1. Create a custom model file (Modelfile)
2. Build the model: `ollama create myatc -f Modelfile`
3. Select "myatc" in AI Settings

### Model Recommendations

- **Llama 2**: Good balance of performance and quality
- **Llama 2:7b**: Faster, lower memory usage
- **Llama 2:13b**: Higher quality, more memory required
- **CodeLlama**: Good for technical aviation terminology
- **Mistral**: Fast and efficient

### System Requirements

- **Minimum**: 8GB RAM, 4GB free disk space
- **Recommended**: 16GB RAM, 8GB free disk space
- **GPU**: Optional but recommended for faster responses

## Security Notes

- Ollama runs locally on your machine
- No data is sent to external servers
- Communication history is stored locally
- Models are downloaded and cached locally

## Support

If you encounter issues:

1. Check the console output for error messages
2. Verify Ollama is running: `ollama list`
3. Test Ollama directly: `ollama run llama2 "Hello"`
4. Check the AI Settings dialog for connection status

For more information about Ollama, visit [ollama.ai](https://ollama.ai).
