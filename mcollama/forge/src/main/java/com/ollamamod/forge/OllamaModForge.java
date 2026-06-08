package com.ollamamod.forge;

import com.ollamamod.OllamaMod;
import com.ollamamod.client.DailyStatsUpdater;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.client.OllamaKeyBindings;
import com.ollamamod.gui.forge.OllamaChatScreen;
import net.minecraft.client.player.LocalPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod(OllamaMod.MOD_ID)
public class OllamaModForge {
    private static ForgePlatform platform;
    private static OllamaChatHandler chatHandler;
    private static OllamaKeyBindings keyBindings;
    
    public static ForgePlatform getPlatform() {
        return platform;
    }
    
    public static OllamaChatHandler getChatHandler() {
        return chatHandler;
    }
    
    public OllamaModForge() {
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
        
        modEventBus.addListener(this::onCommonSetup);
        modEventBus.addListener(this::onClientSetup);
        
        MinecraftForge.EVENT_BUS.register(this);
        
        OllamaMod.init();
    }
    
    private void onCommonSetup(FMLCommonSetupEvent event) {
        platform = new ForgePlatform(() -> new OllamaChatScreen(null));
        chatHandler = new OllamaChatHandler(platform);
    }
    
    private void onClientSetup(FMLClientSetupEvent event) {
        keyBindings = new OllamaKeyBindings(platform, () -> new OllamaChatScreen(null));
        keyBindings.register();
    }
    
    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase == TickEvent.Phase.END) {
            if (platform != null && platform.getOpenGuiKey() != null) {
                if (platform.getOpenGuiKey().consumeClick()) {
                    keyBindings.handleKeyPress();
                }
            }
            
            // Update daily stats including food tracking
            LocalPlayer player = net.minecraft.client.Minecraft.getInstance().player;
            if (player != null) {
                DailyStatsUpdater.onPlayerTick(player);
            }
        }
    }
}
