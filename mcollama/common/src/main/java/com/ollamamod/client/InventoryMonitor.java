package com.ollamamod.client;

import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.food.FoodProperties;

import java.util.*;
import java.util.LinkedHashMap;

public class InventoryMonitor {
    private final Map<String, Integer> foodItemFrequency = new HashMap<>();
    private final Map<String, Integer> foodItemCounts = new HashMap<>();
    private int scanCount = 0;
    
    public void scanInventory(Player player) {
        if (player == null || player.getInventory() == null) {
            return;
        }
        
        scanCount++;
        Set<String> currentFoodItems = new HashSet<>();
        
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack stack = player.getInventory().getItem(i);
            if (!stack.isEmpty() && stack.getItem().getFoodProperties() != null) {
                String itemName = getItemDisplayName(stack);
                int count = stack.getCount();
                
                currentFoodItems.add(itemName);
                foodItemCounts.put(itemName, foodItemCounts.getOrDefault(itemName, 0) + count);
            }
        }
        
        // Update frequency (how often this food appears in inventory)
        for (String foodItem : currentFoodItems) {
            foodItemFrequency.put(foodItem, foodItemFrequency.getOrDefault(foodItem, 0) + 1);
        }
    }
    
    public Map<String, Integer> getTypicalFoodItems() {
        // Return top 5 most frequently seen food items
        return foodItemFrequency.entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .limit(5)
            .collect(LinkedHashMap::new, 
                (map, entry) -> map.put(entry.getKey(), entry.getValue()),
                LinkedHashMap::putAll);
    }
    
    public Map<String, Integer> getFoodItemCounts() {
        return new HashMap<>(foodItemCounts);
    }
    
    public int getTotalFoodValue(Player player) {
        if (player == null || player.getInventory() == null) {
            return 0;
        }
        
        int totalFoodPoints = 0;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack stack = player.getInventory().getItem(i);
            if (!stack.isEmpty()) {
                FoodProperties food = stack.getItem().getFoodProperties();
                if (food != null) {
                    totalFoodPoints += food.getNutrition() * stack.getCount();
                }
            }
        }
        return totalFoodPoints;
    }
    
    private String getItemDisplayName(ItemStack stack) {
        try {
            return stack.getDisplayName().getString();
        } catch (Exception e) {
            return stack.getItem().toString();
        }
    }
    
    public void reset() {
        foodItemFrequency.clear();
        foodItemCounts.clear();
        scanCount = 0;
    }
    
    public int getScanCount() {
        return scanCount;
    }
}
