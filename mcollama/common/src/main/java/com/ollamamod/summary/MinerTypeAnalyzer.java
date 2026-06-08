package com.ollamamod.summary;

import com.ollamamod.client.MiningTracker;
import com.ollamamod.config.OllamaConfig;

import java.util.*;

public class MinerTypeAnalyzer {
    
    // Ore categories for classification
    private static final Set<String> RARE_ORES = new HashSet<>(Arrays.asList(
        "diamond_ore", "deepslate_diamond_ore",
        "emerald_ore", "deepslate_emerald_ore",
        "ancient_debris"
    ));
    
    private static final Set<String> COMMON_ORES = new HashSet<>(Arrays.asList(
        "iron_ore", "deepslate_iron_ore",
        "coal_ore", "deepslate_coal_ore",
        "copper_ore", "deepslate_copper_ore"
    ));
    
    private static final Set<String> BUILDING_BLOCKS = new HashSet<>(Arrays.asList(
        "stone", "cobblestone", "deepslate", "cobbled_deepslate",
        "granite", "diorite", "andesite",
        "dirt", "grass_block", "gravel", "sand", "sandstone"
    ));
    
    private static final Set<String> REDSTONE_BLOCKS = new HashSet<>(Arrays.asList(
        "redstone_ore", "deepslate_redstone_ore",
        "redstone_block", "redstone_lamp",
        "repeater", "comparator", "redstone_torch"
    ));
    
    private static final Set<String> NETHER_BLOCKS = new HashSet<>(Arrays.asList(
        "netherrack", "nether_gold_ore", "ancient_debris",
        "nether_quartz_ore", "blackstone", "basalt"
    ));
    
    public static List<MinerType> analyzeMinerType(MiningTracker tracker) {
        List<MinerType> types = new ArrayList<>();
        
        if (tracker.getTotalBlocksMined() < OllamaConfig.minBlocksForAnalysis) {
            return types; // Not enough data
        }
        
        Map<String, Integer> blocksMined = tracker.getBlocksMined();
        Map<String, Integer> oresMined = tracker.getOresMined();
        int totalBlocks = tracker.getTotalBlocksMined();
        int totalOres = tracker.getTotalOresMined();
        double diversity = tracker.getMiningDiversity();
        
        // Calculate category percentages
        int rareOreCount = countBlocksInCategory(oresMined, RARE_ORES);
        int commonOreCount = countBlocksInCategory(oresMined, COMMON_ORES);
        int buildingBlockCount = countBlocksInCategory(blocksMined, BUILDING_BLOCKS);
        int redstoneBlockCount = countBlocksInCategory(blocksMined, REDSTONE_BLOCKS);
        int netherBlockCount = countBlocksInCategory(blocksMined, NETHER_BLOCKS);
        
        // Diamond Hunter: High percentage of rare ores
        if (totalOres > 0) {
            double rareOrePercentage = (rareOreCount / (double) totalOres) * 100.0;
            if (rareOrePercentage >= 15.0) {
                types.add(new MinerType("Diamond Hunter", rareOrePercentage / 100.0));
            }
        }
        
        // Industrial Miner: Focuses on common ores
        if (totalOres > 0) {
            double commonOrePercentage = (commonOreCount / (double) totalOres) * 100.0;
            if (commonOrePercentage >= 50.0) {
                types.add(new MinerType("Industrial Miner", commonOrePercentage / 100.0));
            }
        }
        
        // Builder: Mines many building materials
        if (totalBlocks > 0) {
            double buildingPercentage = (buildingBlockCount / (double) totalBlocks) * 100.0;
            if (buildingPercentage >= 40.0) {
                types.add(new MinerType("Builder", buildingPercentage / 100.0));
            }
        }
        
        // Redstone Engineer: Focuses on redstone-related blocks
        if (totalBlocks > 0) {
            double redstonePercentage = (redstoneBlockCount / (double) totalBlocks) * 100.0;
            if (redstonePercentage >= 10.0) {
                types.add(new MinerType("Redstone Engineer", redstonePercentage / 100.0));
            }
        }
        
        // Nether Miner: Mines nether-specific blocks
        if (totalBlocks > 0) {
            double netherPercentage = (netherBlockCount / (double) totalBlocks) * 100.0;
            if (netherPercentage >= 20.0) {
                types.add(new MinerType("Nether Miner", netherPercentage / 100.0));
            }
        }
        
        // Explorer: High diversity (mines many different block types)
        if (diversity >= 0.15) {
            types.add(new MinerType("Explorer", diversity));
        }
        
        // Generalist: Balanced mining (no strong preference, but has mined enough)
        if (types.isEmpty() && totalBlocks >= 50) {
            types.add(new MinerType("Generalist", 0.5));
        }
        
        // Sort by confidence score (highest first)
        types.sort((a, b) -> Double.compare(b.confidence, a.confidence));
        
        return types;
    }
    
    public static String generateMinerDescription(List<MinerType> types) {
        if (types.isEmpty()) {
            return "Insufficient mining data";
        }
        
        if (types.size() == 1) {
            return types.get(0).name;
        }
        
        // Multiple types - combine them
        StringBuilder description = new StringBuilder();
        for (int i = 0; i < Math.min(types.size(), 3); i++) {
            if (i > 0) {
                description.append(", ");
            }
            description.append(types.get(i).name);
        }
        
        return description.toString();
    }
    
    private static int countBlocksInCategory(Map<String, Integer> blocks, Set<String> category) {
        int count = 0;
        for (Map.Entry<String, Integer> entry : blocks.entrySet()) {
            String blockName = entry.getKey().toLowerCase();
            // Check if block name matches any in category
            for (String categoryBlock : category) {
                if (blockName.contains(categoryBlock) || categoryBlock.contains(blockName)) {
                    count += entry.getValue();
                    break;
                }
            }
        }
        return count;
    }
    
    public static class MinerType {
        public final String name;
        public final double confidence; // 0.0 to 1.0
        
        public MinerType(String name, double confidence) {
            this.name = name;
            this.confidence = Math.max(0.0, Math.min(1.0, confidence));
        }
    }
}
