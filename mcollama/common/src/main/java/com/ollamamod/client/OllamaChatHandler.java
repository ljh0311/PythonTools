package com.ollamamod.client;

import com.ollamamod.OllamaMod;
import com.ollamamod.config.OllamaConfig;
import com.ollamamod.platform.Platform;
import com.ollamamod.session.ConversationManager;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class OllamaChatHandler {
    private final OllamaClient ollamaClient;
    private final ConversationManager conversationManager;
    private final Platform platform;
    private final CommandExecutor commandExecutor;
    private final CommandResultListener resultListener;
    private final ActionSequenceLearner sequenceLearner;
    
    // Pattern to detect commands in AI responses
    private static final Pattern COMMAND_PATTERN = Pattern.compile(
        "(?i)(?:execute|run|do|use)\\s+(?:command\\s+)?(/[^\\s]+(?:\\s+[^\\n]+)?)"
    );
    
    public OllamaChatHandler(Platform platform) {
        this.platform = platform;
        this.conversationManager = new ConversationManager();
        this.ollamaClient = new OllamaClient(conversationManager);
        this.resultListener = new CommandResultListener();
        this.commandExecutor = new CommandExecutor(resultListener);
        this.sequenceLearner = new ActionSequenceLearner();
        this.ollamaClient.setSequenceLearner(sequenceLearner);
    }
    
    public void handleChatMessage(String message, String playerName) {
        if (!OllamaConfig.enableGui && !OllamaConfig.enableChatCommand) {
            return;
        }
        
        if (!ollamaClient.isAvailable()) {
            OllamaMod.LOGGER.warn("Ollama server is not available at {}", OllamaConfig.ollamaUrl);
            return;
        }
        
        ollamaClient.sendMessage(message, playerName).thenAccept(response -> {
            if (platform.isClient()) {
                // Handle response in client
                OllamaMod.LOGGER.info("AI Response: {}", response);
                
                // Check if response contains command execution request
                if (OllamaConfig.enableCommandExecution) {
                    handleCommandExecution(response, playerName, message);
                }
            }
        }).exceptionally(throwable -> {
            OllamaMod.LOGGER.error("Error processing chat message", throwable);
            return null;
        });
    }
    
    public void handleCommandExecution(String aiResponse, String playerName, String originalMessage) {
        String command = extractCommandFromResponse(aiResponse);
        if (command == null || command.isEmpty()) {
            return;
        }
        
        // Only execute if player explicitly requested command execution
        if (!shouldExecuteCommand(command, originalMessage)) {
            return;
        }
        
        // Get command source - this will be handled by platform-specific code
        // For now, we'll need to pass this through platform interface
        OllamaMod.LOGGER.info("Executing command from AI response: {}", command);
        
        // The actual execution will be handled by platform-specific handlers
        // which will call executeCommandWithSource
    }
    
    public void executeCommandWithSource(String command, String playerName, String context, 
                                        CommandSourceStack source) {
        if (!OllamaConfig.enableCommandExecution) {
            return;
        }
        
        commandExecutor.executeCommand(command, source).thenAccept(result -> {
            // Analyze failure if command failed
            String failureReason = null;
            if (!result.success && OllamaConfig.enableFailureAnalysis) {
                failureReason = FailureReasonAnalyzer.analyzeFailure(
                    command, result.errorMessage, result.output
                );
            }
            
            // Record command learning data
            if (OllamaConfig.enableCommandLearning) {
                sequenceLearner.recordCommandWithDetails(
                    playerName, command, context, result, failureReason
                );
            }
            
            // Log result
            if (result.success) {
                OllamaMod.LOGGER.info("Command executed successfully: {}", command);
            } else {
                OllamaMod.LOGGER.warn("Command failed: {} - Reason: {}", command, failureReason);
            }
        });
    }
    
    public String extractCommandFromResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return null;
        }
        
        // Look for command pattern
        Matcher matcher = COMMAND_PATTERN.matcher(response);
        if (matcher.find()) {
            return matcher.group(1).trim();
        }
        
        // Also check for direct command mentions (e.g., "/give @s diamond 10")
        Pattern directCommand = Pattern.compile("(?:^|\\s)(/[^\\s]+(?:\\s+[^\\n\\r]+)?)");
        Matcher directMatcher = directCommand.matcher(response);
        if (directMatcher.find()) {
            String cmd = directMatcher.group(1).trim();
            // Only return if it looks like a real command (starts with /)
            if (cmd.startsWith("/")) {
                return cmd;
            }
        }
        
        return null;
    }
    
    public boolean shouldExecuteCommand(String command, String context) {
        // Only execute if context explicitly requests command execution
        if (context == null) {
            return false;
        }
        
        String contextLower = context.toLowerCase();
        return contextLower.contains("execute") || 
               contextLower.contains("run") || 
               contextLower.contains("do") || 
               contextLower.contains("use command") ||
               contextLower.contains("give me") ||
               contextLower.contains("teleport") ||
               contextLower.contains("tp me");
    }
    
    public ConversationManager getConversationManager() {
        return conversationManager;
    }
    
    public OllamaClient getOllamaClient() {
        return ollamaClient;
    }
    
    public ActionSequenceLearner getSequenceLearner() {
        return sequenceLearner;
    }
    
    public CommandExecutor getCommandExecutor() {
        return commandExecutor;
    }
    
    public CommandResultListener getResultListener() {
        return resultListener;
    }
}
