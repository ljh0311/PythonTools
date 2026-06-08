package com.ollamamod.forge;

import com.ollamamod.client.CommandResultListener;
import com.ollamamod.client.OllamaChatHandler;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.CommandEvent;
import net.minecraftforge.event.ServerChatEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = "ollamamod", bus = Mod.EventBusSubscriber.Bus.FORGE)
public class CommandExecutionHandler {
    
    @SubscribeEvent
    public static void onCommandExecuted(CommandEvent event) {
        // Check if this command was executed by our system
        CommandSourceStack source = event.getParseResults().getContext().getSource();
        String command = event.getParseResults().getReader().getString();
        
        // Check if this command is being tracked
        OllamaChatHandler chatHandler = OllamaModForge.getChatHandler();
        if (chatHandler == null) {
            return;
        }
        
        CommandResultListener listener = chatHandler.getResultListener();
        if (listener == null) {
            return;
        }
        
        // Check all pending commands to see if this matches
        for (String commandId : listener.getAllPendingCommandIds()) {
            CommandResultListener.CommandInfo info = listener.hasPendingCommand(commandId) ? 
                new CommandResultListener.CommandInfo(command, System.currentTimeMillis()) : null;
            
            if (info != null && info.command.equals(command)) {
                // Capture command result
                if (event.getException() != null) {
                    listener.captureOutput(commandId, event.getException().getMessage(), true);
                } else {
                    // Command succeeded - try to get output
                    listener.captureOutput(commandId, "Command executed successfully", false);
                }
                break;
            }
        }
    }
    
    public static void executeCommandForPlayer(String command, String playerName, 
                                               OllamaChatHandler chatHandler) {
        // This would need access to server to execute commands
        // For now, we'll handle this through the command executor
        // The actual execution happens in CommandExecutor which has access to CommandSourceStack
    }
}
