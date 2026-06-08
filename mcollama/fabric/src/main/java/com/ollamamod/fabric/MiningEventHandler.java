package com.ollamamod.fabric;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.summary.DailyStatsTracker;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;

public class MiningEventHandler {
    
    public static void register() {
        PlayerBlockBreakEvents.AFTER.register((world, player, pos, state, blockEntity) -> {
            if (!OllamaConfig.enableMiningTracking) {
                return;
            }
            
            if (player instanceof Player) {
                String playerName = player.getName().getString();
                
                // Get block name from registry
                ResourceLocation blockId = BuiltInRegistries.BLOCK.getKey(state.getBlock());
                String blockName = blockId != null ? blockId.toString() : state.getBlock().getDescriptionId();
                
                // Record the mined block
                com.ollamamod.client.MiningTracker tracker = DailyStatsTracker.getMiningTracker(playerName);
                tracker.recordBlockMined(blockName, System.currentTimeMillis());
            }
        });
    }
}
