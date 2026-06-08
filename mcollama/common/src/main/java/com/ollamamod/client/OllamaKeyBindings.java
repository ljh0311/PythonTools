package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.gui.ChatScreenProvider;
import com.ollamamod.platform.Platform;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;

public class OllamaKeyBindings {
    private final Platform platform;
    private final ChatScreenProvider screenProvider;
    
    public OllamaKeyBindings(Platform platform, ChatScreenProvider screenProvider) {
        this.platform = platform;
        this.screenProvider = screenProvider;
    }
    
    public void register() {
        if (!OllamaConfig.enableGui) {
            return;
        }
        
        platform.registerKeyBinding("open_gui", 79, "ollamamod"); // O key
    }
    
    public void handleKeyPress() {
        if (!OllamaConfig.enableGui) {
            return;
        }
        
        Minecraft mc = Minecraft.getInstance();
        if (mc.screen == null) {
            Screen chatScreen = screenProvider.createChatScreen(null);
            mc.setScreen(chatScreen);
        }
    }
}
