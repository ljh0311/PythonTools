# Ollama LLM Integration for Car Rental Recommender

## Overview

The Car Rental Recommender now includes **Ollama LLM (Large Language Model) integration** to provide intelligent, AI-powered car rental recommendations based on your historical data. This feature uses local LLMs to analyze patterns and provide detailed reasoning for recommendations.

## Features

### 👤 User Profile
The AI system is configured with a specific user profile to provide personalized recommendations:
- **Age**: 24 years old male
- **Driving Experience**: 3 years (decently confident)
- **Decision Style**: Value-conscious, thorough researcher
- **Priorities**: Maximizing time and money value
- **Usage**: Multi-purpose rentals (errands, leisure driving, sightseeing)
- **Focus**: Getting the most out of what is paid for

### 🤖 Personalized AI Recommendations
- **User Profile Awareness**: Considers you as a 24-year-old value-conscious male driver with 3 years of experience
- **Natural Language Analysis**: The LLM analyzes your historical rental data with your profile in mind
- **Value-Focused Reasoning**: Prioritizes cost efficiency and maximizing rental value for multiple purposes
- **Multi-Factor Consideration**: Considers cost efficiency, provider reliability, fuel efficiency, and versatility for errands/leisure
- **Contextual Reasoning**: Provides explanations tailored to your value-conscious decision-making style
- **Confidence Scoring**: Each recommendation includes a confidence score based on data quality and profile match

### 🎯 Smart Analysis
- **Pattern Recognition**: Identifies trends in your rental behavior
- **Cost Optimization**: Suggests the most cost-effective options based on distance and duration
- **Provider Insights**: Analyzes which providers work best for different trip types
- **Fuel Efficiency**: Considers fuel consumption for longer trips

### 🔧 Flexible Configuration
- **Multiple Models**: Support for various Ollama models (llama2, mistral, codellama, etc.)
- **Combined Methods**: Works alongside traditional and ML-based recommendations
- **Customizable**: Enable/disable Ollama recommendations independently

## Setup Instructions

### 1. Install Ollama

Download and install Ollama from [https://ollama.ai](https://ollama.ai)

**Windows:**
```bash
# Download the Windows installer from the website
# Run the installer and follow the setup wizard
```

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Download a Model

After installation, download a model (llama2 is recommended for car rental analysis):

```bash
ollama pull llama2
```

Other recommended models:
```bash
ollama pull mistral          # Good for general reasoning
ollama pull codellama        # Good for structured analysis
ollama pull neural-chat      # Good for conversational responses
```

### 3. Start Ollama Service

Start the Ollama service:

```bash
ollama serve
```

The service will run on `http://localhost:11434` by default.

### 4. Configure the Application

1. **Load your rental data** into the application
2. **Go to the Recommendations tab**
3. **Check "Use Ollama LLM"** to enable AI-powered recommendations
4. **Select your preferred model** from the dropdown
5. **Enter your trip details** (distance, duration, weekend option)
6. **Click "Get Recommendations"**

## Usage

### Basic Usage

1. **Enable Ollama**: Check the "Use Ollama LLM" checkbox
2. **Select Model**: Choose your preferred Ollama model from the dropdown
3. **Enter Trip Details**: 
   - Distance in kilometers
   - Duration in hours
   - Check "Weekend Trip" if applicable
4. **Get Recommendations**: Click the button to receive AI-powered recommendations

### Understanding Results

The application will display recommendations with:
- **Provider**: Car rental company
- **Car Model**: Specific vehicle model
- **Estimated Cost**: Total rental cost
- **Method**: Shows "Ollama Analysis" for AI recommendations
- **Confidence**: How confident the AI is in the recommendation

### Color Coding

- **Green**: Ollama AI recommendations
- **Blue**: Machine Learning predictions
- **Orange**: Historical analysis
- **Gray**: Default pricing

## Model Comparison

| Model | Best For | Speed | Accuracy | Memory |
|-------|----------|-------|----------|---------|
| llama2 | General analysis | Fast | Good | ~4GB |
| llama2:7b | Quick responses | Very Fast | Good | ~4GB |
| llama2:13b | Detailed analysis | Medium | Better | ~8GB |
| mistral | Reasoning | Fast | Very Good | ~4GB |
| codellama | Structured data | Medium | Good | ~4GB |
| neural-chat | Conversational | Fast | Good | ~4GB |

## Troubleshooting

### Common Issues

**1. "Cannot connect to Ollama"**
- Ensure Ollama is installed and running
- Check if the service is running on `localhost:11434`
- Restart Ollama: `ollama serve`

**2. "Model not found"**
- Download the model: `ollama pull <model_name>`
- Check available models: `ollama list`
- Use a different model from the dropdown

**3. "Slow responses"**
- Use a smaller model (llama2:7b instead of llama2:13b)
- Close other applications to free up memory
- Consider using a more powerful computer

**4. "No recommendations"**
- Ensure you have historical rental data loaded
- Check that the data contains the required columns
- Try enabling other recommendation methods (ML, Historical)

### Performance Tips

- **Use llama2:7b** for faster responses
- **Close unnecessary applications** to free up RAM
- **Use SSD storage** for better model loading speed
- **Consider GPU acceleration** if available

## Technical Details

### API Integration

The application communicates with Ollama via HTTP API:
- **Endpoint**: `http://localhost:11434/api/generate`
- **Method**: POST
- **Timeout**: 30 seconds
- **Temperature**: 0.3 (for consistent responses)

### Data Processing

1. **Context Preparation**: Historical data is analyzed and formatted
2. **Prompt Engineering**: Structured prompts are created for the LLM
3. **Response Parsing**: JSON responses are parsed and validated
4. **Fallback Handling**: Graceful degradation when LLM is unavailable

### Prompt Structure

The LLM receives structured prompts including:
- Customer request details (distance, duration, weekend)
- Historical rental data summary
- Provider statistics and patterns
- Popular car models and costs

## Security & Privacy

- **Local Processing**: All LLM processing happens locally on your machine
- **No Data Sharing**: Your rental data never leaves your computer
- **Offline Capable**: Works without internet connection (after model download)
- **Open Source**: Ollama is open source and auditable

## Future Enhancements

Planned improvements:
- **Custom Model Training**: Train models on your specific rental patterns
- **Advanced Analytics**: More sophisticated pattern recognition
- **Multi-Model Ensemble**: Combine multiple models for better accuracy
- **Real-time Learning**: Adapt recommendations based on new data

## Support

For issues with:
- **Ollama Installation**: Visit [https://ollama.ai](https://ollama.ai)
- **Application Issues**: Check the troubleshooting section above
- **Model Selection**: Refer to the model comparison table

---

**Note**: Ollama integration requires a computer with at least 4GB of available RAM and sufficient storage for the selected model.
