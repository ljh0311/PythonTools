package com.ollamamod.client;

import com.ollamamod.OllamaMod;
import com.ollamamod.config.OllamaConfig;
import net.minecraft.commands.CommandSourceStack;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public class CommandExecutor {
    private final CommandResultListener resultListener;
    private static final Set<String> DESTRUCTIVE_COMMANDS = new HashSet<>(Arrays.asList(
        "kill", "ban", "kick", "deop", "stop", "save-all", "save-off"
    ));

    public CommandExecutor(CommandResultListener resultListener) {
        this.resultListener = resultListener;
    }

    public CompletableFuture<CommandResult> executeCommand(String command, CommandSourceStack source) {
        CompletableFuture<CommandResult> future = new CompletableFuture<>();

        String refusal = validateCommand(command);
        if (refusal != null) {
            future.complete(new CommandResult(false, "", refusal, 0, System.currentTimeMillis()));
            return future;
        }

        if (source.getServer() == null) {
            future.complete(new CommandResult(false, "",
                "Command execution requires a server (single-player or LAN).",
                0, System.currentTimeMillis()));
            return future;
        }

        source.getServer().execute(() -> {
            try {
                String commandId = UUID.randomUUID().toString();
                resultListener.registerCommand(commandId, command);

                int resultCode = source.getServer().getCommands().performPrefixedCommand(source, command);

                CommandResultListener.CapturedResult captured = resultListener.getResult(commandId);
                resultListener.unregisterCommand(commandId);

                boolean success = resultCode > 0;
                String output = captured != null ? captured.output : "";
                String errorMessage = captured != null ? captured.errorMessage : "";

                if (success && (output == null || output.isEmpty())) {
                    output = "Command executed successfully";
                }

                future.complete(new CommandResult(success, output, errorMessage, resultCode,
                    System.currentTimeMillis()));
            } catch (Exception e) {
                OllamaMod.LOGGER.error("Error executing command: {}", command, e);
                future.complete(new CommandResult(false, "",
                    "Error executing command: " + e.getMessage(), 0, System.currentTimeMillis()));
            }
        });

        return future;
    }

    /** Returns a player-facing refusal reason, or null if the command may run. */
    public String validateCommand(String command) {
        if (!OllamaConfig.enableCommandExecution) {
            return "Command execution is disabled. Set enableCommandExecution to true in ollamamod.json.";
        }

        if (command == null || command.trim().isEmpty()) {
            return "No command to execute.";
        }

        if (!isCommandSafe(command)) {
            return "Command is not on the execution whitelist or is blacklisted: " + command;
        }

        if (OllamaConfig.blockDestructiveCommands && isDestructive(command)) {
            return "Destructive command blocked: " + command;
        }

        return null;
    }

    public boolean isCommandSafe(String command) {
        if (command == null || command.trim().isEmpty()) {
            return false;
        }

        String commandLower = normalizeCommandRoot(command);

        for (String blacklisted : OllamaConfig.commandExecutionBlacklist) {
            if (commandLower.equals(blacklisted.toLowerCase())) {
                return false;
            }
        }

        for (String whitelistedCmd : OllamaConfig.commandExecutionWhitelist) {
            if (commandLower.equals(whitelistedCmd.toLowerCase())) {
                return true;
            }
        }

        return false;
    }

    private static boolean isDestructive(String command) {
        String root = normalizeCommandRoot(command);
        return DESTRUCTIVE_COMMANDS.contains(root);
    }

    private static String normalizeCommandRoot(String command) {
        String trimmed = command.trim();
        if (trimmed.startsWith("/")) {
            trimmed = trimmed.substring(1);
        }
        int space = trimmed.indexOf(' ');
        return (space >= 0 ? trimmed.substring(0, space) : trimmed).toLowerCase(Locale.ROOT);
    }

    public static class CommandResult {
        public final boolean success;
        public final String output;
        public final String errorMessage;
        public final int resultCode;
        public final long timestamp;

        public CommandResult(boolean success, String output, String errorMessage,
                           int resultCode, long timestamp) {
            this.success = success;
            this.output = output != null ? output : "";
            this.errorMessage = errorMessage != null ? errorMessage : "";
            this.resultCode = resultCode;
            this.timestamp = timestamp;
        }
    }
}
