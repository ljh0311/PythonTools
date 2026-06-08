package com.ollamamod.client;

import java.util.*;

public class OllamaBehaviorAnalyzer {
    private final Map<String, PlayerProfile> profiles = new HashMap<>();
    
    public void analyzeBehavior(String playerId, List<PlayerActionRecorder.RecordedAction> actions) {
        PlayerProfile profile = profiles.computeIfAbsent(playerId, k -> new PlayerProfile(playerId));
        
        if (actions.isEmpty()) {
            return;
        }
        
        // Calculate statistics
        int totalActions = actions.size();
        long timeSpan = actions.get(actions.size() - 1).timestamp - actions.get(0).timestamp;
        
        // Movement analysis
        double totalDistance = 0;
        for (int i = 1; i < actions.size(); i++) {
            PlayerActionRecorder.RecordedAction prev = actions.get(i - 1);
            PlayerActionRecorder.RecordedAction curr = actions.get(i);
            totalDistance += Math.sqrt(
                Math.pow(curr.x - prev.x, 2) +
                Math.pow(curr.y - prev.y, 2) +
                Math.pow(curr.z - prev.z, 2)
            );
        }
        
        profile.updateStats(totalActions, timeSpan, totalDistance);
    }
    
    public BehaviorInsight generateInsight(String playerId) {
        PlayerProfile profile = profiles.get(playerId);
        if (profile == null) {
            return null;
        }
        
        List<String> insights = new ArrayList<>();
        
        if (profile.getAverageSpeed() > 10) {
            insights.add("Player moves quickly and actively");
        }
        
        if (profile.getTotalDistance() > 1000) {
            insights.add("Player has traveled significant distances");
        }
        
        return new BehaviorInsight(playerId, insights, System.currentTimeMillis());
    }
    
    public static class PlayerProfile {
        private final String playerId;
        private int totalActions;
        private long totalTime;
        private double totalDistance;
        private final long createdAt;
        
        public PlayerProfile(String playerId) {
            this.playerId = playerId;
            this.createdAt = System.currentTimeMillis();
        }
        
        public void updateStats(int actions, long time, double distance) {
            this.totalActions += actions;
            this.totalTime += time;
            this.totalDistance += distance;
        }
        
        public double getAverageSpeed() {
            return totalTime > 0 ? totalDistance / (totalTime / 1000.0) : 0;
        }
        
        public String getPlayerId() {
            return playerId;
        }
        
        public int getTotalActions() {
            return totalActions;
        }
        
        public long getTotalTime() {
            return totalTime;
        }
        
        public double getTotalDistance() {
            return totalDistance;
        }
    }
    
    public static class BehaviorInsight {
        public final String playerId;
        public final List<String> insights;
        public final long timestamp;
        
        public BehaviorInsight(String playerId, List<String> insights, long timestamp) {
            this.playerId = playerId;
            this.insights = insights;
            this.timestamp = timestamp;
        }
    }
}
