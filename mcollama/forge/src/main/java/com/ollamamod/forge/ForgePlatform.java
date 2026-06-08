package com.ollamamod.forge;

import com.ollamamod.gui.ChatScreenProvider;
import com.ollamamod.platform.Platform;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.SubscribeEvent;

import java.nio.file.Path;

public class ForgePlatform implements Platform {
    private final ChatScreenProvider screenProvider;
    private KeyMapping openGuiKey;
    
    public ForgePlatform(ChatScreenProvider screenProvider) {
        this.screenProvider = screenProvider;
        MinecraftForge.EVENT_BUS.register(this);
    }
    
    @Override
    public Path getConfigDirectory() {
        return net.minecraftforge.fml.loading.FMLPaths.CONFIGDIR.get();
    }
    
    @Override
    public void registerClientCommands(ClientCommandRegistrar registrar) {
        // Commands are registered via Forge events
    }
    
    @SubscribeEvent
    public void onKeyRegister(RegisterKeyMappingsEvent event) {
        if (openGuiKey != null) {
            event.register(openGuiKey);
        }
    }
    
    @Override
    public void registerKeyBinding(String name, int key, String category) {
        openGuiKey = new KeyMapping(
            "key.ollamamod." + name,
            key,
            "key.categories." + category
        );
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
