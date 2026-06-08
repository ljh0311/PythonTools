package com.ollamamod.fabric;

import com.ollamamod.gui.ChatScreenProvider;
import com.ollamamod.platform.Platform;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

import java.nio.file.Path;

public class FabricPlatform implements Platform {
    private final ChatScreenProvider screenProvider;
    private KeyMapping openGuiKey;
    
    public FabricPlatform(ChatScreenProvider screenProvider) {
        this.screenProvider = screenProvider;
    }
    
    @Override
    public Path getConfigDirectory() {
        return net.fabricmc.loader.api.FabricLoader.getInstance().getConfigDir();
    }
    
    @Override
    public void registerClientCommands(ClientCommandRegistrar registrar) {
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> {
            registrar.register("ollama", (source, args) -> {
                // Commands are handled through the common command system
            });
        });
    }
    
    @Override
    public void registerKeyBinding(String name, int key, String category) {
        openGuiKey = KeyBindingHelper.registerKeyBinding(new KeyMapping(
            "key.ollamamod." + name,
            key,
            "key.categories." + category
        ));
    }
    
    @Override
    public Screen createChatScreen() {
        return screenProvider.createChatScreen(net.minecraft.client.Minecraft.getInstance().screen);
    }
    
    @Override
    public void sendMessage(CommandSourceStack source, Component message) {
        source.sendSuccess(() -> message, false);
    }
    
    @Override
    public boolean isClient() {
        return net.minecraft.client.Minecraft.getInstance() != null;
    }
    
    public KeyMapping getOpenGuiKey() {
        return openGuiKey;
    }
}
