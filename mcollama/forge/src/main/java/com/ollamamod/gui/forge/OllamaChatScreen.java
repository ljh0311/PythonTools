package com.ollamamod.gui.forge;

import com.ollamamod.client.OllamaCommandActions;
import com.ollamamod.client.OllamaException;
import com.ollamamod.forge.OllamaModForge;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
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
        messageBox.setSuggestion(Component.translatable("gui.ollamamod.chat.placeholder").getString());
        addRenderableWidget(messageBox);
        setInitialFocus(messageBox);
        
        responseArea = new MultiLineTextWidget(centerX - 150, centerY - 80, 
            Component.translatable("gui.ollamamod.chat.response_placeholder"), font);
        responseArea.setMaxWidth(300);
        responseArea.setMaxRows(10);
        addRenderableWidget(responseArea);
        
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
        
        responseArea.setMessage(Component.translatable("gui.ollamamod.chat.loading"));
        messageBox.setValue("");
        setBusy(true);
        
        OllamaModForge.getChatHandler().getOllamaClient()
            .sendMessage(message, OllamaCommandActions.currentPlayerName(), minecraft.player)
            .thenAccept(response -> showResult(Component.literal(response)))
            .exceptionally(throwable -> {
                showResult(Component.literal(OllamaException.playerMessage(throwable))
                    .withStyle(ChatFormatting.RED));
                return null;
            });
    }
    
    private void showResult(Component result) {
        minecraft.execute(() -> {
            if (minecraft.screen != this) {
                return;
            }
            setBusy(false);
            responseArea.setMessage(result);
        });
    }
    
    private void setBusy(boolean busy) {
        sendButton.active = !busy;
        messageBox.setEditable(!busy);
    }
    
    private void clearChat() {
        OllamaModForge.getChatHandler().getConversationManager()
            .clearSession(OllamaCommandActions.currentPlayerName());
        responseArea.setMessage(Component.translatable("gui.ollamamod.chat.response_placeholder"));
    }
    
    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
        renderBackground(graphics);
        super.render(graphics, mouseX, mouseY, delta);
        graphics.drawCenteredString(font, title, width / 2, 20, 0xFFFFFF);
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
