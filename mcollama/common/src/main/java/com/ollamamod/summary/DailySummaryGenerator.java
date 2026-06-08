package com.ollamamod.summary;

import com.ollamamod.config.OllamaConfig;

import java.text.DecimalFormat;
import java.time.LocalDate;
import java.util.*;

public class DailySummaryGenerator {
    private static final DecimalFormat DECIMAL_FORMAT = new DecimalFormat("#.##");
    
    public static String generateDailySummary(String playerName) {
        DailyStats stats = DailyStatsTracker.getPlayerStats(playerName);
        long sessionDuration = DailyStatsTracker.getSessionDuration(playerName);
        
        if (stats == null) {
            return "No statistics available for today.";
        }
        
        StringBuilder summary = new StringBuilder();
        summary.append("§6=== Daily Summary ===\n");
        summary.append("§7Date: ").append(LocalDate.now()).append("\n\n");
        
        // Distance stats
        if (OllamaConfig.showDistanceStats && stats.distanceTraveled > 0) {
            summary.append("§bDistance Traveled: §f")
                   .append(DECIMAL_FORMAT.format(stats.distanceTraveled))
                   .append(" blocks\n");
        }
        
        // Combat stats
        if (OllamaConfig.showCombatStats) {
            summary.append("§cCombat Stats:\n");
            summary.append("  §7Mobs Killed: §f").append(stats.mobsKilled).append("\n");
            summary.append("  §7Deaths: §f").append(stats.deaths).append("\n");
            summary.append("  §7Damage Dealt: §f").append(DECIMAL_FORMAT.format(stats.damageDealt)).append("\n");
            summary.append("  §7Damage Taken: §f").append(DECIMAL_FORMAT.format(stats.damageTaken)).append("\n");
        }
        
        // Mining stats
        if (OllamaConfig.showMiningStats && !stats.blocksMined.isEmpty()) {
            summary.append("§eMining Stats:\n");
            
            // Show miner type if available
            if (OllamaConfig.showMinerType && !stats.minerTypeDescription.isEmpty() && 
                !stats.minerTypeDescription.equals("Insufficient mining data")) {
                summary.append("  §7Miner Type: §f").append(stats.minerTypeDescription).append("\n");
            }
            
            // Calculate totals
            int totalBlocks = stats.blocksMined.values().stream().mapToInt(Integer::intValue).sum();
            int totalOres = 0;
            // Calculate total ores by summing counts of blocks that are in oreProbabilities
            if (!stats.oreProbabilities.isEmpty()) {
                for (String oreName : stats.oreProbabilities.keySet()) {
                    totalOres += stats.blocksMined.getOrDefault(oreName, 0);
                }
            }
            
            summary.append("  §7Total Blocks Mined: §f").append(totalBlocks).append("\n");
            if (totalOres > 0) {
                summary.append("  §7Total Ores Mined: §f").append(totalOres).append("\n");
            }
            
            // Show ore probabilities if enabled
            if (OllamaConfig.showOreProbabilities && !stats.oreProbabilities.isEmpty()) {
                summary.append("  §7Ore Probabilities:\n");
                stats.oreProbabilities.entrySet().stream()
                    .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                    .forEach(entry -> {
                        String blockName = formatBlockName(entry.getKey());
                        summary.append("    §7").append(blockName)
                               .append(": §f").append(DECIMAL_FORMAT.format(entry.getValue()))
                               .append("%\n");
                    });
            }
            
            // Show top mined blocks
            summary.append("  §7Top Mined Blocks:\n");
            stats.blocksMined.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .limit(5)
                .forEach(entry -> {
                    String blockName = formatBlockName(entry.getKey());
                    summary.append("    §7").append(blockName)
                           .append(": §f").append(entry.getValue()).append("\n");
                });
        }
        
        // Playtime stats
        if (OllamaConfig.showPlaytimeStats) {
            summary.append("§aPlay Time: §f")
                   .append(DECIMAL_FORMAT.format(stats.playTimeMinutes))
                   .append(" minutes\n");
        }
        
        // Food consumption stats
        if (OllamaConfig.showFoodStats) {
            summary.append("\n§6Food Consumption Stats:\n");
            summary.append("  §7Food Consumed Today: §f").append(stats.totalFoodConsumed).append(" points\n");
            
            if (stats.consumptionRate > 0) {
                summary.append("  §7Average Consumption: §f")
                       .append(DECIMAL_FORMAT.format(stats.consumptionRate))
                       .append(" points/hour\n");
            }
            
            summary.append("  §7Average Hunger Level: §f")
                   .append(DECIMAL_FORMAT.format(stats.averageHungerLevel))
                   .append("/20\n");
            
            if (stats.lowHungerEvents > 0) {
                summary.append("  §7Low Hunger Events: §f").append(stats.lowHungerEvents).append(" times\n");
            }
        }
        
        // Food recommendation
        if (OllamaConfig.showFoodStats && stats.totalFoodConsumed > 0) {
            FoodRecommendationGenerator.FoodRecommendation recommendation = 
                FoodRecommendationGenerator.generateRecommendation(stats, sessionDuration);
            
            if (recommendation != null && !recommendation.message.isEmpty()) {
                summary.append("\n§6Food Recommendation:\n");
                summary.append("  §7").append(recommendation.message.replace("\n", "\n  §7"));
                
                if (!recommendation.itemRecommendations.isEmpty()) {
                    summary.append("\n  §7Recommendation: §f");
                    for (int i = 0; i < recommendation.itemRecommendations.size(); i++) {
                        if (i > 0) summary.append(" or ");
                        summary.append(recommendation.itemRecommendations.get(i));
                    }
                    summary.append("\n");
                }
            }
        }
        
        return summary.toString();
    }
    
    private static String formatBlockName(String blockName) {
        // Convert block names like "iron_ore" to "Iron Ore"
        if (blockName == null || blockName.isEmpty()) {
            return blockName;
        }
        
        // Handle underscores and capitalization
        String[] parts = blockName.split("_");
        StringBuilder formatted = new StringBuilder();
        
        for (int i = 0; i < parts.length; i++) {
            if (i > 0) {
                formatted.append(" ");
            }
            if (!parts[i].isEmpty()) {
                formatted.append(Character.toUpperCase(parts[i].charAt(0)));
                if (parts[i].length() > 1) {
                    formatted.append(parts[i].substring(1));
                }
            }
        }
        
        return formatted.toString();
    }
}
