package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.summary.DailyStatsTracker;
import net.minecraft.world.entity.player.Player;

public class DailyStatsUpdater {
    
    public static void onPlayerTick(Player player) {
        if (!OllamaConfig.enableDailySummary || player == null) {
            return;
        }
        
        // Update daily stats including food tracking
        DailyStatsTracker.updatePlayerStats(player);
    }
}
