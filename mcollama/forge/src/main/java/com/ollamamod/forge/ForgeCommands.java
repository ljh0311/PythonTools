package com.ollamamod.forge;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.ollamamod.client.OllamaChatHandler;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterClientCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import static net.minecraft.commands.Commands.argument;
import static net.minecraft.commands.Commands.literal;

@Mod.EventBusSubscriber(value = Dist.CLIENT, modid = "ollamamod", bus = Mod.EventBusSubscriber.Bus.FORGE)
public class ForgeCommands {
    
    @SubscribeEvent
    public static void onRegisterCommands(RegisterClientCommandsEvent event) {
        OllamaChatHandler chatHandler = OllamaModForge.getChatHandler();
        if (chatHandler == null) return;
        
        event.getDispatcher().register(literal("ollama")
            .then(argument("message", StringArgumentType.greedyString())
                .executes(context -> {
                    String message = StringArgumentType.getString(context, "message");
                    String playerName = Minecraft.getInstance().player != null ?
                        Minecraft.getInstance().player.getName().getString() : "Player";
                    
                    chatHandler.getOllamaClient().sendMessage(message, playerName)
                        .thenAccept(response -> {
                            if (Minecraft.getInstance().player != null) {
                                Minecraft.getInstance().player.sendSystemMessage(
                                    Component.literal("AI: " + response)
                                );
                            }
                        });
                    return 1;
                })
            )
        );
        
        event.getDispatcher().register(literal("ollama_clear")
            .executes(context -> {
                String playerName = Minecraft.getInstance().player != null ?
                    Minecraft.getInstance().player.getName().getString() : "Player";
                chatHandler.getConversationManager().clearSession(playerName);
                if (Minecraft.getInstance().player != null) {
                    Minecraft.getInstance().player.sendSystemMessage(
                        Component.literal("Conversation cleared")
                    );
                }
                return 1;
            })
        );
    }
}
