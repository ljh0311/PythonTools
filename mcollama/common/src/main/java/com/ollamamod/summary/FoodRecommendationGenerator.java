package com.ollamamod.summary;

import com.ollamamod.config.OllamaConfig;

import java.util.*;
import java.util.stream.Collectors;

public class FoodRecommendationGenerator {
    
    public static FoodRecommendation generateRecommendation(DailyStats stats, long sessionDurationMinutes) {
        if (stats.totalFoodConsumed == 0 || sessionDurationMinutes <= 0) {
            return new FoodRecommendation(
                "Not enough data to generate food recommendations yet.",
                Collections.emptyList(),
                0,
                0
            );
        }
        
        // Calculate consumption rate
        double hours = sessionDurationMinutes / 60.0;
        double consumptionRate = stats.totalFoodConsumed / hours;
        
        // Estimate typical session length (use current session or default to 2 hours)
        double typicalSessionHours = hours > 0 ? hours : 2.0;
        if (typicalSessionHours < 0.5) {
            typicalSessionHours = 2.0; // Default to 2 hours if session too short
        }
        
        // Calculate recommended food points
        double baseRecommendation = consumptionRate * typicalSessionHours;
        double recommendedFoodPoints = baseRecommendation * OllamaConfig.foodRecommendationSafetyMultiplier;
        
        // Round to reasonable values
        int minRecommended = (int) Math.ceil(recommendedFoodPoints * 0.8);
        int maxRecommended = (int) Math.ceil(recommendedFoodPoints * 1.2);
        
        // Generate item-specific recommendations
        List<String> itemRecommendations = generateItemRecommendations(
            stats.typicalFoodItems,
            minRecommended,
            maxRecommended
        );
        
        // Build recommendation message
        StringBuilder message = new StringBuilder();
        message.append("Based on your consumption patterns, carry approximately ")
               .append(minRecommended).append("-").append(maxRecommended)
               .append(" food points.\n");
        
        if (!stats.typicalFoodItems.isEmpty()) {
            message.append("You typically use: ");
            List<String> topFoods = new ArrayList<>(stats.typicalFoodItems.keySet());
            for (int i = 0; i < Math.min(3, topFoods.size()); i++) {
                if (i > 0) message.append(", ");
                message.append(topFoods.get(i));
            }
            message.append("\n");
        }
        
        return new FoodRecommendation(
            message.toString(),
            itemRecommendations,
            minRecommended,
            maxRecommended
        );
    }
    
    private static List<String> generateItemRecommendations(
            Map<String, Integer> typicalFoodItems,
            int minPoints,
            int maxPoints) {
        
        List<String> recommendations = new ArrayList<>();
        
        // Common food values (approximate)
        Map<String, Integer> foodValues = new HashMap<>();
        foodValues.put("Cooked Beef", 8);
        foodValues.put("Cooked Porkchop", 8);
        foodValues.put("Cooked Chicken", 6);
        foodValues.put("Bread", 5);
        foodValues.put("Golden Carrot", 6);
        foodValues.put("Cooked Mutton", 6);
        foodValues.put("Cooked Rabbit", 5);
        foodValues.put("Steak", 8);
        foodValues.put("Cooked Salmon", 6);
        foodValues.put("Cooked Cod", 5);
        foodValues.put("Apple", 4);
        foodValues.put("Carrot", 3);
        foodValues.put("Potato", 1);
        foodValues.put("Baked Potato", 5);
        
        // Generate recommendations for typical foods
        for (String foodItem : typicalFoodItems.keySet()) {
            Integer foodValue = findFoodValue(foodItem, foodValues);
            if (foodValue != null && foodValue > 0) {
                int minCount = (int) Math.ceil((double) minPoints / foodValue);
                int maxCount = (int) Math.ceil((double) maxPoints / foodValue);
                recommendations.add(String.format("%d-%d %s", minCount, maxCount, foodItem));
            }
        }
        
        // If no typical foods, suggest common ones
        if (recommendations.isEmpty()) {
            int beefCount = (int) Math.ceil((double) minPoints / 8);
            int breadCount = (int) Math.ceil((double) minPoints / 5);
            recommendations.add(String.format("%d-%d Cooked Beef", beefCount, (int) Math.ceil((double) maxPoints / 8)));
            recommendations.add(String.format("%d-%d Bread", breadCount, (int) Math.ceil((double) maxPoints / 5)));
        }
        
        return recommendations;
    }
    
    private static Integer findFoodValue(String foodName, Map<String, Integer> foodValues) {
        // Try exact match first
        if (foodValues.containsKey(foodName)) {
            return foodValues.get(foodName);
        }
        
        // Try partial match
        for (Map.Entry<String, Integer> entry : foodValues.entrySet()) {
            if (foodName.toLowerCase().contains(entry.getKey().toLowerCase()) ||
                entry.getKey().toLowerCase().contains(foodName.toLowerCase())) {
                return entry.getValue();
            }
        }
        
        // Default values for common patterns
        if (foodName.toLowerCase().contains("beef") || foodName.toLowerCase().contains("steak")) {
            return 8;
        }
        if (foodName.toLowerCase().contains("bread")) {
            return 5;
        }
        if (foodName.toLowerCase().contains("carrot")) {
            return foodName.toLowerCase().contains("golden") ? 6 : 3;
        }
        if (foodName.toLowerCase().contains("chicken") || foodName.toLowerCase().contains("pork")) {
            return 6;
        }
        
        return 5; // Default
    }
    
    public static class FoodRecommendation {
        public final String message;
        public final List<String> itemRecommendations;
        public final int minFoodPoints;
        public final int maxFoodPoints;
        
        public FoodRecommendation(String message, List<String> itemRecommendations,
                                 int minFoodPoints, int maxFoodPoints) {
            this.message = message;
            this.itemRecommendations = itemRecommendations;
            this.minFoodPoints = minFoodPoints;
            this.maxFoodPoints = maxFoodPoints;
        }
    }
}
