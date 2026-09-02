package com.ollamamod.forge;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.ollamamod.client.OllamaChatHandler;
import com.ollamamod.client.OllamaCommandActions;
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
            .then(literal("do")
                .then(argument("request", StringArgumentType.greedyString())
                    .executes(context -> {
                        OllamaCommandActions.sendDoRequest(chatHandler,
                            StringArgumentType.getString(context, "request"));
                        return 1;
                    })
                )
            )
            .then(literal("summary")
                .executes(context -> {
                    OllamaCommandActions.showDailySummary();
                    return 1;
                })
            )
            .then(argument("message", StringArgumentType.greedyString())
                .executes(context -> {
                    OllamaCommandActions.sendPrompt(chatHandler,
                        StringArgumentType.getString(context, "message"));
                    return 1;
                })
            )
        );
        
        event.getDispatcher().register(literal("ollama_clear")
            .executes(context -> {
                OllamaCommandActions.clearConversation(chatHandler);
                return 1;
            })
        );
    }
}
