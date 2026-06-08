package com.ollamamod.session;

import com.ollamamod.config.OllamaConfig;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class ConversationManager {
    private final Map<String, ConversationSession> sessions = new ConcurrentHashMap<>();
    
    public void addMessage(String playerName, String userMessage, String aiResponse) {
        ConversationSession session = sessions.computeIfAbsent(playerName, 
            k -> new ConversationSession(playerName));
        
        session.addMessage(new Message(userMessage, aiResponse));
        
        // Enforce session limits
        if (session.getMessages().size() > OllamaConfig.maxContextTokens && 
            OllamaConfig.maxContextTokens > 0) {
            List<Message> messages = session.getMessages();
            int toRemove = messages.size() - OllamaConfig.maxContextTokens;
            messages.subList(0, toRemove).clear();
        }
    }
    
    public String getContext(String playerName) {
        ConversationSession session = sessions.get(playerName);
        if (session == null) {
            return "";
        }
        
        StringBuilder context = new StringBuilder();
        for (Message msg : session.getMessages()) {
            context.append("Player: ").append(msg.userMessage).append("\n");
            context.append("Assistant: ").append(msg.aiResponse).append("\n\n");
        }
        return context.toString();
    }
    
    public void clearSession(String playerName) {
        sessions.remove(playerName);
    }
    
    public static class ConversationSession {
        private final String playerName;
        private final List<Message> messages = new ArrayList<>();
        private final long createdAt = System.currentTimeMillis();
        
        public ConversationSession(String playerName) {
            this.playerName = playerName;
        }
        
        public void addMessage(Message message) {
            messages.add(message);
        }
        
        public List<Message> getMessages() {
            return messages;
        }
        
        public String getPlayerName() {
            return playerName;
        }
        
        public long getCreatedAt() {
            return createdAt;
        }
    }
    
    public static class Message {
        public final String userMessage;
        public final String aiResponse;
        public final long timestamp;
        
        public Message(String userMessage, String aiResponse) {
            this.userMessage = userMessage;
            this.aiResponse = aiResponse;
            this.timestamp = System.currentTimeMillis();
        }
    }
}
