package org.mtr.ollama;

import net.minecraftforge.common.ForgeConfigSpec;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.config.ModConfigEvent;

@Mod.EventBusSubscriber(modid = "mtr", bus = Mod.EventBusSubscriber.Bus.MOD)
public class OllamaConfig {
    private static final ForgeConfigSpec.Builder BUILDER = new ForgeConfigSpec.Builder();
    
    private static final ForgeConfigSpec.ConfigValue<String> OLLAMA_URL = BUILDER
            .comment("The URL of the Ollama server")
            .define("ollamaUrl", "http://localhost:11434");
    
    private static final ForgeConfigSpec.ConfigValue<String> DEFAULT_MODEL = BUILDER
            .comment("The default model to use for AI responses")
            .define("defaultModel", "llama2");
    
    private static final ForgeConfigSpec.ConfigValue<Integer> TIMEOUT_SECONDS = BUILDER
            .comment("Timeout in seconds for AI requests")
            .defineInRange("timeoutSeconds", 120, 10, 600);
    
    private static final ForgeConfigSpec.ConfigValue<Boolean> ENABLE_CHAT_COMMAND = BUILDER
            .comment("Enable the /mtr ollama chat command")
            .define("enableChatCommand", true);
    
    private static final ForgeConfigSpec.ConfigValue<Boolean> ENABLE_WORLD_CONTEXT = BUILDER
            .comment("Enable MTR system context gathering for AI responses")
            .define("enableWorldContext", true);
    
    private static final ForgeConfigSpec.ConfigValue<String> OVERSEER_PERSONALITY = BUILDER
            .comment("The personality/role of the AI (e.g., 'Train Management Assistant', 'Route Optimizer')")
            .define("overseerPersonality", "Train Management Assistant");
    
    private static final ForgeConfigSpec.ConfigValue<Boolean> ENABLE_STREAMING = BUILDER
            .comment("Enable streaming responses (tokens appear as they are generated)")
            .define("enableStreaming", true);
    
    private static final ForgeConfigSpec.ConfigValue<Integer> MAX_CONTEXT_TOKENS = BUILDER
            .comment("Maximum number of tokens to keep in conversation context (0 = unlimited)")
            .defineInRange("maxContextTokens", 2048, 0, 16384);
    
    private static final ForgeConfigSpec.ConfigValue<Boolean> ENABLE_ROUTE_OPTIMIZATION = BUILDER
            .comment("Enable AI-powered route optimization suggestions")
            .define("enableRouteOptimization", true);
    
    private static final ForgeConfigSpec.ConfigValue<Boolean> ENABLE_NETWORK_ANALYSIS = BUILDER
            .comment("Enable AI analysis of train network")
            .define("enableNetworkAnalysis", true);
    
    static final ForgeConfigSpec SPEC = BUILDER.build();
    
    public static String ollamaUrl;
    public static String defaultModel;
    public static int timeoutSeconds;
    public static boolean enableChatCommand;
    public static boolean enableWorldContext;
    public static String overseerPersonality;
    public static boolean enableStreaming;
    public static int maxContextTokens;
    public static boolean enableRouteOptimization;
    public static boolean enableNetworkAnalysis;

    public static void loadConfig() {
        ollamaUrl = (String)OLLAMA_URL.get();
        defaultModel = (String)DEFAULT_MODEL.get();
        timeoutSeconds = (Integer)TIMEOUT_SECONDS.get();
        enableChatCommand = (Boolean)ENABLE_CHAT_COMMAND.get();
        enableWorldContext = (Boolean)ENABLE_WORLD_CONTEXT.get();
        overseerPersonality = (String)OVERSEER_PERSONALITY.get();
        enableStreaming = (Boolean)ENABLE_STREAMING.get();
        maxContextTokens = (Integer)MAX_CONTEXT_TOKENS.get();
        enableRouteOptimization = (Boolean)ENABLE_ROUTE_OPTIMIZATION.get();
        enableNetworkAnalysis = (Boolean)ENABLE_NETWORK_ANALYSIS.get();
    }

    @SubscribeEvent
    static void onLoad(ModConfigEvent event) {
        OllamaConfig.loadConfig();
    }

    static {
        OllamaConfig.loadConfig();
    }
}
