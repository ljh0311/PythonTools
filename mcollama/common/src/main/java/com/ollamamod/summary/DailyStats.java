package com.ollamamod.summary;

import java.util.*;

public class DailyStats {
    // Distance stats
    public double distanceTraveled = 0.0;
    
    // Combat stats
    public int mobsKilled = 0;
    public int deaths = 0;
    public float damageDealt = 0.0f;
    public float damageTaken = 0.0f;
    
    // Mining stats
    public Map<String, Integer> blocksMined = new HashMap<>();
    public Map<String, Double> oreProbabilities = new HashMap<>();
    public List<String> minerTypes = new ArrayList<>();
    public String minerTypeDescription = "";
    
    // Playtime stats
    public long playTimeMinutes = 0;
    public int experienceGained = 0;
    
    // Food stats
    public int totalFoodConsumed = 0;
    public double consumptionRate = 0.0; // food points per hour
    public double averageHungerLevel = 20.0;
    public List<Long> foodConsumptionEvents = new ArrayList<>();
    public Map<String, Integer> typicalFoodItems = new HashMap<>();
    public int lowHungerEvents = 0;
    
    public void reset() {
        distanceTraveled = 0.0;
        mobsKilled = 0;
        deaths = 0;
        damageDealt = 0.0f;
        damageTaken = 0.0f;
        blocksMined.clear();
        oreProbabilities.clear();
        minerTypes.clear();
        minerTypeDescription = "";
        playTimeMinutes = 0;
        experienceGained = 0;
        totalFoodConsumed = 0;
        consumptionRate = 0.0;
        averageHungerLevel = 20.0;
        foodConsumptionEvents.clear();
        typicalFoodItems.clear();
        lowHungerEvents = 0;
    }
}
