package com.ollamamod.fabric;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.ollamamod.OllamaMod;
import com.ollamamod.client.DailyStatsUpdater;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.client.OllamaKeyBindings;
import com.ollamamod.commands.OllamaCommand;
import com.ollamamod.gui.fabric.OllamaChatScreen;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.argument;
import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.literal;

public class OllamaModFabric implements ModInitializer, ClientModInitializer {
    private static FabricPlatform platform;
    private static OllamaChatHandler chatHandler;
    private static OllamaKeyBindings keyBindings;
    
    public static FabricPlatform getPlatform() {
        return platform;
    }
    
    public static OllamaChatHandler getChatHandler() {
        return chatHandler;
    }
    
    @Override
    public void onInitialize() {
        OllamaMod.init();
        
        platform = new FabricPlatform(() -> new OllamaChatScreen(null));
        chatHandler = new OllamaChatHandler(platform);
        
        // Register mining event handler
        MiningEventHandler.register();
        
        // Register Fabric client commands
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> {
            dispatcher.register(literal("ollama")
                .then(argument("message", StringArgumentType.greedyString())
                    .executes(context -> {
                        String message = StringArgumentType.getString(context, "message");
                        String playerName = Minecraft.getInstance().player != null ?
                            Minecraft.getInstance().player.getName().getString() : "Player";
                        
                        chatHandler.getOllamaClient().sendMessage(message, playerName)
                            .thenAccept(response -> {
                                if (Minecraft.getInstance().player != null) {
                                    Minecraft.getInstance().player.sendSystemMessage(
                                        Component.literal("AI: " + response)
                                    );
                                }
                            });
                        return 1;
                    })
                )
            );
            
            dispatcher.register(literal("ollama_clear")
                .executes(context -> {
                    String playerName = Minecraft.getInstance().player != null ?
                        Minecraft.getInstance().player.getName().getString() : "Player";
                    chatHandler.getConversationManager().clearSession(playerName);
                    if (Minecraft.getInstance().player != null) {
                        Minecraft.getInstance().player.sendSystemMessage(
                            Component.literal("Conversation cleared")
                        );
                    }
                    return 1;
                })
            );
        });
    }
    
    @Override
    public void onInitializeClient() {
        keyBindings = new OllamaKeyBindings(platform, () -> new OllamaChatScreen(null));
        keyBindings.register();
        
        // Handle key press events
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (platform.getOpenGuiKey() != null && platform.getOpenGuiKey().consumeClick()) {
                keyBindings.handleKeyPress();
            }
            
            // Update daily stats including food tracking
            if (client.player != null) {
                DailyStatsUpdater.onPlayerTick(client.player);
            }
        });
    }
}
