package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;

import java.util.*;

public class ActionSequenceLearner {
    private final Map<String, List<BehaviorPattern>> learnedPatterns = new HashMap<>();
    private final Map<String, List<CommandLearningData>> learningData = new HashMap<>();
    
    public void learnSequence(String playerId, List<PlayerActionRecorder.RecordedAction> sequence) {
        if (sequence.size() < OllamaConfig.patternLearningThreshold) {
            return;
        }
        
        List<BehaviorPattern> patterns = learnedPatterns.computeIfAbsent(playerId, k -> new ArrayList<>());
        
        // Simple pattern detection - find repeated sequences
        Map<List<String>, Integer> sequenceCounts = new HashMap<>();
        
        for (int i = 0; i <= sequence.size() - 3; i++) {
            List<String> subSequence = new ArrayList<>();
            for (int j = i; j < Math.min(i + 3, sequence.size()); j++) {
                subSequence.add(sequence.get(j).x + "," + sequence.get(j).y + "," + sequence.get(j).z);
            }
            sequenceCounts.put(subSequence, sequenceCounts.getOrDefault(subSequence, 0) + 1);
        }
        
        // Create patterns for frequently occurring sequences
        for (Map.Entry<List<String>, Integer> entry : sequenceCounts.entrySet()) {
            if (entry.getValue() >= OllamaConfig.patternLearningThreshold) {
                BehaviorPattern pattern = new BehaviorPattern(
                    entry.getKey(),
                    entry.getValue(),
                    System.currentTimeMillis()
                );
                patterns.add(pattern);
            }
        }
        
        // Limit patterns per player
        if (patterns.size() > OllamaConfig.maxPatterns) {
            patterns.sort(Comparator.comparingLong(BehaviorPattern::getLastSeen).reversed());
            patterns.subList(OllamaConfig.maxPatterns, patterns.size()).clear();
        }
    }
    
    public List<BehaviorPattern> getPatterns(String playerId) {
        return learnedPatterns.getOrDefault(playerId, Collections.emptyList());
    }
    
    public void recordCommand(String playerId, String command, String context, boolean success) {
        List<CommandLearningData> data = learningData.computeIfAbsent(playerId, k -> new ArrayList<>());
        data.add(new CommandLearningData(command, context, success, System.currentTimeMillis()));
        
        if (data.size() > OllamaConfig.maxLearningEntries) {
            data.subList(0, data.size() - OllamaConfig.maxLearningEntries).clear();
        }
    }
    
    public void recordCommandWithDetails(String playerId, String command, String context, 
                                        CommandExecutor.CommandResult result, String failureReason) {
        if (!OllamaConfig.enableCommandLearning) {
            return;
        }
        
        List<CommandLearningData> data = learningData.computeIfAbsent(playerId, k -> new ArrayList<>());
        
        Map<String, String> additionalContext = new HashMap<>();
        additionalContext.put("resultCode", String.valueOf(result.resultCode));
        
        CommandLearningData learningData = new CommandLearningData(
            command, context, result.success, result.timestamp,
            failureReason, result.output, result.errorMessage, additionalContext
        );
        
        data.add(learningData);
        
        if (data.size() > OllamaConfig.maxCommandLearningEntries) {
            data.subList(0, data.size() - OllamaConfig.maxCommandLearningEntries).clear();
        }
    }
    
    public List<FailurePattern> getFailurePatterns(String playerId, String commandType) {
        List<CommandLearningData> data = learningData.getOrDefault(playerId, Collections.emptyList());
        Map<String, Integer> failureReasons = new HashMap<>();
        Map<String, Integer> failureCategories = new HashMap<>();
        
        for (CommandLearningData entry : data) {
            if (!entry.success && entry.command.startsWith("/" + commandType)) {
                if (entry.failureReason != null && !entry.failureReason.isEmpty()) {
                    failureReasons.put(entry.failureReason, 
                        failureReasons.getOrDefault(entry.failureReason, 0) + 1);
                    
                    FailureReasonAnalyzer.FailureCategory category = 
                        FailureReasonAnalyzer.getFailureCategory(entry.errorMessage);
                    failureCategories.put(category.name(), 
                        failureCategories.getOrDefault(category.name(), 0) + 1);
                }
            }
        }
        
        List<FailurePattern> patterns = new ArrayList<>();
        for (Map.Entry<String, Integer> entry : failureReasons.entrySet()) {
            patterns.add(new FailurePattern(entry.getKey(), entry.getValue(), 
                FailureReasonAnalyzer.getFailureCategory(entry.getKey())));
        }
        
        patterns.sort((a, b) -> Integer.compare(b.frequency, a.frequency));
        return patterns;
    }
    
