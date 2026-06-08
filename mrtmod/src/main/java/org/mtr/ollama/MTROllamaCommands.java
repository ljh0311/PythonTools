package org.mtr.ollama;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import org.mtr.mapping.registry.CommandBuilder;
import org.mtr.mod.Init;

import java.util.concurrent.CompletableFuture;

public class MTROllamaCommands {
    
    public static void register(CommandBuilder<?> commandBuilder) {
        commandBuilder.then("ollama", ollamaBuilder -> {
            ollamaBuilder.permissionLevel(2);
            
            // Chat command
            ollamaBuilder.then("chat", chatBuilder -> {
                chatBuilder.then("message", StringArgumentType.greedyString(), messageBuilder -> {
                    messageBuilder.executes(context -> {
                        String message = context.getArgument("message", String.class);
                        return executeChat(context.getSource(), message);
                    });
                });
                chatBuilder.executes(context -> {
                    context.getSource().sendFailure(Component.literal("Usage: /mtr ollama chat <message>"));
                    return 0;
                });
            });
            
            // Status command
            ollamaBuilder.then("status", statusBuilder -> {
                statusBuilder.executes(context -> executeStatus(context));
            });
            
            // Analyze command
            ollamaBuilder.then("analyze", analyzeBuilder -> {
                analyzeBuilder.executes(context -> executeAnalyze(context));
            });
            
            // Optimize command
            ollamaBuilder.then("optimize", optimizeBuilder -> {
                optimizeBuilder.executes(context -> executeOptimize(context));
            });
            
            // Help command
            ollamaBuilder.then("help", helpBuilder -> {
                helpBuilder.executes(context -> executeHelp(context));
            });
        });
    }
    
