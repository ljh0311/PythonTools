package com.ollamamod.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.ollamamod.OllamaMod;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class OllamaConfig {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static Path configPath;

    // Ollama Connection
    public static String ollamaUrl = "http://localhost:11434";
    public static String defaultModel = "llama2";
    public static int timeoutSeconds = 30;

    // Features
    public static boolean enableChatCommand = true;
    public static boolean enableGui = true;
    public static boolean enableChatTrigger = true;
    public static String chatTrigger = "@ai";
    public static boolean enableWorldContext = true;
    public static boolean enableCommandExecution = true;
    public static boolean confirmBeforeExecute = true;

    // Command Execution & Learning
    public static boolean enableCommandLearning = true;
    public static boolean enableFailureAnalysis = true;
    public static int maxCommandLearningEntries = 500;
    public static List<String> commandExecutionWhitelist = new ArrayList<>();
    public static List<String> commandExecutionBlacklist = new ArrayList<>();

    // AI Settings
    public static String overseerPersonality = "Assistant";
    /** Maximum conversation turns kept per player (0 = unlimited). */
    public static int maxContextMessages = 20;

    // Daily Summary
    public static boolean enableDailySummary = true;
    public static boolean showDistanceStats = true;
    public static boolean showCombatStats = true;
    public static boolean showMiningStats = true;
    public static boolean showPlaytimeStats = true;
    public static boolean showFoodStats = true;
    public static int foodTrackingInterval = 100; // ticks (5 seconds at 20 TPS)
    public static double foodRecommendationSafetyMultiplier = 1.5;

    // Action Recording & Learning
    public static boolean enableActionRecording = true;
    public static int recordingInterval = 1; // ticks
    public static int patternLearningThreshold = 5;

    // Mining Tracking
    public static boolean enableMiningTracking = true;
    public static boolean showMinerType = true;
    public static boolean showOreProbabilities = true;
    public static int minBlocksForAnalysis = 10;

    // Limits
    public static int maxPatterns = 100;
    public static int maxLearningEntries = 1000;
    public static int maxRecordingQueueSize = 1000;

    public static void init(Path configDirectory) {
        configPath = configDirectory.resolve("ollamamod.json");
        load();
    }

    public static void load() {
        if (configPath == null) {
            OllamaMod.LOGGER.warn("Config path not set; using defaults");
            return;
        }

        if (!Files.exists(configPath)) {
            save();
            return;
        }

        try {
            String json = Files.readString(configPath);
            ConfigData data = GSON.fromJson(json, ConfigData.class);
            if (data != null) {
                apply(data);
            }
        } catch (IOException e) {
            OllamaMod.LOGGER.error("Failed to load config from {}", configPath, e);
        }
    }

    public static void save() {
        if (configPath == null) {
            OllamaMod.LOGGER.warn("Config path not set; cannot save");
            return;
        }

        try {
            Files.createDirectories(configPath.getParent());
            Files.writeString(configPath, GSON.toJson(toData()));
        } catch (IOException e) {
            OllamaMod.LOGGER.error("Failed to save config to {}", configPath, e);
        }
    }

    private static void apply(ConfigData data) {
        if (data.ollamaUrl != null) ollamaUrl = data.ollamaUrl;
        if (data.defaultModel != null) defaultModel = data.defaultModel;
        timeoutSeconds = data.timeoutSeconds;
        enableChatCommand = data.enableChatCommand;
        enableGui = data.enableGui;
        enableChatTrigger = data.enableChatTrigger;
        if (data.chatTrigger != null) chatTrigger = data.chatTrigger;
        enableWorldContext = data.enableWorldContext;
        enableCommandExecution = data.enableCommandExecution;
        confirmBeforeExecute = data.confirmBeforeExecute;
        enableCommandLearning = data.enableCommandLearning;
        enableFailureAnalysis = data.enableFailureAnalysis;
        maxCommandLearningEntries = data.maxCommandLearningEntries;
        if (data.commandExecutionWhitelist != null) {
            commandExecutionWhitelist = new ArrayList<>(data.commandExecutionWhitelist);
        }
        if (data.commandExecutionBlacklist != null) {
            commandExecutionBlacklist = new ArrayList<>(data.commandExecutionBlacklist);
        }
        if (data.overseerPersonality != null) overseerPersonality = data.overseerPersonality;
        maxContextMessages = data.maxContextMessages;
        enableDailySummary = data.enableDailySummary;
        showDistanceStats = data.showDistanceStats;
        showCombatStats = data.showCombatStats;
        showMiningStats = data.showMiningStats;
        showPlaytimeStats = data.showPlaytimeStats;
        showFoodStats = data.showFoodStats;
        foodTrackingInterval = data.foodTrackingInterval;
        foodRecommendationSafetyMultiplier = data.foodRecommendationSafetyMultiplier;
        enableActionRecording = data.enableActionRecording;
        recordingInterval = data.recordingInterval;
        patternLearningThreshold = data.patternLearningThreshold;
        enableMiningTracking = data.enableMiningTracking;
        showMinerType = data.showMinerType;
        showOreProbabilities = data.showOreProbabilities;
        minBlocksForAnalysis = data.minBlocksForAnalysis;
        maxPatterns = data.maxPatterns;
        maxLearningEntries = data.maxLearningEntries;
        maxRecordingQueueSize = data.maxRecordingQueueSize;
    }

    private static ConfigData toData() {
        ConfigData data = new ConfigData();
        data.ollamaUrl = ollamaUrl;
        data.defaultModel = defaultModel;
        data.timeoutSeconds = timeoutSeconds;
        data.enableChatCommand = enableChatCommand;
        data.enableGui = enableGui;
        data.enableChatTrigger = enableChatTrigger;
        data.chatTrigger = chatTrigger;
        data.enableWorldContext = enableWorldContext;
        data.enableCommandExecution = enableCommandExecution;
        data.confirmBeforeExecute = confirmBeforeExecute;
        data.enableCommandLearning = enableCommandLearning;
        data.enableFailureAnalysis = enableFailureAnalysis;
        data.maxCommandLearningEntries = maxCommandLearningEntries;
        data.commandExecutionWhitelist = commandExecutionWhitelist;
        data.commandExecutionBlacklist = commandExecutionBlacklist;
        data.overseerPersonality = overseerPersonality;
        data.maxContextMessages = maxContextMessages;
        data.enableDailySummary = enableDailySummary;
        data.showDistanceStats = showDistanceStats;
        data.showCombatStats = showCombatStats;
        data.showMiningStats = showMiningStats;
        data.showPlaytimeStats = showPlaytimeStats;
        data.showFoodStats = showFoodStats;
        data.foodTrackingInterval = foodTrackingInterval;
        data.foodRecommendationSafetyMultiplier = foodRecommendationSafetyMultiplier;
        data.enableActionRecording = enableActionRecording;
        data.recordingInterval = recordingInterval;
        data.patternLearningThreshold = patternLearningThreshold;
        data.enableMiningTracking = enableMiningTracking;
        data.showMinerType = showMinerType;
        data.showOreProbabilities = showOreProbabilities;
        data.minBlocksForAnalysis = minBlocksForAnalysis;
        data.maxPatterns = maxPatterns;
        data.maxLearningEntries = maxLearningEntries;
        data.maxRecordingQueueSize = maxRecordingQueueSize;
        return data;
    }

    private static class ConfigData {
        String ollamaUrl;
        String defaultModel;
        int timeoutSeconds;
        boolean enableChatCommand;
        boolean enableGui;
        boolean enableChatTrigger;
        String chatTrigger;
        boolean enableWorldContext;
        boolean enableCommandExecution;
        boolean confirmBeforeExecute;
        boolean enableCommandLearning;
        boolean enableFailureAnalysis;
        int maxCommandLearningEntries;
        List<String> commandExecutionWhitelist;
        List<String> commandExecutionBlacklist;
        String overseerPersonality;
        int maxContextMessages;
        boolean enableDailySummary;
        boolean showDistanceStats;
        boolean showCombatStats;
        boolean showMiningStats;
        boolean showPlaytimeStats;
        boolean showFoodStats;
        int foodTrackingInterval;
        double foodRecommendationSafetyMultiplier;
        boolean enableActionRecording;
        int recordingInterval;
        int patternLearningThreshold;
        boolean enableMiningTracking;
        boolean showMinerType;
        boolean showOreProbabilities;
        int minBlocksForAnalysis;
        int maxPatterns;
        int maxLearningEntries;
        int maxRecordingQueueSize;
    }
}
