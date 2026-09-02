package com.ollamamod.client;

import com.ollamamod.config.OllamaConfig;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ChatTriggerTest {

    @AfterEach
    void reset() {
        OllamaConfig.enableChatTrigger = true;
        OllamaConfig.chatTrigger = "@ai";
    }

    @Test
    void extractsPromptAfterTrigger() {
        assertEquals("hello world", ChatTrigger.extractPrompt("@ai hello world"));
    }

    @Test
    void triggerIsCaseInsensitive() {
        assertEquals("hi", ChatTrigger.extractPrompt("@AI hi"));
    }

    @Test
    void ignoresPlainChat() {
        assertNull(ChatTrigger.extractPrompt("hello everyone"));
    }

    @Test
    void ignoresTriggerOnly() {
        assertNull(ChatTrigger.extractPrompt("@ai"));
        assertNull(ChatTrigger.extractPrompt("  @ai   "));
    }

    @Test
    void respectsDisabledFlag() {
        OllamaConfig.enableChatTrigger = false;
        assertNull(ChatTrigger.extractPrompt("@ai hello"));
    }
}