    private static int executeChat(CommandSourceStack source, String message) {
        Entity entity = source.getEntity();
        if (!(entity instanceof ServerPlayer)) {
            source.sendFailure(Component.literal("This command can only be used by players"));
            return 0;
        }
        
        ServerPlayer player = (ServerPlayer) entity;
        OllamaConfig.loadConfig();
        
        if (!OllamaConfig.enableChatCommand) {
            source.sendFailure(Component.literal("Ollama chat command is disabled"));
            return 0;
        }
        
        String personality = OllamaConfig.overseerPersonality != null ? 
            OllamaConfig.overseerPersonality : "Train Management Assistant";
        
        source.sendSuccess(() -> Component.literal("§6[" + personality + "] §fGathering MTR system context..."), false);
        
        String baseUrl = OllamaConfig.ollamaUrl != null ? OllamaConfig.ollamaUrl : "http://localhost:11434";
        String model = OllamaConfig.defaultModel != null ? OllamaConfig.defaultModel : "llama2";
        OllamaClient client = new OllamaClient(baseUrl, model);
        
        String mtrContext = null;
        if (OllamaConfig.enableWorldContext) {
            try {
                MTRWorldContext.MTRSystemInfo mtrInfo = MTRWorldContext.gatherMTRContext(player);
                mtrContext = MTRWorldContext.formatMTRContextForAI(mtrInfo);
            } catch (Exception e) {
                source.sendSuccess(() -> Component.literal("§e[" + personality + "] §fMTR context unavailable, responding with general knowledge..."), false);
            }
        }
        
        client.sendMessage(message, mtrContext).thenAccept(response -> {
            if (source.getServer() != null) {
                source.getServer().execute(() -> 
                    source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false)
                );
            } else {
                source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false);
            }
        }).exceptionally(throwable -> {
            if (source.getServer() != null) {
                source.getServer().execute(() -> 
                    source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()))
                );
            } else {
                source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()));
            }
            return null;
        });
        
        return 1;
    }
    
    private static int executeStatus(CommandSourceStack source) {
        OllamaConfig.loadConfig();
        source.sendSuccess(() -> Component.literal("[Ollama] Checking server status..."), false);
        
        String baseUrl = OllamaConfig.ollamaUrl != null ? OllamaConfig.ollamaUrl : "http://localhost:11434";
        String model = OllamaConfig.defaultModel != null ? OllamaConfig.defaultModel : "llama2";
        OllamaClient client = new OllamaClient(baseUrl, model);
        
        client.isServerAvailable().thenAccept(available -> {
            if (source.getServer() != null) {
                source.getServer().execute(() -> {
                    if (available) {
                        source.sendSuccess(() -> Component.literal("[Ollama] Server is online and ready"), false);
                    } else {
                        source.sendFailure(Component.literal("[Ollama] Server is offline or unreachable"));
                    }
                });
            } else {
                if (available) {
                    source.sendSuccess(() -> Component.literal("[Ollama] Server is online and ready"), false);
                } else {
                    source.sendFailure(Component.literal("[Ollama] Server is offline or unreachable"));
                }
            }
        }).exceptionally(throwable -> {
            if (source.getServer() != null) {
                source.getServer().execute(() -> 
                    source.sendFailure(Component.literal("[Ollama] Error checking status: " + throwable.getMessage()))
                );
            } else {
                source.sendFailure(Component.literal("[Ollama] Error checking status: " + throwable.getMessage()));
            }
            return null;
        });
        
        return 1;
    }
    
    private static int executeAnalyze(CommandSourceStack source) {
        Entity entity = source.getEntity();
        if (!(entity instanceof ServerPlayer)) {
            source.sendFailure(Component.literal("This command can only be used by players"));
            return 0;
        }
        
        ServerPlayer player = (ServerPlayer) entity;
        OllamaConfig.loadConfig();
        
        if (!OllamaConfig.enableNetworkAnalysis) {
            source.sendFailure(Component.literal("Network analysis is disabled"));
            return 0;
        }
        
        String personality = OllamaConfig.overseerPersonality != null ? 
            OllamaConfig.overseerPersonality : "Train Management Assistant";
        
        source.sendSuccess(() -> Component.literal("[" + personality + "] Analyzing your MTR network..."), false);
        
        try {
            MTRWorldContext.MTRSystemInfo mtrInfo = MTRWorldContext.gatherMTRContext(player);
            String mtrContext = MTRWorldContext.formatMTRContextForAI(mtrInfo);
            
            String analysisPrompt = "Please analyze this MTR train network and provide insights. " +
                "Suggest improvements, identify potential issues, and recommend optimizations for routes, stations, and depots.";
            
            String baseUrl = OllamaConfig.ollamaUrl != null ? OllamaConfig.ollamaUrl : "http://localhost:11434";
            String model = OllamaConfig.defaultModel != null ? OllamaConfig.defaultModel : "llama2";
            OllamaClient client = new OllamaClient(baseUrl, model);
            
            client.sendMessage(analysisPrompt, mtrContext).thenAccept(response -> {
                if (source.getServer() != null) {
                    source.getServer().execute(() -> 
                        source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false)
                    );
                } else {
                    source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false);
                }
            }).exceptionally(throwable -> {
                if (source.getServer() != null) {
                    source.getServer().execute(() -> 
                        source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()))
                    );
                } else {
                    source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()));
                }
                return null;
            });
        } catch (Exception e) {
            source.sendFailure(Component.literal("[" + personality + "] Error analyzing network: " + e.getMessage()));
        }
        
        return 1;
    }
    
    private static int executeOptimize(CommandSourceStack source) {
        Entity entity = source.getEntity();
        if (!(entity instanceof ServerPlayer)) {
            source.sendFailure(Component.literal("This command can only be used by players"));
            return 0;
        }
        
        ServerPlayer player = (ServerPlayer) entity;
        OllamaConfig.loadConfig();
        
        if (!OllamaConfig.enableRouteOptimization) {
            source.sendFailure(Component.literal("Route optimization is disabled"));
            return 0;
        }
        
        String personality = OllamaConfig.overseerPersonality != null ? 
            OllamaConfig.overseerPersonality : "Train Management Assistant";
        
        source.sendSuccess(() -> Component.literal("[" + personality + "] Analyzing routes for optimization..."), false);
        
        try {
            MTRWorldContext.MTRSystemInfo mtrInfo = MTRWorldContext.gatherMTRContext(player);
            String mtrContext = MTRWorldContext.formatMTRContextForAI(mtrInfo);
            
            String optimizationPrompt = "Please analyze this MTR train network and provide specific route optimization suggestions. " +
                "Focus on improving efficiency, reducing travel times, and optimizing station connections.";
            
            String baseUrl = OllamaConfig.ollamaUrl != null ? OllamaConfig.ollamaUrl : "http://localhost:11434";
            String model = OllamaConfig.defaultModel != null ? OllamaConfig.defaultModel : "llama2";
            OllamaClient client = new OllamaClient(baseUrl, model);
            
            client.sendMessage(optimizationPrompt, mtrContext).thenAccept(response -> {
                if (source.getServer() != null) {
                    source.getServer().execute(() -> 
                        source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false)
                    );
                } else {
                    source.sendSuccess(() -> Component.literal("[" + personality + "] " + response), false);
                }
            }).exceptionally(throwable -> {
                if (source.getServer() != null) {
                    source.getServer().execute(() -> 
                        source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()))
                    );
                } else {
                    source.sendFailure(Component.literal("[" + personality + "] Error: " + throwable.getMessage()));
                }
                return null;
            });
        } catch (Exception e) {
            source.sendFailure(Component.literal("[" + personality + "] Error optimizing routes: " + e.getMessage()));
        }
        
        return 1;
    }
    
    private static int executeHelp(CommandSourceStack source) {
        source.sendSuccess(() -> Component.literal("§6=== MTR Ollama Commands ==="), false);
        source.sendSuccess(() -> Component.literal("§b/mtr ollama chat <message> §7- Chat with AI about trains"), false);
        source.sendSuccess(() -> Component.literal("§b/mtr ollama status §7- Check Ollama server status"), false);
        source.sendSuccess(() -> Component.literal("§b/mtr ollama analyze §7- Analyze your train network"), false);
        source.sendSuccess(() -> Component.literal("§b/mtr ollama optimize §7- Get route optimization suggestions"), false);
        source.sendSuccess(() -> Component.literal("§b/mtr ollama help §7- Show this help"), false);
        return 1;
    }
}
