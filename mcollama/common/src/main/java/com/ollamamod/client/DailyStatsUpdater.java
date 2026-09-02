package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.summary.DailyStatsTracker;
import net.minecraft.world.entity.player.Player;

public class DailyStatsUpdater {
    private static int ticksSinceSample = 0;

    public static void onPlayerTick(Player player) {
        if (!OllamaConfig.enableDailySummary || player == null) {
            return;
        }

        ticksSinceSample++;
        if (ticksSinceSample < OllamaConfig.foodTrackingInterval) {
            return;
        }
        ticksSinceSample = 0;
        DailyStatsTracker.updatePlayerStats(player);
    }
}
