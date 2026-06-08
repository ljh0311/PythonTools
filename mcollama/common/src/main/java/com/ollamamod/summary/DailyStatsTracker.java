package com.ollamamod.summary;

import com.ollamamod.client.FoodConsumptionTracker;
import com.ollamamod.client.InventoryMonitor;
import com.ollamamod.client.MiningTracker;
import com.ollamamod.config.OllamaConfig;
import net.minecraft.world.entity.player.Player;

import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class DailyStatsTracker {
    private static final Map<String, DailyStats> playerStats = new ConcurrentHashMap<>();
    private static final Map<String, FoodConsumptionTracker> foodTrackers = new ConcurrentHashMap<>();
    private static final Map<String, InventoryMonitor> inventoryMonitors = new ConcurrentHashMap<>();
    private static final Map<String, MiningTracker> miningTrackers = new ConcurrentHashMap<>();
    private static final Map<String, LocalDate> lastResetDate = new ConcurrentHashMap<>();
    private static final Map<String, Long> sessionStartTimes = new ConcurrentHashMap<>();
    
    public static void updatePlayerStats(Player player) {
        if (player == null) {
            return;
        }
        
        String playerName = player.getName().getString();
        LocalDate currentDate = LocalDate.now();
        
        // Reset stats if new day
        LocalDate lastReset = lastResetDate.get(playerName);
        if (lastReset == null || !lastReset.equals(currentDate)) {
            resetPlayerStats(playerName);
            lastResetDate.put(playerName, currentDate);
        }
        
        DailyStats stats = playerStats.computeIfAbsent(playerName, k -> new DailyStats());
        FoodConsumptionTracker foodTracker = foodTrackers.computeIfAbsent(playerName, k -> new FoodConsumptionTracker());
        InventoryMonitor inventoryMonitor = inventoryMonitors.computeIfAbsent(playerName, k -> new InventoryMonitor());
        MiningTracker miningTracker = miningTrackers.computeIfAbsent(playerName, k -> new MiningTracker());
        
        // Track food consumption
        int currentFoodLevel = player.getFoodData().getFoodLevel();
        long currentTime = System.currentTimeMillis();
        foodTracker.recordFoodLevel(currentFoodLevel, currentTime);
        
        // Update food stats
        stats.totalFoodConsumed = foodTracker.getTotalFoodConsumed();
        stats.consumptionRate = foodTracker.getConsumptionRate();
        stats.averageHungerLevel = foodTracker.getAverageHungerLevel();
        stats.lowHungerEvents = foodTracker.getLowHungerEvents();
        
        // Update consumption events (store timestamps)
        stats.foodConsumptionEvents.clear();
        for (FoodConsumptionTracker.ConsumptionEvent event : foodTracker.getConsumptionEvents()) {
            stats.foodConsumptionEvents.add(event.timestamp);
        }
        
        // Scan inventory periodically
        if (player.tickCount % OllamaConfig.foodTrackingInterval == 0) {
            inventoryMonitor.scanInventory(player);
            stats.typicalFoodItems = inventoryMonitor.getTypicalFoodItems();
        }
        
        // Update mining stats
        if (OllamaConfig.enableMiningTracking) {
            stats.blocksMined = miningTracker.getBlocksMined();
            stats.oreProbabilities = miningTracker.getOreProbabilities();
            
            // Analyze miner type
            List<MinerTypeAnalyzer.MinerType> minerTypes = MinerTypeAnalyzer.analyzeMinerType(miningTracker);
            stats.minerTypes.clear();
            for (MinerTypeAnalyzer.MinerType type : minerTypes) {
                stats.minerTypes.add(type.name);
            }
            stats.minerTypeDescription = MinerTypeAnalyzer.generateMinerDescription(minerTypes);
        }
    }
    
    public static DailyStats getPlayerStats(String playerName) {
        return playerStats.getOrDefault(playerName, new DailyStats());
    }
    
    public static void resetPlayerStats(String playerName) {
        DailyStats stats = playerStats.get(playerName);
        if (stats != null) {
            stats.reset();
        }
        
        FoodConsumptionTracker tracker = foodTrackers.get(playerName);
        if (tracker != null) {
            tracker.reset();
        }
        
        InventoryMonitor monitor = inventoryMonitors.get(playerName);
        if (monitor != null) {
            monitor.reset();
        }
        
        MiningTracker miningTracker = miningTrackers.get(playerName);
        if (miningTracker != null) {
            miningTracker.reset();
        }
        
        sessionStartTimes.put(playerName, System.currentTimeMillis());
    }
    
    public static MiningTracker getMiningTracker(String playerName) {
        return miningTrackers.computeIfAbsent(playerName, k -> new MiningTracker());
    }
    
    public static long getSessionDuration(String playerName) {
        Long startTime = sessionStartTimes.get(playerName);
        if (startTime == null) {
            sessionStartTimes.put(playerName, System.currentTimeMillis());
            return 0;
        }
        return (System.currentTimeMillis() - startTime) / (1000 * 60); // minutes
    }
    
    public static Map<String, DailyStats> getAllPlayerStats() {
        return new HashMap<>(playerStats);
    }
    
    // Compatibility method for existing code that calls generateDailySummary
    public static String generateDailySummary(String playerName) {
        return DailySummaryGenerator.generateDailySummary(playerName);
    }
}
