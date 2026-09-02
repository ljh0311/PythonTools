package com.ollamamod.fabric;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.ollamamod.OllamaMod;
import com.ollamamod.client.ChatTrigger;
import com.ollamamod.client.DailyStatsUpdater;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.client.OllamaCommandActions;
import com.ollamamod.client.OllamaKeyBindings;
import com.ollamamod.client.OllamaStartupCheck;
import com.ollamamod.gui.fabric.OllamaChatScreen;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.message.v1.ClientSendMessageEvents;

import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.argument;
import static net.fabricmc.fabric.api.client.command.v2.ClientCommandManager.literal;

/**
 * Client-only entry point. The mod talks to a local Ollama server from the player's own
 * machine and registers only client commands, so it has nothing to do on a dedicated server.
 */
public class OllamaModFabric implements ClientModInitializer {
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
    public void onInitializeClient() {
        OllamaMod.init();
        
        platform = new FabricPlatform(OllamaChatScreen::new);
        chatHandler = new OllamaChatHandler(platform);
        
        MiningEventHandler.register();
        registerCommands();
        registerChatTrigger();
        
        keyBindings = new OllamaKeyBindings(platform, OllamaChatScreen::new);
        keyBindings.register();
        
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (platform.getOpenGuiKey() != null && platform.getOpenGuiKey().consumeClick()) {
                keyBindings.handleKeyPress();
            }
            
            if (client.player != null) {
                OllamaStartupCheck.runOnce(chatHandler.getOllamaClient());
                DailyStatsUpdater.onPlayerTick(client.player);
            }
        });
    }
    
    private void registerCommands() {
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> {
            dispatcher.register(literal("ollama")
                .then(argument("message", StringArgumentType.greedyString())
                    .executes(context -> {
                        OllamaCommandActions.sendPrompt(chatHandler,
                            StringArgumentType.getString(context, "message"));
                        return 1;
                    })
                )
            );
            
            dispatcher.register(literal("ollama_clear")
                .executes(context -> {
                    OllamaCommandActions.clearConversation(chatHandler);
                    return 1;
                })
            );
        });
    }
    
    private void registerChatTrigger() {
        ClientSendMessageEvents.ALLOW_CHAT.register(message -> {
            String prompt = ChatTrigger.extractPrompt(message);
            if (prompt == null) {
                return true;
            }
            
            // Keep the trigger message off the server; it was addressed to the mod.
            OllamaCommandActions.sendPrompt(chatHandler, prompt);
            return false;
        });
    }
}
