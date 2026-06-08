package org.mtr.ollama;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.mtr.ollama.OllamaConfig;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;
import java.util.stream.Stream;

public class OllamaClient {
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30L))
            .build();
    private static final Gson gson = new Gson();
    private final String baseUrl;
    private final String model;
    private final AtomicReference<CompletableFuture<?>> currentRequest = new AtomicReference<>();

    public OllamaClient(String baseUrl, String model) {
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            throw new IllegalArgumentException("Base URL cannot be null or empty");
        }
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.model = model != null ? model : "llama2";
    }

    public CompletableFuture<String> sendMessage(String message) {
        return this.sendMessage(message, null);
    }

    public CompletableFuture<String> sendMessage(String message, String worldContext) {
        return this.sendMessageAsync(message, worldContext);
    }

    private CompletableFuture<String> sendMessageAsync(String message, String worldContext) {
        CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
            try {
                return this.sendMessageWithModel(message, worldContext, this.model);
            } catch (Exception e) {
                return "An unexpected error occurred: " + e.getMessage();
            }
        });
        this.currentRequest.set(future);
        return future;
    }

    public CompletableFuture<String> sendMessageStreaming(String message, String worldContext, Consumer<String> tokenConsumer) {
        CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
            try {
                String prompt = this.createMTRPrompt(message, worldContext);
                JsonObject requestBody = new JsonObject();
                requestBody.addProperty("model", this.model);
                requestBody.addProperty("prompt", prompt);
                requestBody.addProperty("stream", Boolean.valueOf(true));
                String requestJson = gson.toJson(requestBody);
                
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(this.baseUrl + "/api/generate"))
                        .header("Content-Type", "application/json")
                        .timeout(Duration.ofMinutes(2L))
                        .POST(HttpRequest.BodyPublishers.ofString(requestJson))
                        .build();
                
                StringBuilder fullResponse = new StringBuilder();
                return (String)((CompletableFuture)((CompletableFuture)httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofLines())
                        .thenApply(response -> {
                            if (response.statusCode() == 200) {
                                ((Stream)response.body()).forEach(line -> {
                                    if (line != null && !line.trim().isEmpty()) {
                                        try {
                                            JsonObject jsonLine = JsonParser.parseString((String)line).getAsJsonObject();
                                            if (jsonLine.has("response")) {
                                                String token = jsonLine.get("response").getAsString();
                                                fullResponse.append(token);
                                                tokenConsumer.accept(token);
                                            }
                                        } catch (Exception exception) {
                                            // empty catch block
                                        }
                                    }
                                });
                                return fullResponse.toString();
                            }
                            String error = "Error: Server replied with HTTP " + response.statusCode();
                            tokenConsumer.accept(error);
                            return error;
                        })).exceptionally(throwable -> {
                            String error = "Connection error: " + throwable.getMessage();
                            tokenConsumer.accept(error);
                            return error;
                        })).join();
            } catch (Exception e) {
                String error = "An unexpected error occurred: " + e.getMessage();
                tokenConsumer.accept(error);
                return error;
            }
        });
        this.currentRequest.set(future);
        return future;
    }

    public void cancel() {
        CompletableFuture<?> request = this.currentRequest.getAndSet(null);
        if (request != null && !request.isDone()) {
            request.cancel(true);
        }
    }

    private String sendMessageWithModel(String message, String worldContext, String modelToUse) {
        try {
            String prompt = this.createMTRPrompt(message, worldContext);
            JsonObject requestBody = new JsonObject();
            requestBody.addProperty("model", modelToUse);
            requestBody.addProperty("prompt", prompt);
            requestBody.addProperty("stream", Boolean.valueOf(false));
            String requestJson = gson.toJson(requestBody);
            
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(this.baseUrl + "/api/generate"))
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofMinutes(2L))
                    .POST(HttpRequest.BodyPublishers.ofString(requestJson))
                    .build();
            
            HttpResponse<String> response = httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString()).join();
            if (response.statusCode() == 200) {
                JsonObject jsonResponse = JsonParser.parseString((String)response.body()).getAsJsonObject();
                if (jsonResponse.has("response")) {
                    return jsonResponse.get("response").getAsString();
                }
                return "Error: No response found in server reply.";
            }
            String errorBody = response.body();
            return "Error: Server replied with HTTP " + response.statusCode() + 
                    (errorBody != null && !errorBody.isEmpty() ? "\nResponse: " + errorBody : "");
        } catch (Exception e) {
            return "An unexpected error occurred: " + e.getMessage();
        }
    }

    private String createMTRPrompt(String userMessage, String worldContext) {
        StringBuilder prompt = new StringBuilder();
        String personality = OllamaConfig.overseerPersonality != null ? OllamaConfig.overseerPersonality : "Train Management Assistant";
        prompt.append("You are a helpful ").append(personality).append(" that provides assistance with Minecraft Transit Railway (MTR) train systems. ");
        prompt.append("You help players manage routes, stations, depots, and optimize train networks.\n\n");
        
        if (worldContext != null && !worldContext.trim().isEmpty()) {
            prompt.append("CURRENT MTR SYSTEM STATE:\n");
            prompt.append(worldContext);
            prompt.append("\n");
        }
        
        prompt.append("INSTRUCTIONS:\n");
        prompt.append("- Provide practical advice for managing MTR train systems\n");
        prompt.append("- Suggest route optimizations and improvements\n");
        prompt.append("- Help with station and depot management\n");
        prompt.append("- Be concise and focused on MTR-specific tasks\n");
        prompt.append("- Use MTR terminology (routes, platforms, sidings, depots, etc.)\n\n");
        
        prompt.append("PLAYER MESSAGE: ").append(userMessage).append("\n\n");
        prompt.append("RESPONSE:");
        return prompt.toString();
    }

    public CompletableFuture<Boolean> isServerAvailable() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(this.baseUrl + "/api/tags"))
                        .GET()
                        .timeout(Duration.ofSeconds(10L))
                        .build();
                HttpResponse<String> response = httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString()).join();
                return response.statusCode() == 200;
            } catch (Exception e) {
                return false;
            }
        });
    }
}
