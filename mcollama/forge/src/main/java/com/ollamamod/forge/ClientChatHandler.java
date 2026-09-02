package com.ollamamod.forge;

import com.ollamamod.client.ChatTrigger;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.client.OllamaCommandActions;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientChatEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Lets a player address the model from the vanilla chat box (default "@ai ..."),
 * so they get chat history and scrollback instead of a single-reply screen.
 */
@Mod.EventBusSubscriber(value = Dist.CLIENT, modid = "ollamamod", bus = Mod.EventBusSubscriber.Bus.FORGE)
public class ClientChatHandler {
    
    @SubscribeEvent
    public static void onClientChat(ClientChatEvent event) {
        OllamaChatHandler chatHandler = OllamaModForge.getChatHandler();
        if (chatHandler == null) return;
        
        String prompt = ChatTrigger.extractPrompt(event.getMessage());
        if (prompt == null) return;
        
        // Keep the trigger message off the server; it was addressed to the mod.
        event.setCanceled(true);
        OllamaCommandActions.sendPrompt(chatHandler, prompt);
    }
}
