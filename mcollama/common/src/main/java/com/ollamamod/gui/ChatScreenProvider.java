package com.ollamamod.gui;

import net.minecraft.client.gui.screens.Screen;

public interface ChatScreenProvider {
    Screen createChatScreen(Screen parent);
}
