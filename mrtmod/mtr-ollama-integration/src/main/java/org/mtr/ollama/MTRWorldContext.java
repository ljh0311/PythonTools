package org.mtr.ollama;

import net.minecraft.server.level.ServerPlayer;
import org.mtr.core.data.Data;
import org.mtr.core.data.Route;
import org.mtr.mod.Init;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

public class MTRWorldContext {
    
    public static MTRSystemInfo gatherMTRContext(ServerPlayer player) {
        MTRSystemInfo info = new MTRSystemInfo();
        info.playerName = player.getName().getString();
        
        try {
            // Access Main instance through reflection (since it's private in Init)
            Field mainField = Init.class.getDeclaredField("main");
            mainField.setAccessible(true);
            Object mainObj = mainField.get(null);
            
            if (mainObj == null) {
                info.error = "MTR system not initialized";
                return info;
            }
            
            // Get simulators using reflection
            Field simulatorsField = mainObj.getClass().getDeclaredField("simulators");
            simulatorsField.setAccessible(true);
            Object simulatorsObj = simulatorsField.get(mainObj);
            
            // Get world index
            String worldId = Init.getWorldId(player.getLevel());
            Field worldListField = Init.class.getDeclaredField("WORLD_ID_LIST");
            worldListField.setAccessible(true);
            @SuppressWarnings("unchecked")
            List<String> worldList = (List<String>) worldListField.get(null);
            int worldIndex = worldList.indexOf(worldId);
            
            if (worldIndex >= 0) {
                // Get simulator at index
                Object simulator = ((List<?>) simulatorsObj).get(worldIndex);
                
                // Get data from simulator
                Field dataField = simulator.getClass().getDeclaredField("data");
                dataField.setAccessible(true);
                Data data = (Data) dataField.get(simulator);
                
                // Gather station information
                info.stationCount = data.stations.size();
                info.platformCount = data.platforms.size();
                info.routeCount = data.routes.size();
                info.depotCount = data.depots.size();
                
                // Get station names
                List<String> stationNames = new ArrayList<>();
                data.stations.forEach(station -> {
                    if (stationNames.size() < 10) { // Limit to 10 stations
                        stationNames.add(station.getName());
                    }
                });
                info.stationNames = stationNames;
                
                // Get route information
                List<String> routeInfo = new ArrayList<>();
                data.routes.forEach(route -> {
                    if (routeInfo.size() < 10) { // Limit to 10 routes
                        String routeName = route.getName();
                        String routeNumber = route.getRouteNumber();
                        routeInfo.add(routeName + (routeNumber != null && !routeNumber.isEmpty() ? " (" + routeNumber + ")" : ""));
                    }
                });
                info.routeNames = routeInfo;
                
                // Get depot information
                List<String> depotInfo = new ArrayList<>();
                data.depots.forEach(depot -> {
                    if (depotInfo.size() < 5) { // Limit to 5 depots
                        depotInfo.add(depot.getName() + " - Routes: " + depot.routes.size());
                    }
                });
                info.depotNames = depotInfo;
                
                // Calculate network statistics
                int totalPlatforms = 0;
                for (Route route : data.routes) {
                    totalPlatforms += route.getRoutePlatforms().size();
                }
                info.totalPlatformsInRoutes = totalPlatforms;
                
            } else {
                info.error = "World not found in MTR system";
            }
        } catch (Exception e) {
            info.error = "Error gathering MTR context: " + e.getMessage();
            e.printStackTrace();
        }
        
        return info;
    }
    
    public static String formatMTRContextForAI(MTRSystemInfo info) {
        StringBuilder context = new StringBuilder();
        context.append("=== MTR TRAIN SYSTEM CONTEXT ===\n");
        context.append("Player: ").append(info.playerName).append("\n");
        
        if (info.error != null) {
            context.append("Error: ").append(info.error).append("\n");
            context.append("===============================\n");
            return context.toString();
        }
        
        context.append("Network Statistics:\n");
        context.append("  - Stations: ").append(info.stationCount).append("\n");
        context.append("  - Platforms: ").append(info.platformCount).append("\n");
        context.append("  - Routes: ").append(info.routeCount).append("\n");
        context.append("  - Depots: ").append(info.depotCount).append("\n");
        context.append("  - Total Platforms in Routes: ").append(info.totalPlatformsInRoutes).append("\n");
        
        if (!info.stationNames.isEmpty()) {
            context.append("\nStations:\n");
            for (String stationName : info.stationNames) {
                context.append("  - ").append(stationName).append("\n");
            }
            if (info.stationCount > info.stationNames.size()) {
                context.append("  ... and ").append(info.stationCount - info.stationNames.size()).append(" more\n");
            }
        }
        
        if (!info.routeNames.isEmpty()) {
            context.append("\nRoutes:\n");
            for (String routeName : info.routeNames) {
                context.append("  - ").append(routeName).append("\n");
            }
            if (info.routeCount > info.routeNames.size()) {
                context.append("  ... and ").append(info.routeCount - info.routeNames.size()).append(" more\n");
            }
        }
        
        if (!info.depotNames.isEmpty()) {
            context.append("\nDepots:\n");
            for (String depotName : info.depotNames) {
                context.append("  - ").append(depotName).append("\n");
            }
            if (info.depotCount > info.depotNames.size()) {
                context.append("  ... and ").append(info.depotCount - info.depotNames.size()).append(" more\n");
            }
        }
        
        context.append("===============================\n");
        return context.toString();
    }
    
    public static class MTRSystemInfo {
        public String playerName;
        public int stationCount;
        public int platformCount;
        public int routeCount;
        public int depotCount;
        public int totalPlatformsInRoutes;
        public List<String> stationNames = new ArrayList<>();
        public List<String> routeNames = new ArrayList<>();
        public List<String> depotNames = new ArrayList<>();
        public String error;
    }
}
