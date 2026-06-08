package com.ollamamod.world;

import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

public class WorldContext {
    public static String gatherContext(Player player) {
        if (player == null || player.level() == null) {
            return "";
        }
        
        Level level = player.level();
        BlockPos pos = player.blockPosition();
        
        StringBuilder context = new StringBuilder();
        context.append("World: ").append(level.dimension().location()).append("\n");
        context.append("Position: ").append(pos.getX()).append(", ")
               .append(pos.getY()).append(", ").append(pos.getZ()).append("\n");
        context.append("Biome: ").append(level.getBiome(pos).unwrapKey()
            .map(k -> k.location().toString()).orElse("Unknown")).append("\n");
        context.append("Time: ").append(level.getDayTime() % 24000).append(" ticks\n");
        context.append("Health: ").append(player.getHealth()).append("/")
               .append(player.getMaxHealth()).append("\n");
        
        return context.toString();
    }
    
    public static class WorldInfo {
        public final String dimension;
        public final int x, y, z;
        public final String biome;
        public final long time;
        public final float health;
        public final float maxHealth;
        
        public WorldInfo(Player player) {
            Level level = player.level();
            BlockPos pos = player.blockPosition();
            
            this.dimension = level.dimension().location().toString();
            this.x = pos.getX();
            this.y = pos.getY();
            this.z = pos.getZ();
            this.biome = level.getBiome(pos).unwrapKey()
                .map(k -> k.location().toString()).orElse("Unknown");
            this.time = level.getDayTime() % 24000;
            this.health = player.getHealth();
            this.maxHealth = player.getMaxHealth();
        }
    }
}
