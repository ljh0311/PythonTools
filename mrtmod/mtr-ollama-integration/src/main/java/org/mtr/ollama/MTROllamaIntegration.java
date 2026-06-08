package org.mtr.ollama;

import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.mtr.mapping.registry.CommandBuilder;
import org.mtr.mod.Init;

public class MTROllamaIntegration {
    private static final Logger LOGGER = LogManager.getLogger("MTR-Ollama");
    
    public static void init() {
        LOGGER.info("Initializing MTR Ollama Integration...");
        
        // Register configuration
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, OllamaConfig.SPEC, "mtr-ollama-common.toml");
        
        // Register event listener for setup
        FMLJavaModLoadingContext.get().getModEventBus().addListener(MTROllamaIntegration::setup);
        
        // Register commands
        Init.REGISTRY.registerCommand("mtr", (CommandBuilder<?> commandBuilder) -> {
            MTROllamaCommands.register(commandBuilder);
        }, "minecrafttransitrailway");
        
        LOGGER.info("MTR Ollama Integration initialized successfully");
    }
    
    private static void setup(FMLCommonSetupEvent event) {
        event.enqueueWork(() -> {
            LOGGER.info("MTR Ollama Integration setup complete");
            OllamaConfig.loadConfig();
        });
    }
}