    public String suggestCommandCorrection(String command, String failureReason) {
        if (failureReason == null || failureReason.isEmpty()) {
            return null;
        }
        
        String[] parts = command.trim().split("\\s+");
        if (parts.length == 0) {
            return null;
        }
        
        String cmdName = parts[0].replace("/", "");
        String suggestion = null;
        
        // Common corrections based on failure reasons
        if (failureReason.contains("not enough arguments")) {
            if (cmdName.equals("give") && parts.length < 4) {
                suggestion = command + " <count>";
            } else if (cmdName.equals("tp") && parts.length < 2) {
                suggestion = command + " <target>";
            } else if (cmdName.equals("gamemode") && parts.length < 2) {
                suggestion = command + " <gamemode>";
            }
        } else if (failureReason.contains("too many arguments")) {
            // Suggest removing extra arguments
            if (cmdName.equals("give") && parts.length > 4) {
                suggestion = "/give " + (parts.length > 1 ? parts[1] : "@s") + " " + 
                           (parts.length > 2 ? parts[2] : "diamond") + " " + 
                           (parts.length > 3 ? parts[3] : "1");
            }
        } else if (failureReason.contains("invalid number")) {
            // Find and suggest fixing the number parameter
            for (int i = 1; i < parts.length; i++) {
                try {
                    Integer.parseInt(parts[i]);
                    // This is a number, but might be wrong format
                    suggestion = "Check number parameter at position " + i;
                    break;
                } catch (NumberFormatException e) {
                    // Not a number, continue
                }
            }
        } else if (failureReason.contains("player not found") || 
                   failureReason.contains("entity not found")) {
            suggestion = "Check player/entity name spelling - use @s for self, @p for nearest player";
        }
        
        return suggestion;
    }
    
    public double getCommandSuccessRate(String playerId, String command) {
        List<CommandLearningData> data = learningData.getOrDefault(playerId, Collections.emptyList());
        if (data.isEmpty()) {
            return 0.0;
        }
        
        int total = 0;
        int successful = 0;
        
        for (CommandLearningData entry : data) {
            if (entry.command.equals(command) || entry.command.startsWith(command)) {
                total++;
                if (entry.success) {
                    successful++;
                }
            }
        }
        
        if (total == 0) {
            return 0.0;
        }
        
        return (successful / (double) total) * 100.0;
    }
    
    public List<CommandLearningData> getCommandHistory(String playerId, String commandType) {
        List<CommandLearningData> data = learningData.getOrDefault(playerId, Collections.emptyList());
        List<CommandLearningData> filtered = new ArrayList<>();
        
        for (CommandLearningData entry : data) {
            if (commandType == null || entry.command.startsWith("/" + commandType) || 
                entry.command.startsWith(commandType)) {
                filtered.add(entry);
            }
        }
        
        return filtered;
    }
    
    public static class FailurePattern {
        public final String reason;
        public final int frequency;
        public final FailureReasonAnalyzer.FailureCategory category;
        
        public FailurePattern(String reason, int frequency, 
                            FailureReasonAnalyzer.FailureCategory category) {
            this.reason = reason;
            this.frequency = frequency;
            this.category = category;
        }
    }
    
    public static class BehaviorPattern {
        private final List<String> sequence;
        private final int frequency;
        private final long lastSeen;
        
        public BehaviorPattern(List<String> sequence, int frequency, long lastSeen) {
            this.sequence = sequence;
            this.frequency = frequency;
            this.lastSeen = lastSeen;
        }
        
        public List<String> getSequence() {
            return sequence;
        }
        
        public int getFrequency() {
            return frequency;
        }
        
        public long getLastSeen() {
            return lastSeen;
        }
    }
    
    public static class CommandLearningData {
        public final String command;
        public final String context;
        public final boolean success;
        public final long timestamp;
        public final String failureReason;
        public final String commandOutput;
        public final String errorMessage;
        public final Map<String, String> additionalContext;
        
        // Legacy constructor for backward compatibility
        public CommandLearningData(String command, String context, boolean success, long timestamp) {
            this(command, context, success, timestamp, null, null, null, null);
        }
        
        // Full constructor with all fields
        public CommandLearningData(String command, String context, boolean success, long timestamp,
                                  String failureReason, String commandOutput, String errorMessage,
                                  Map<String, String> additionalContext) {
            this.command = command;
            this.context = context;
            this.success = success;
            this.timestamp = timestamp;
            this.failureReason = failureReason;
            this.commandOutput = commandOutput;
            this.errorMessage = errorMessage;
            this.additionalContext = additionalContext != null ? new HashMap<>(additionalContext) : new HashMap<>();
        }
    }
}
