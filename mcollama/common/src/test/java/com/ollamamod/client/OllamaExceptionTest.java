package com.ollamamod.client;

import org.junit.jupiter.api.Test;

import java.util.concurrent.CompletionException;

import static org.junit.jupiter.api.Assertions.*;

class OllamaExceptionTest {

    @Test
    void unwrapsPlayerMessage() {
        OllamaException inner = new OllamaException("Cannot reach Ollama");
        CompletionException wrapped = new CompletionException(inner);
        assertEquals("Cannot reach Ollama", OllamaException.playerMessage(wrapped));
    }
}
