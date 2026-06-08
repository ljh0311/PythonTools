package com.ollamamod.gui.forge;

import com.ollamamod.forge.OllamaModForge;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.MultiLineTextWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class OllamaChatScreen extends Screen {
    private EditBox messageBox;
    private MultiLineTextWidget responseArea;
    private Button sendButton;
    private Button clearButton;
    private final Screen parent;
    
    public OllamaChatScreen(Screen parent) {
        super(Component.translatable("gui.ollamamod.chat.title"));
        this.parent = parent;
    }
    
    @Override
    protected void init() {
        super.init();
        
        int centerX = width / 2;
        int centerY = height / 2;
        
        messageBox = new EditBox(font, centerX - 150, centerY + 60, 300, 20, 
            Component.translatable("gui.ollamamod.chat.placeholder"));
        messageBox.setMaxLength(500);
        addWidget(messageBox);
        
        responseArea = new MultiLineTextWidget(centerX - 150, centerY - 80, 
            Component.translatable("gui.ollamamod.chat.response_placeholder"), font);
        responseArea.setMaxWidth(300);
        addWidget(responseArea);
        
        sendButton = Button.builder(Component.translatable("gui.ollamamod.chat.send"), 
            button -> sendMessage())
            .bounds(centerX - 80, centerY + 90, 70, 20)
            .build();
        addRenderableWidget(sendButton);
        
        clearButton = Button.builder(Component.translatable("gui.ollamamod.chat.clear"),
            button -> clearChat())
            .bounds(centerX + 10, centerY + 90, 70, 20)
            .build();
        addRenderableWidget(clearButton);
    }
    
    private void sendMessage() {
        String message = messageBox.getValue();
        if (message.isEmpty()) {
            return;
        }
        
        String playerName = minecraft.player != null ? 
            minecraft.player.getName().getString() : "Player";
        
        responseArea.setMessage(Component.translatable("gui.ollamamod.chat.loading"));
        messageBox.setValue("");
        
        OllamaModForge.getChatHandler().getOllamaClient().sendMessage(message, playerName)
            .thenAccept(response -> {
                if (minecraft != null && minecraft.screen == this) {
                    minecraft.execute(() -> {
                        responseArea.setMessage(Component.literal(response));
                    });
                }
            })
            .exceptionally(throwable -> {
                if (minecraft != null && minecraft.screen == this) {
                    minecraft.execute(() -> {
                        responseArea.setMessage(Component.literal("Error: " + throwable.getMessage()));
                    });
                }
                return null;
            });
    }
    
    private void clearChat() {
        String playerName = minecraft.player != null ? 
            minecraft.player.getName().getString() : "Player";
        OllamaModForge.getChatHandler().getConversationManager().clearSession(playerName);
        responseArea.setMessage(Component.translatable("gui.ollamamod.chat.response_placeholder"));
    }
    
    @Override
    public void render(com.mojang.blaze3d.vertex.PoseStack matrices, int mouseX, int mouseY, float delta) {
        renderBackground(matrices);
        super.render(matrices, mouseX, mouseY, delta);
        drawCenteredString(matrices, font, title, width / 2, 20, 0xFFFFFF);
    }
    
    @Override
    public void onClose() {
        minecraft.setScreen(parent);
    }
    
    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if (keyCode == 257 && sendButton.active) { // Enter
            sendMessage();
            return true;
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
    }
}
