package com.ollamamod.client;

import java.util.*;

public class MiningTracker {
    private final Map<String, Integer> blocksMined = new HashMap<>();
    private final Map<String, Integer> oresMined = new HashMap<>();
    private final List<MiningEvent> miningEvents = new ArrayList<>();
    private long sessionStartTime = System.currentTimeMillis();
    
    // Known ore blocks (vanilla Minecraft)
    private static final Set<String> ORE_BLOCKS = new HashSet<>(Arrays.asList(
        "diamond_ore", "deepslate_diamond_ore",
        "iron_ore", "deepslate_iron_ore",
        "coal_ore", "deepslate_coal_ore",
        "gold_ore", "deepslate_gold_ore",
        "copper_ore", "deepslate_copper_ore",
        "emerald_ore", "deepslate_emerald_ore",
        "lapis_ore", "deepslate_lapis_ore",
        "redstone_ore", "deepslate_redstone_ore",
        "nether_gold_ore",
        "ancient_debris"
    ));
    
    public void recordBlockMined(String blockName, long timestamp) {
        if (blockName == null || blockName.isEmpty()) {
            return;
        }
        
        // Normalize block name (remove namespace if present, convert to lowercase)
        String normalizedName = normalizeBlockName(blockName);
        
        // Increment total blocks mined
        blocksMined.put(normalizedName, blocksMined.getOrDefault(normalizedName, 0) + 1);
        
        // Check if it's an ore and track separately
        if (isOre(normalizedName)) {
            oresMined.put(normalizedName, oresMined.getOrDefault(normalizedName, 0) + 1);
        }
        
        // Record event
        miningEvents.add(new MiningEvent(timestamp, normalizedName, isOre(normalizedName)));
    }
    
    public Map<String, Double> getOreProbabilities() {
        Map<String, Double> probabilities = new HashMap<>();
        int totalOres = getTotalOresMined();
        
        if (totalOres == 0) {
            return probabilities;
        }
        
        for (Map.Entry<String, Integer> entry : oresMined.entrySet()) {
            double probability = (entry.getValue() / (double) totalOres) * 100.0;
            probabilities.put(entry.getKey(), probability);
        }
        
        return probabilities;
    }
    
    public int getTotalBlocksMined() {
        return blocksMined.values().stream().mapToInt(Integer::intValue).sum();
    }
    
    public int getTotalOresMined() {
        return oresMined.values().stream().mapToInt(Integer::intValue).sum();
    }
    
    public Map<String, Integer> getBlocksMined() {
        return new HashMap<>(blocksMined);
    }
    
    public Map<String, Integer> getOresMined() {
        return new HashMap<>(oresMined);
    }
    
    public List<MiningEvent> getMiningEvents() {
        return new ArrayList<>(miningEvents);
    }
    
    public Map<String, Integer> getMiningPatterns() {
        // Return a map of block types to counts, sorted by frequency
        Map<String, Integer> patterns = new HashMap<>(blocksMined);
        return patterns;
    }
    
    public double getMiningDiversity() {
        // Calculate diversity as the number of unique block types mined
        // Higher diversity = more varied mining
        int uniqueBlocks = blocksMined.size();
        int totalBlocks = getTotalBlocksMined();
        
        if (totalBlocks == 0) {
            return 0.0;
        }
        
        // Diversity score: unique blocks / total blocks (higher is more diverse)
        return (double) uniqueBlocks / totalBlocks;
    }
    
    private String normalizeBlockName(String blockName) {
        // Remove namespace prefix (e.g., "minecraft:iron_ore" -> "iron_ore")
        if (blockName.contains(":")) {
            blockName = blockName.substring(blockName.indexOf(':') + 1);
        }
        
        // Convert to lowercase for consistency
        blockName = blockName.toLowerCase();
        
        // Handle display names - try to extract block ID
        // If it's a display name like "Iron Ore", convert to "iron_ore"
        if (blockName.contains(" ")) {
            blockName = blockName.replace(" ", "_");
        }
        
        return blockName;
    }
    
    private boolean isOre(String blockName) {
        // Check exact match first
        if (ORE_BLOCKS.contains(blockName)) {
            return true;
        }
        
        // Check if block name contains "ore" (for modded ores)
        if (blockName.contains("ore")) {
            return true;
        }
        
        // Check for specific ore patterns
        String lowerName = blockName.toLowerCase();
        return lowerName.endsWith("_ore") || lowerName.contains("_ore_");
    }
    
    public void reset() {
        blocksMined.clear();
        oresMined.clear();
        miningEvents.clear();
        sessionStartTime = System.currentTimeMillis();
    }
    
    public static class MiningEvent {
        public final long timestamp;
        public final String blockName;
        public final boolean isOre;
        
        public MiningEvent(long timestamp, String blockName, boolean isOre) {
            this.timestamp = timestamp;
            this.blockName = blockName;
            this.isOre = isOre;
        }
    }
}
