package com.ollamamod.client;

import java.util.*;

public class FoodConsumptionTracker {
    private int previousFoodLevel = 20;
    private final List<ConsumptionEvent> consumptionEvents = new ArrayList<>();
    private final List<Integer> hungerLevels = new ArrayList<>();
    private long sessionStartTime = System.currentTimeMillis();
    private int totalFoodConsumed = 0;
    private int lowHungerCount = 0;
    
    public void recordFoodLevel(int currentLevel, long timestamp) {
        // Track hunger levels for average calculation
        hungerLevels.add(currentLevel);
        
        // Detect consumption (food level decreased)
        if (currentLevel < previousFoodLevel) {
            int consumed = previousFoodLevel - currentLevel;
            totalFoodConsumed += consumed;
            
            consumptionEvents.add(new ConsumptionEvent(timestamp, consumed, currentLevel));
        }
        
        // Track low hunger events (below 6 food points)
        if (currentLevel < 6 && previousFoodLevel >= 6) {
            lowHungerCount++;
        }
        
        previousFoodLevel = currentLevel;
    }
    
    public double getConsumptionRate() {
        long sessionDuration = System.currentTimeMillis() - sessionStartTime;
        if (sessionDuration <= 0) {
            return 0.0;
        }
        
        // Convert to hours
        double hours = sessionDuration / (1000.0 * 60.0 * 60.0);
        if (hours <= 0) {
            return 0.0;
        }
        
        return totalFoodConsumed / hours;
    }
    
    public int getTotalFoodConsumed() {
        return totalFoodConsumed;
    }
    
    public double getAverageHungerLevel() {
        if (hungerLevels.isEmpty()) {
            return 20.0;
        }
        
        int sum = hungerLevels.stream().mapToInt(Integer::intValue).sum();
        return sum / (double) hungerLevels.size();
    }
    
    public List<ConsumptionEvent> getConsumptionEvents() {
        return new ArrayList<>(consumptionEvents);
    }
    
    public int getLowHungerEvents() {
        return lowHungerCount;
    }
    
    public void reset() {
        previousFoodLevel = 20;
        consumptionEvents.clear();
        hungerLevels.clear();
        sessionStartTime = System.currentTimeMillis();
        totalFoodConsumed = 0;
        lowHungerCount = 0;
    }
    
    public static class ConsumptionEvent {
        public final long timestamp;
        public final int amountConsumed;
        public final int hungerLevelAfter;
        
        public ConsumptionEvent(long timestamp, int amountConsumed, int hungerLevelAfter) {
            this.timestamp = timestamp;
            this.amountConsumed = amountConsumed;
            this.hungerLevelAfter = hungerLevelAfter;
        }
    }
}
