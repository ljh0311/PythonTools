package com.ollamamod.config;

import java.util.ArrayList;
import java.util.List;

public class OllamaConfig {
    // Ollama Connection
    public static String ollamaUrl = "http://localhost:11434";
    public static String defaultModel = "llama2";
    public static String fallbackModel = "tinyllama";
    public static int timeoutSeconds = 30;
    
    // Features
    public static boolean enableChatCommand = true;
    public static boolean enableGui = true;
    public static boolean enableWorldContext = true;
    public static boolean enableCommandExecution = true;
    public static boolean enableBroadcast = false;
    public static boolean enableStreaming = false;
    public static boolean confirmBeforeExecute = true;
    
    // Command Execution & Learning
    public static boolean enableCommandLearning = true;
    public static boolean enableFailureAnalysis = true;
    public static int maxCommandLearningEntries = 500;
    public static List<String> commandExecutionWhitelist = new ArrayList<>();
    public static List<String> commandExecutionBlacklist = new ArrayList<>();
    
    // AI Settings
    public static String overseerPersonality = "Assistant";
    public static int maxContextTokens = 0; // 0 = unlimited
    
    // Memory Management
    public static boolean enableMemoryMonitoring = true;
    public static double memoryWarningThreshold = 0.8;
    public static boolean enableMemoryManagement = true;
    public static int memoryCleanupInterval = 300; // seconds
    
    // Daily Summary
    public static boolean enableDailySummary = true;
    public static List<String> summaryTimes = new ArrayList<>(List.of("00:00", "06:00", "12:00", "18:00"));
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
    public static int maxRecordingDuration = 0; // minutes, 0 = unlimited
    public static int patternLearningThreshold = 5;
    public static boolean autoReplicateEnabled = false;
    
    // Mining Tracking
    public static boolean enableMiningTracking = true;
    public static boolean showMinerType = true;
    public static boolean showOreProbabilities = true;
    public static int minBlocksForAnalysis = 10;
    
    // Limits
    public static int maxSessionsPerPlayer = 10;
    public static int maxPatterns = 100;
    public static int maxLearningEntries = 1000;
    public static int maxBehaviorEntries = 500;
    public static int maxRecordingQueueSize = 1000;
    public static int sessionRetentionDays = 30;
    public static int patternRetentionDays = 60;
    
    // AI Tips
    public static boolean enableAiTips = true;
    public static long tipCooldownInventoryMs = 5000;
    public static long tipCooldownBiomeMs = 10000;
    public static long tipCooldownPeriodicMs = 30000;
    public static long tipPeriodicIntervalMs = 120000;
    public static int maxTipsPerSession = 0; // 0 = unlimited
    
    // Performance
    public static boolean enableAsyncFileIO = true;
    
    public static void init() {
        // Config will be loaded by platform-specific implementations
    }
    
    public static void load() {
        // Platform-specific config loading
    }
}
