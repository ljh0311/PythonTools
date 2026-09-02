package com.ollamamod.client;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.ollamamod.OllamaMod;
import com.ollamamod.config.OllamaConfig;
import com.ollamamod.session.ConversationManager;

import java.io.IOException;
import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;

public class OllamaClient {
    private static final Gson GSON = new Gson();
    private static final HttpClient HTTP_CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    
    private final ConversationManager conversationManager;
    private ActionSequenceLearner sequenceLearner;
    private String currentPlayerName;
    
    public OllamaClient(ConversationManager conversationManager) {
        this.conversationManager = conversationManager;
    }
    
    public void setSequenceLearner(ActionSequenceLearner sequenceLearner) {
        this.sequenceLearner = sequenceLearner;
    }
    
    public CompletableFuture<String> sendMessage(String message, String playerName) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                String model = OllamaConfig.defaultModel;
                String context = conversationManager.getContext(playerName);
                
                // Store player name for command learning context
                this.currentPlayerName = playerName;
                
                JsonObject requestBody = new JsonObject();
                requestBody.addProperty("model", model);
                requestBody.addProperty("prompt", buildPrompt(message, context));
                // Non-streaming only: the parser below expects a single JSON object, whereas
                // a streaming response is newline-delimited JSON.
                requestBody.addProperty("stream", false);
                
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(OllamaConfig.ollamaUrl + "/api/generate"))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(GSON.toJson(requestBody)))
                        .timeout(Duration.ofSeconds(OllamaConfig.timeoutSeconds))
                        .build();
                
                HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
                
                if (response.statusCode() != 200) {
                    OllamaMod.LOGGER.error("Ollama API error {}: {}", response.statusCode(), response.body());
                    throw new OllamaException(describeHttpFailure(response.statusCode(), response.body(), model));
                }
                
                String aiResponse = readResponseField(response.body());
                conversationManager.addMessage(playerName, message, aiResponse);
                return aiResponse;
                
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new OllamaException("Request to Ollama was interrupted.", e);
            } catch (IOException e) {
                OllamaMod.LOGGER.error("Error communicating with Ollama", e);
                throw new OllamaException(describeTransportFailure(e), e);
            }
        });
    }
    
    private static String readResponseField(String body) {
        try {
            JsonObject json = GSON.fromJson(body, JsonObject.class);
            if (json != null && json.has("response")) {
                return json.get("response").getAsString();
            }
        } catch (RuntimeException e) {
            OllamaMod.LOGGER.error("Could not parse Ollama response body: {}", body, e);
        }
        throw new OllamaException("Ollama sent a reply this mod could not read. See latest.log for the raw body.");
    }
    
    private static String describeHttpFailure(int statusCode, String body, String model) {
        if (statusCode == 404) {
            return "Ollama has no model named '" + model + "'. Pull it first with: ollama pull " + model;
        }
        String detail = readErrorField(body);
        return "Ollama returned HTTP " + statusCode + (detail.isEmpty() ? "." : ": " + detail);
    }
    
    private static String describeTransportFailure(IOException e) {
        if (e instanceof HttpTimeoutException) {
            return "Ollama at " + OllamaConfig.ollamaUrl + " did not reply within "
                    + OllamaConfig.timeoutSeconds + "s. Try a smaller model, or raise timeoutSeconds.";
        }
        if (e instanceof ConnectException) {
            return "Cannot reach Ollama at " + OllamaConfig.ollamaUrl
                    + ". Is it running? Start it with: ollama serve";
        }
        return "Cannot reach Ollama at " + OllamaConfig.ollamaUrl + " (" + e.getMessage() + ")";
    }
    
    private static String readErrorField(String body) {
        try {
            JsonObject json = GSON.fromJson(body, JsonObject.class);
            if (json != null && json.has("error")) {
                return json.get("error").getAsString();
            }
        } catch (RuntimeException ignored) {
            // Fall through to the bare status code, which is still better than nothing.
        }
        return "";
    }
    
    private String buildPrompt(String message, String context) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are ").append(OllamaConfig.overseerPersonality)
              .append(" in Minecraft. ");
        
        if (!context.isEmpty()) {
            prompt.append("\n\nContext:\n").append(context);
        }
        
        // Add command learning context if available
        if (OllamaConfig.enableCommandLearning && sequenceLearner != null && message != null) {
            String commandLearningContext = buildCommandLearningContext(message);
            if (commandLearningContext != null && !commandLearningContext.isEmpty()) {
                prompt.append("\n\nCommand Learning Context:\n").append(commandLearningContext);
            }
        }
        
        prompt.append("\n\nPlayer: ").append(message);
        prompt.append("\nAssistant: ");
        
        return prompt.toString();
    }
    
    private String buildCommandLearningContext(String message) {
        if (sequenceLearner == null || message == null) {
            return null;
        }
        
        // Use stored player name
        String playerName = currentPlayerName != null ? currentPlayerName : "Player";
        
        StringBuilder context = new StringBuilder();
        
        // Check if message mentions a command
        if (message.toLowerCase().contains("give") || message.toLowerCase().contains("/give")) {
            List<ActionSequenceLearner.FailurePattern> patterns = 
                sequenceLearner.getFailurePatterns(playerName, "give");
            if (!patterns.isEmpty()) {
                context.append("Common failures with /give command:\n");
                for (int i = 0; i < Math.min(3, patterns.size()); i++) {
                    ActionSequenceLearner.FailurePattern pattern = patterns.get(i);
                    context.append("- ").append(pattern.reason)
                           .append(" (occurred ").append(pattern.frequency).append(" times)\n");
                }
            }
            
            double successRate = sequenceLearner.getCommandSuccessRate(playerName, "/give");
            if (successRate > 0) {
                context.append("Success rate with /give: ").append(String.format("%.1f", successRate)).append("%\n");
            }
        }
        
        // Add general command suggestions based on learned patterns
        List<ActionSequenceLearner.CommandLearningData> recentFailures = 
            sequenceLearner.getCommandHistory(playerName, null);
        if (!recentFailures.isEmpty()) {
            int failureCount = 0;
            for (ActionSequenceLearner.CommandLearningData data : recentFailures) {
                if (!data.success && failureCount < 3) {
                    context.append("Recent failure: ").append(data.command)
                           .append(" - ").append(data.failureReason != null ? data.failureReason : "Unknown reason")
                           .append("\n");
                    failureCount++;
                }
            }
        }
        
        return context.toString();
    }
    
    public boolean isAvailable() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(OllamaConfig.ollamaUrl + "/api/tags"))
                    .GET()
                    .timeout(Duration.ofSeconds(5))
                    .build();
            
            HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }
}
