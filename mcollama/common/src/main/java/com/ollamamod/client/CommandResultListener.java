package com.ollamamod.client;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class CommandResultListener {
    private final Map<String, CommandInfo> pendingCommands = new ConcurrentHashMap<>();
    private final Map<String, CapturedResult> capturedResults = new ConcurrentHashMap<>();
    
    public void registerCommand(String commandId, String command) {
        pendingCommands.put(commandId, new CommandInfo(command, System.currentTimeMillis()));
    }
    
    public void unregisterCommand(String commandId) {
        pendingCommands.remove(commandId);
        // Keep captured results for a short time in case of delayed capture
        new Thread(() -> {
            try {
                Thread.sleep(5000); // Keep for 5 seconds
                capturedResults.remove(commandId);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }).start();
    }
    
    public void captureOutput(String commandId, String output, boolean isError) {
        CapturedResult result = capturedResults.computeIfAbsent(commandId, 
            k -> new CapturedResult());
        
        if (isError) {
            if (result.errorMessage == null || result.errorMessage.isEmpty()) {
                result.errorMessage = output;
            } else {
                result.errorMessage += "\n" + output;
            }
        } else {
            if (result.output == null || result.output.isEmpty()) {
                result.output = output;
            } else {
                result.output += "\n" + output;
            }
        }
    }
    
    public CapturedResult getResult(String commandId) {
        return capturedResults.get(commandId);
    }
    
    public boolean hasPendingCommand(String commandId) {
        return pendingCommands.containsKey(commandId);
    }
    
    public List<String> getAllPendingCommandIds() {
        return new ArrayList<>(pendingCommands.keySet());
    }
    
    public static class CommandInfo {
        public final String command;
        public final long timestamp;
        
        public CommandInfo(String command, long timestamp) {
            this.command = command;
            this.timestamp = timestamp;
        }
    }
    
    public static class CapturedResult {
        public String output = "";
        public String errorMessage = "";
        
        public CapturedResult() {
        }
        
        public CapturedResult(String output, String errorMessage) {
            this.output = output != null ? output : "";
            this.errorMessage = errorMessage != null ? errorMessage : "";
        }
    }
}
