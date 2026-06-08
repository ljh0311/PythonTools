package com.ollamamod.commands;

import com.ollamamod.OllamaMod;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.config.OllamaConfig;
import com.ollamamod.platform.Platform;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

public class OllamaCommand {
    private final OllamaChatHandler chatHandler;
    private final Platform platform;
    
    public OllamaCommand(OllamaChatHandler chatHandler, Platform platform) {
        this.chatHandler = chatHandler;
        this.platform = platform;
    }
    
    public void register(Platform.ClientCommandRegistrar registrar) {
        if (!OllamaConfig.enableChatCommand) {
            return;
        }
        
        registrar.register("ollama", (source, args) -> {
            if (args.length == 0) {
                sendMessage(source, Component.literal("Usage: /ollama <message>"));
                return;
            }
            
            String message = String.join(" ", args);
            String playerName = source.getEntity() != null ? 
                source.getEntity().getName().getString() : "Server";
            
            sendMessage(source, Component.literal("Sending message to AI..."));
            
            chatHandler.getOllamaClient().sendMessage(message, playerName)
                .thenAccept(response -> {
                    sendMessage(source, Component.literal("AI: " + response));
                    
                    // Check if response contains command to execute
                    if (OllamaConfig.enableCommandExecution) {
                        String command = chatHandler.extractCommandFromResponse(response);
                        if (command != null && chatHandler.shouldExecuteCommand(command, message)) {
                            // Execute the command
                            chatHandler.executeCommandWithSource(command, playerName, message, source);
                            sendMessage(source, Component.literal("Executing command: " + command));
                        }
                    }
                })
                .exceptionally(throwable -> {
                    sendMessage(source, Component.literal("Error: " + throwable.getMessage()));
                    OllamaMod.LOGGER.error("Command error", throwable);
                    return null;
                });
        });
        
        registrar.register("ollama_clear", (source, args) -> {
            String playerName = source.getEntity() != null ? 
                source.getEntity().getName().getString() : "Server";
            chatHandler.getConversationManager().clearSession(playerName);
            sendMessage(source, Component.literal("Conversation cleared"));
        });
    }
    
    private void sendMessage(CommandSourceStack source, Component message) {
        platform.sendMessage(source, message);
    }
}
