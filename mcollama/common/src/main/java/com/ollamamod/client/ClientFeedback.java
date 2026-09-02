package com.ollamamod.client;

import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

/**
 * Single place that decides how the mod speaks to the player in chat, so replies,
 * status and errors are visually distinguishable from ordinary chat.
 */
public final class ClientFeedback {

    private ClientFeedback() {
    }

    public static void aiReply(String response) {
        send(ChatFormatting.AQUA, "[AI] ", ChatFormatting.WHITE, response);
    }

    public static void info(String message) {
        send(ChatFormatting.AQUA, "[Ollama] ", ChatFormatting.GRAY, message);
    }

    public static void error(String message) {
        send(ChatFormatting.AQUA, "[Ollama] ", ChatFormatting.RED, message);
    }

    private static void send(ChatFormatting prefixColor, String prefix,
                             ChatFormatting bodyColor, String body) {
        Component component = Component.literal(prefix).withStyle(prefixColor)
                .append(Component.literal(body).withStyle(bodyColor));

        // Callers are usually CompletableFuture callbacks on a pool thread.
        Minecraft minecraft = Minecraft.getInstance();
        minecraft.execute(() -> {
            if (minecraft.player != null) {
                minecraft.player.sendSystemMessage(component);
            }
        });
    }
}
