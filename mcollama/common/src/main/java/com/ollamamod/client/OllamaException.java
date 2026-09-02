package com.ollamamod.client;

import java.util.concurrent.CompletionException;

/**
 * Failure whose message is written for a player to read, not for a log file.
 *
 * <p>Failures used to be returned as ordinary result strings, which meant callers could
 * not tell a reply apart from an error and every {@code exceptionally} handler was dead.
 */
public class OllamaException extends RuntimeException {

    public OllamaException(String playerMessage) {
        super(playerMessage);
    }

    public OllamaException(String playerMessage, Throwable cause) {
        super(playerMessage, cause);
    }

    /**
     * Digs the player-facing text out of whatever a {@link java.util.concurrent.CompletableFuture}
     * handed us, which is normally a {@link CompletionException} wrapping the real cause.
     */
    public static String playerMessage(Throwable throwable) {
        Throwable cause = throwable;
        while (cause instanceof CompletionException && cause.getCause() != null) {
            cause = cause.getCause();
        }
        if (cause instanceof OllamaException) {
            return cause.getMessage();
        }
        return "Unexpected problem talking to Ollama: " + cause;
    }
}
