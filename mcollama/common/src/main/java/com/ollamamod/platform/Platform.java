package com.ollamamod.platform;

import net.minecraft.client.gui.screens.Screen;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;

import java.nio.file.Path;

public interface Platform {
    Path getConfigDirectory();
    
    void registerClientCommands(ClientCommandRegistrar registrar);
    
    void registerKeyBinding(String name, int key, String category);
    
    Screen createChatScreen();
    
    void sendMessage(CommandSourceStack source, Component message);
    
    boolean isClient();
    
    @FunctionalInterface
    interface ClientCommandRegistrar {
        void register(String name, CommandExecutor executor);
    }
    
    @FunctionalInterface
    interface CommandExecutor {
        void execute(CommandSourceStack source, String[] args);
    }
}
