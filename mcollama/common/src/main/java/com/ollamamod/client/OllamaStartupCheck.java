package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;

import java.util.concurrent.CompletableFuture;

/**
 * One-off greeting the first time a player is in a world.
 *
 * <p>Without this the mod is completely silent on startup, so a player cannot tell whether
 * it loaded, which model it will use, or that Ollama is not running until their first
 * prompt fails.
 */
public final class OllamaStartupCheck {
    private static boolean alreadyRun;

    private OllamaStartupCheck() {
    }

    public static void runOnce(OllamaClient client) {
        if (alreadyRun) {
            return;
        }
        alreadyRun = true;

        // isAvailable() blocks for up to 5s, so it must not touch the client thread.
        CompletableFuture.runAsync(() -> {
            if (client.isAvailable()) {
                ClientFeedback.info("Connected to " + OllamaConfig.ollamaUrl + " using model '"
                        + OllamaConfig.defaultModel + "'. Type \"" + OllamaConfig.chatTrigger
                        + " <message>\" in chat, or press O.");
            } else {
                ClientFeedback.error("Cannot reach Ollama at " + OllamaConfig.ollamaUrl
                        + ". Start it with: ollama serve");
            }
        });
    }
}
