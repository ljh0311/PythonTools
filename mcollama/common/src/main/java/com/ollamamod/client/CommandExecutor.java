package com.ollamamod.client;

import com.ollamamod.OllamaMod;
import com.ollamamod.config.OllamaConfig;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public class CommandExecutor {
    private final CommandResultListener resultListener;
    private static final Set<String> DESTRUCTIVE_COMMANDS = new HashSet<>(Arrays.asList(
        "kill", "ban", "kick", "deop", "stop", "save-all", "save-off"
    ));
    
    public CommandExecutor(CommandResultListener resultListener) {
        this.resultListener = resultListener;
    }
    
    public CompletableFuture<CommandResult> executeCommand(String command, CommandSourceStack source) {
        return CompletableFuture.supplyAsync(() -> {
            if (!OllamaConfig.enableCommandExecution) {
                return new CommandResult(false, "Command execution is disabled", 
                    "Command execution is disabled in configuration", 0, System.currentTimeMillis());
            }
            
            // Validate command safety
            if (!isCommandSafe(command)) {
                return new CommandResult(false, "Command is not safe to execute", 
                    "Command is in blacklist or requires confirmation", 0, System.currentTimeMillis());
            }
            
            // Check if command requires confirmation
            if (OllamaConfig.confirmBeforeExecute && requiresConfirmation(command)) {
                return new CommandResult(false, "Command requires confirmation", 
                    "Destructive commands require player confirmation", 0, System.currentTimeMillis());
            }
            
            try {
                // Check if we have a server (server-side execution)
                if (source.getServer() == null) {
                    return new CommandResult(false, "", 
                        "Command execution requires server-side context", 0, System.currentTimeMillis());
                }
                
                // Register listener for this command
                String commandId = UUID.randomUUID().toString();
                resultListener.registerCommand(commandId, command);
                
                // Execute command
                int resultCode = source.getServer().getCommands().performCommand(
                    source, command
                );
                
                // Wait briefly for command output to be captured
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                
                // Get captured output
                CommandResultListener.CapturedResult captured = resultListener.getResult(commandId);
                resultListener.unregisterCommand(commandId);
                
                boolean success = resultCode > 0;
                String output = captured != null ? captured.output : "";
                String errorMessage = captured != null ? captured.errorMessage : "";
                
                // If no output captured but command succeeded, assume success
                if (success && (output == null || output.isEmpty())) {
                    output = "Command executed successfully";
                }
                
                return new CommandResult(success, output, errorMessage, resultCode, System.currentTimeMillis());
                
            } catch (Exception e) {
                OllamaMod.LOGGER.error("Error executing command: {}", command, e);
                return new CommandResult(false, "", 
                    "Error executing command: " + e.getMessage(), 0, System.currentTimeMillis());
            }
        });
    }
    
    public boolean isCommandSafe(String command) {
        if (command == null || command.trim().isEmpty()) {
            return false;
        }
        
        String commandLower = command.toLowerCase().trim();
        
        // Check blacklist
        if (!OllamaConfig.commandExecutionBlacklist.isEmpty()) {
            for (String blacklisted : OllamaConfig.commandExecutionBlacklist) {
                if (commandLower.startsWith("/" + blacklisted.toLowerCase()) || 
                    commandLower.startsWith(blacklisted.toLowerCase())) {
                    return false;
                }
            }
        }
        
        // Check whitelist (if not empty, only whitelisted commands are allowed)
        if (!OllamaConfig.commandExecutionWhitelist.isEmpty()) {
            boolean whitelisted = false;
            for (String whitelistedCmd : OllamaConfig.commandExecutionWhitelist) {
                if (commandLower.startsWith("/" + whitelistedCmd.toLowerCase()) || 
                    commandLower.startsWith(whitelistedCmd.toLowerCase())) {
                    whitelisted = true;
                    break;
                }
            }
            if (!whitelisted) {
                return false;
            }
        }
        
        return true;
    }
    
    private boolean requiresConfirmation(String command) {
        String commandLower = command.toLowerCase().trim();
        for (String destructive : DESTRUCTIVE_COMMANDS) {
            if (commandLower.startsWith("/" + destructive) || commandLower.startsWith(destructive)) {
                return true;
            }
        }
        return false;
    }
    
    public static class CommandResult {
        public final boolean success;
        public final String output;
        public final String errorMessage;
        public final int resultCode;
        public final long timestamp;
        
        public CommandResult(boolean success, String output, String errorMessage, 
                           int resultCode, long timestamp) {
            this.success = success;
            this.output = output != null ? output : "";
            this.errorMessage = errorMessage != null ? errorMessage : "";
            this.resultCode = resultCode;
            this.timestamp = timestamp;
        }
    }
}
