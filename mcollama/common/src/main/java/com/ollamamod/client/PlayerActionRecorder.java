package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import net.minecraft.world.entity.player.Player;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;

public class PlayerActionRecorder {
    private final ConcurrentLinkedQueue<RecordedAction> actionQueue = new ConcurrentLinkedQueue<>();
    private RecordingSession currentSession;
    private int tickCounter = 0;
    
    public void tick(Player player) {
        if (!OllamaConfig.enableActionRecording || player == null) {
            return;
        }
        
        tickCounter++;
        if (tickCounter >= OllamaConfig.recordingInterval) {
            tickCounter = 0;
            recordAction(player);
        }
    }
    
    private void recordAction(Player player) {
        if (currentSession == null) {
            currentSession = new RecordingSession(player.getUUID());
        }
        
        RecordedAction action = new RecordedAction(
            System.currentTimeMillis(),
            player.blockPosition(),
            player.getHealth(),
            player.getFoodData().getFoodLevel()
        );
        
        actionQueue.offer(action);
        
        if (actionQueue.size() >= OllamaConfig.maxRecordingQueueSize) {
            flushToDisk();
        }
    }
    
    private void flushToDisk() {
        // Platform-specific file I/O
        actionQueue.clear();
    }
    
    public void startSession(Player player) {
        currentSession = new RecordingSession(player.getUUID());
    }
    
    public void endSession() {
        flushToDisk();
        currentSession = null;
    }
    
    public static class RecordedAction {
        public final long timestamp;
        public final int x, y, z;
        public final float health;
        public final int foodLevel;
        
        public RecordedAction(long timestamp, net.minecraft.core.BlockPos pos, 
                            float health, int foodLevel) {
            this.timestamp = timestamp;
            this.x = pos.getX();
            this.y = pos.getY();
            this.z = pos.getZ();
            this.health = health;
            this.foodLevel = foodLevel;
        }
    }
    
    public static class RecordingSession {
        public final java.util.UUID playerId;
        public final long startTime;
        public final List<RecordedAction> actions = new ArrayList<>();
        
        public RecordingSession(java.util.UUID playerId) {
            this.playerId = playerId;
            this.startTime = System.currentTimeMillis();
        }
    }
}
