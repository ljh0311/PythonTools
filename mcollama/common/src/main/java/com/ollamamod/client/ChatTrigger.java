package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;

/**
 * Recognises the in-chat trigger prefix so a player can talk to the model from the
 * vanilla chat box, which already gives them history, scrollback and copy/paste.
 */
public final class ChatTrigger {

    private ChatTrigger() {
    }

    /**
     * @return the prompt when the message was addressed to the AI, otherwise {@code null}
     *         so the caller lets the message through to the server untouched.
     */
    public static String extractPrompt(String rawMessage) {
        if (!OllamaConfig.enableChatTrigger || rawMessage == null) {
            return null;
        }

        String trigger = OllamaConfig.chatTrigger;
        if (trigger == null || trigger.isEmpty()) {
            return null;
        }

        String trimmed = rawMessage.trim();
        if (!trimmed.regionMatches(true, 0, trigger, 0, trigger.length())) {
            return null;
        }

        String prompt = trimmed.substring(trigger.length()).trim();
        return prompt.isEmpty() ? null : prompt;
    }
}
