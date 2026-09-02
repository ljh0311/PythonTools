package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.summary.DailySummaryGenerator;
import net.minecraft.client.Minecraft;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.world.entity.player.Player;

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

        chatHandler.getOllamaClient().sendMessage(message, currentPlayerName(), currentPlayer())
                .thenAccept(ClientFeedback::aiReply)
                .exceptionally(throwable -> {
                    ClientFeedback.error(OllamaException.playerMessage(throwable));
                    return null;
                });
    }

    public static void sendDoRequest(OllamaChatHandler chatHandler, String request) {
        if (!OllamaConfig.enableCommandExecution) {
            ClientFeedback.error(
                "Command execution is disabled. Set enableCommandExecution to true in ollamamod.json.");
            return;
        }

        CommandSourceStack source = resolveCommandSource();
        if (source == null) {
            ClientFeedback.error("Cannot run commands: join a world first.");
            return;
        }

        ClientFeedback.info("Asking AI for a command\u2026");

        chatHandler.getOllamaClient().sendMessage(request, currentPlayerName(), currentPlayer())
                .thenAccept(response -> {
                    ClientFeedback.aiReply(response);
                    String command = chatHandler.extractCommandFromResponse(response);
                    if (command == null || command.isEmpty()) {
                        ClientFeedback.error("AI response did not contain a command to run.");
                        return;
                    }
                    chatHandler.executeCommandWithSource(command, currentPlayerName(), request, source);
                })
                .exceptionally(throwable -> {
                    ClientFeedback.error(OllamaException.playerMessage(throwable));
                    return null;
                });
    }

    private static CommandSourceStack resolveCommandSource() {
        Minecraft minecraft = Minecraft.getInstance();
        return minecraft.player != null ? minecraft.player.createCommandSourceStack() : null;
    }

    public static void showDailySummary() {
        String summary = DailySummaryGenerator.generateDailySummary(currentPlayerName());
        for (String line : summary.split("\n")) {
            if (line.isEmpty()) {
                continue;
            }
            for (int i = 0; i < line.length(); i += 250) {
                ClientFeedback.info(line.substring(i, Math.min(i + 250, line.length())));
            }
        }
    }

    public static void clearConversation(OllamaChatHandler chatHandler) {
        chatHandler.getConversationManager().clearSession(currentPlayerName());
        ClientFeedback.info("Conversation cleared.");
    }

    public static String currentPlayerName() {
        Minecraft minecraft = Minecraft.getInstance();
        return minecraft.player != null ? minecraft.player.getName().getString() : "Player";
    }

    public static Player currentPlayer() {
        return Minecraft.getInstance().player;
    }
}
