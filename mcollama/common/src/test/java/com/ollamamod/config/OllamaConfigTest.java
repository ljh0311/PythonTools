package com.ollamamod.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;

class OllamaConfigTest {

    @Test
    void createsConfigOnFirstRun(@TempDir Path configDir) throws IOException {
        OllamaConfig.init(configDir);
        Path file = configDir.resolve("ollamamod.json");
        assertTrue(Files.exists(file));
        assertTrue(Files.readString(file).contains("ollamaUrl"));
    }

    @Test
    void roundTripsEditedValues(@TempDir Path configDir) throws IOException {
        OllamaConfig.init(configDir);
        OllamaConfig.defaultModel = "phi3";
        OllamaConfig.chatTrigger = "#ai";
        OllamaConfig.save();

        OllamaConfig.defaultModel = "llama2";
        OllamaConfig.chatTrigger = "@ai";
        OllamaConfig.load();

        assertEquals("phi3", OllamaConfig.defaultModel);
        assertEquals("#ai", OllamaConfig.chatTrigger);
    }
}
