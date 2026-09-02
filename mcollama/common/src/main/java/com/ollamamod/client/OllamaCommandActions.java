package com.ollamamod.client;

import net.minecraft.client.Minecraft;

/**
 * Behaviour behind the player-facing entry points. Fabric and Forge can only share the
 * behaviour, not the Brigadier tree, because their client dispatchers use different
 * source types; keeping the behaviour here stops the two loaders from drifting apart.
 */
public final class OllamaCommandActions {

    private OllamaCommandActions() {
    }

    public static void sendPrompt(OllamaChatHandler chatHandler, String message) {
        ClientFeedback.info("Thinking\u2026");

        chatHandler.getOllamaClient().sendMessage(message, currentPlayerName())
                .thenAccept(ClientFeedback::aiReply)
                .exceptionally(throwable -> {
                    ClientFeedback.error(OllamaException.playerMessage(throwable));
                    return null;
                });
    }

    public static void clearConversation(OllamaChatHandler chatHandler) {
        chatHandler.getConversationManager().clearSession(currentPlayerName());
        ClientFeedback.info("Conversation cleared.");
    }

    public static String currentPlayerName() {
        Minecraft minecraft = Minecraft.getInstance();
        return minecraft.player != null ? minecraft.player.getName().getString() : "Player";
    }
}
