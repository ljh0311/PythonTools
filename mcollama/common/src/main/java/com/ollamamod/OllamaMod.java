package com.ollamamod;

import com.ollamamod.config.OllamaConfig;
import com.ollamamod.platform.Platform;
import dev.architectury.event.EventResult;
import dev.architectury.event.events.common.LifecycleEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class OllamaMod {
    public static final String MOD_ID = "ollamamod";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    public static void init() {
        LOGGER.info("Ollama Mod is loading!");
        
        OllamaConfig.init();
        
        LifecycleEvent.SETUP.register(() -> {
            LOGGER.info("Ollama Mod setup complete!");
        });
    }
}
