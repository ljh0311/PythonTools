package com.ollamamod.forge;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.summary.DailyStatsTracker;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.level.BlockEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = "ollamamod", bus = Mod.EventBusSubscriber.Bus.FORGE)
public class MiningEventHandler {
    
    @SubscribeEvent
    public static void onBlockBreak(BlockEvent.BreakEvent event) {
        if (!OllamaConfig.enableMiningTracking) {
            return;
        }
        
        if (event.getPlayer() instanceof Player) {
            Player player = (Player) event.getPlayer();
            String playerName = player.getName().getString();
            
            // Get block name from registry
            ResourceLocation blockId = BuiltInRegistries.BLOCK.getKey(event.getState().getBlock());
            String blockName = blockId != null ? blockId.toString() : event.getState().getBlock().getDescriptionId();
            
            // Record the mined block
            com.ollamamod.client.MiningTracker tracker = DailyStatsTracker.getMiningTracker(playerName);
            tracker.recordBlockMined(blockName, System.currentTimeMillis());
        }
    }
}
