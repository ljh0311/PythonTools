package com.ollamamod.client;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class FailureReasonAnalyzerTest {

    @Test
    void mapsUnknownCommand() {
        String reason = FailureReasonAnalyzer.analyzeFailure(
            "/give", "Unknown or incomplete command", "");
        assertTrue(reason.toLowerCase().contains("syntax") || reason.toLowerCase().contains("recognized"));
    }

    @Test
    void mapsPermissionDenied() {
        String reason = FailureReasonAnalyzer.analyzeFailure(
            "/op player", "You do not have permission to run this command", "");
        assertTrue(reason.toLowerCase().contains("permission"));
    }
}
