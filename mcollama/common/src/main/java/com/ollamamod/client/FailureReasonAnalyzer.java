package com.ollamamod.client;

import java.util.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

public class FailureReasonAnalyzer {
    
    // Common error patterns and their meanings
    private static final Map<Pattern, String> ERROR_PATTERNS = new HashMap<>();
    
    static {
        // Syntax errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)unknown or incomplete command"), 
            "Invalid command syntax - command not recognized");
        ERROR_PATTERNS.put(Pattern.compile("(?i)incorrect argument"), 
            "Invalid argument format - check command syntax");
        ERROR_PATTERNS.put(Pattern.compile("(?i)too many arguments"), 
            "Too many arguments provided - command has fewer parameters");
        ERROR_PATTERNS.put(Pattern.compile("(?i)not enough arguments"), 
            "Not enough arguments - command requires more parameters");
        
        // Target errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)no player was found"), 
            "Invalid player target - player does not exist or is not online");
        ERROR_PATTERNS.put(Pattern.compile("(?i)entity not found"), 
            "Invalid entity target - entity does not exist");
        ERROR_PATTERNS.put(Pattern.compile("(?i)player.*not found"), 
            "Player not found - check player name spelling");
        
        // Permission errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)don't have permission"), 
            "Insufficient permissions - player lacks required permission level");
        ERROR_PATTERNS.put(Pattern.compile("(?i)permission denied"), 
            "Permission denied - command requires higher permission level");
        ERROR_PATTERNS.put(Pattern.compile("(?i)you do not have permission"), 
            "No permission - player cannot execute this command");
        
        // Parameter errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)invalid number"), 
            "Invalid number parameter - expected numeric value");
        ERROR_PATTERNS.put(Pattern.compile("(?i)invalid.*coordinate"), 
            "Invalid coordinate - check position values");
        ERROR_PATTERNS.put(Pattern.compile("(?i)invalid.*item"), 
            "Invalid item - item name or ID not recognized");
        ERROR_PATTERNS.put(Pattern.compile("(?i)invalid.*gamemode"), 
            "Invalid gamemode - gamemode name not recognized");
        
        // Range/limit errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)out of range"), 
            "Value out of range - parameter exceeds allowed limits");
        ERROR_PATTERNS.put(Pattern.compile("(?i)too (high|low)"), 
            "Value too high or low - parameter outside valid range");
        
        // State errors
        ERROR_PATTERNS.put(Pattern.compile("(?i)already.*"), 
            "Already in that state - target already has requested property");
        ERROR_PATTERNS.put(Pattern.compile("(?i)cannot.*"), 
            "Cannot perform action - operation not possible in current state");
    }
    
    public static String analyzeFailure(String command, String errorMessage, String output) {
        if (errorMessage == null || errorMessage.trim().isEmpty()) {
            // Try to extract failure from output
            if (output != null && !output.trim().isEmpty()) {
                return analyzeOutputForFailure(command, output);
            }
            return "Unknown failure - no error message provided";
        }
        
        // First, try to match known error patterns
        String categorizedReason = categorizeFailure(errorMessage);
        if (categorizedReason != null) {
            // Extract specific details
            String details = extractFailureDetails(command, errorMessage);
            if (details != null && !details.isEmpty()) {
                return categorizedReason + " - " + details;
            }
            return categorizedReason;
        }
        
        // If no pattern matches, try to extract useful information from error message
        return extractFailureDetails(command, errorMessage);
    }
    
    public static String categorizeFailure(String errorMessage) {
        if (errorMessage == null || errorMessage.trim().isEmpty()) {
            return null;
        }
        
        String errorLower = errorMessage.toLowerCase();
        
        for (Map.Entry<Pattern, String> entry : ERROR_PATTERNS.entrySet()) {
            if (entry.getKey().matcher(errorMessage).find()) {
                return entry.getValue();
            }
        }
        
        return null;
    }
    
    public static String extractFailureDetails(String command, String errorMessage) {
        if (errorMessage == null || errorMessage.trim().isEmpty()) {
            return null;
        }
        
        StringBuilder details = new StringBuilder();
        
        // Extract player name if mentioned
        Pattern playerPattern = Pattern.compile("(?i)player ['\"]?([^'\"\\s]+)['\"]?");
        Matcher playerMatcher = playerPattern.matcher(errorMessage);
        if (playerMatcher.find()) {
            details.append("Player '").append(playerMatcher.group(1)).append("' ");
        }
        
        // Extract entity name if mentioned
        Pattern entityPattern = Pattern.compile("(?i)entity ['\"]?([^'\"\\s]+)['\"]?");
        Matcher entityMatcher = entityPattern.matcher(errorMessage);
        if (entityMatcher.find()) {
            details.append("Entity '").append(entityMatcher.group(1)).append("' ");
        }
        
        // Extract item name if mentioned
        Pattern itemPattern = Pattern.compile("(?i)item ['\"]?([^'\"\\s]+)['\"]?");
        Matcher itemMatcher = itemPattern.matcher(errorMessage);
        if (itemMatcher.find()) {
            details.append("Item '").append(itemMatcher.group(1)).append("' ");
        }
        
        // Extract coordinate if mentioned
        Pattern coordPattern = Pattern.compile("(?i)coordinate[s]? ([-\\d.]+)");
        Matcher coordMatcher = coordPattern.matcher(errorMessage);
        if (coordMatcher.find()) {
            details.append("Coordinate ").append(coordMatcher.group(1)).append(" ");
        }
        
        // Extract number if mentioned
        Pattern numberPattern = Pattern.compile("(?i)number ['\"]?([^'\"\\s]+)['\"]?");
        Matcher numberMatcher = numberPattern.matcher(errorMessage);
        if (numberMatcher.find()) {
            details.append("Number '").append(numberMatcher.group(1)).append("' ");
        }
        
        // Analyze command structure for common issues
        if (command != null) {
            String[] parts = command.trim().split("\\s+");
            String cmdName = parts.length > 0 ? parts[0].replace("/", "") : "";
            
            // Check for common command-specific issues
            if (cmdName.equals("give") && parts.length < 4) {
                details.append("Command requires format: /give <target> <item> <count>");
            } else if (cmdName.equals("tp") && parts.length < 2) {
                details.append("Command requires target or coordinates");
            } else if (cmdName.equals("gamemode") && parts.length < 2) {
                details.append("Command requires gamemode parameter");
            }
        }
        
        String result = details.toString().trim();
        return result.isEmpty() ? errorMessage : result;
    }
    
    private static String analyzeOutputForFailure(String command, String output) {
        // Check if output indicates failure
        String outputLower = output.toLowerCase();
        
        if (outputLower.contains("error") || outputLower.contains("failed") || 
            outputLower.contains("cannot") || outputLower.contains("invalid")) {
            return "Command failed - " + output;
        }
        
        return null;
    }
    
    public static FailureCategory getFailureCategory(String errorMessage) {
        if (errorMessage == null || errorMessage.trim().isEmpty()) {
            return FailureCategory.UNKNOWN;
        }
        
        String errorLower = errorMessage.toLowerCase();
        
        if (errorLower.contains("permission") || errorLower.contains("don't have permission")) {
            return FailureCategory.PERMISSION;
        } else if (errorLower.contains("not found") || errorLower.contains("does not exist")) {
            return FailureCategory.INVALID_TARGET;
        } else if (errorLower.contains("unknown") || errorLower.contains("incomplete") || 
                   errorLower.contains("incorrect argument")) {
            return FailureCategory.SYNTAX_ERROR;
        } else if (errorLower.contains("invalid number") || errorLower.contains("invalid") && 
                   (errorLower.contains("coordinate") || errorLower.contains("item"))) {
            return FailureCategory.INVALID_PARAMETER;
        } else if (errorLower.contains("too many") || errorLower.contains("not enough")) {
            return FailureCategory.ARGUMENT_COUNT;
        } else if (errorLower.contains("out of range") || errorLower.contains("too high") || 
                   errorLower.contains("too low")) {
            return FailureCategory.VALUE_RANGE;
        }
        
        return FailureCategory.UNKNOWN;
    }
    
    public enum FailureCategory {
        SYNTAX_ERROR,
        PERMISSION,
        INVALID_TARGET,
        INVALID_PARAMETER,
        ARGUMENT_COUNT,
        VALUE_RANGE,
        UNKNOWN
    }
}
