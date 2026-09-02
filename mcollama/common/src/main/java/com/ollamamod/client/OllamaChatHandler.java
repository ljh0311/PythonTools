package com.ollamamod.client;

import com.ollamamod.OllamaMod;
import com.ollamamod.config.OllamaConfig;
import com.ollamamod.platform.Platform;
import com.ollamamod.session.ConversationManager;
import net.minecraft.commands.CommandSourceStack;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class OllamaChatHandler {
    private final OllamaClient ollamaClient;
    private final ConversationManager conversationManager;
    private final Platform platform;
    private final CommandExecutor commandExecutor;
    private final CommandResultListener resultListener;
    private final ActionSequenceLearner sequenceLearner;

    private static final Pattern COMMAND_PATTERN = Pattern.compile(
        "(?i)(?:execute|run|do|use)\\s+(?:command\\s+)?(/[^\\s]+(?:\\s+[^\\n]+)?)"
    );

    public OllamaChatHandler(Platform platform) {
        this.platform = platform;
        this.conversationManager = new ConversationManager();
        this.ollamaClient = new OllamaClient(conversationManager);
        this.resultListener = new CommandResultListener();
        this.commandExecutor = new CommandExecutor(resultListener);
        this.sequenceLearner = new ActionSequenceLearner();
        this.ollamaClient.setSequenceLearner(sequenceLearner);
    }

    public void handleChatMessage(String message, String playerName) {
        if (!OllamaConfig.enableGui && !OllamaConfig.enableChatCommand) {
            return;
        }

        if (!ollamaClient.isAvailable()) {
            OllamaMod.LOGGER.warn("Ollama server is not available at {}", OllamaConfig.ollamaUrl);
            return;
        }

        ollamaClient.sendMessage(message, playerName).thenAccept(response -> {
            if (platform.isClient()) {
                OllamaMod.LOGGER.info("AI Response: {}", response);
            }
        }).exceptionally(throwable -> {
            OllamaMod.LOGGER.error("Error processing chat message", throwable);
            return null;
        });
    }

    public void executeCommandWithSource(String command, String playerName, String context,
                                        CommandSourceStack source) {
        String refusal = commandExecutor.validateCommand(command);
        if (refusal != null) {
            ClientFeedback.error(refusal);
            return;
        }

        commandExecutor.executeCommand(command, source).thenAccept(result -> {
            String failureReason = null;
            if (!result.success && OllamaConfig.enableFailureAnalysis) {
                failureReason = FailureReasonAnalyzer.analyzeFailure(
                    command, result.errorMessage, result.output
                );
            }

            if (OllamaConfig.enableCommandLearning) {
                sequenceLearner.recordCommandWithDetails(
                    playerName, command, context, result, failureReason
                );
            }

            if (result.success) {
                ClientFeedback.info("Executed: " + command);
                if (!result.output.isEmpty()) {
                    ClientFeedback.info(result.output);
                }
            } else {
                String message = failureReason != null && !failureReason.isEmpty()
                    ? failureReason
                    : (result.errorMessage.isEmpty() ? "Command failed: " + command : result.errorMessage);
                ClientFeedback.error(message);
            }
        });
    }

    public String extractCommandFromResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return null;
        }

        Matcher matcher = COMMAND_PATTERN.matcher(response);
        if (matcher.find()) {
            return matcher.group(1).trim();
        }

        Pattern directCommand = Pattern.compile("(?:^|\\s)(/[^\\s]+(?:\\s+[^\\n\\r]+)?)");
        Matcher directMatcher = directCommand.matcher(response);
        if (directMatcher.find()) {
            String cmd = directMatcher.group(1).trim();
            if (cmd.startsWith("/")) {
                return cmd;
            }
        }

        return null;
    }

    public ConversationManager getConversationManager() {
        return conversationManager;
    }

    public OllamaClient getOllamaClient() {
        return ollamaClient;
    }

    public ActionSequenceLearner getSequenceLearner() {
        return sequenceLearner;
    }

    public CommandExecutor getCommandExecutor() {
        return commandExecutor;
    }

    public CommandResultListener getResultListener() {
        return resultListener;
    }
}
