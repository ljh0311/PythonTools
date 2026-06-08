#include "network.h"
#include "lwip/ip4_addr.h"
#include <string.h>

static struct udp_pcb *udp_pcb = NULL;
static command_callback_t command_callback = NULL;
static bool wifi_initialized = false;

// UDP receive callback
static void udp_receive_callback(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                               const ip_addr_t *addr, u16_t port) {
    if (p != NULL && command_callback != NULL) {
        // Copy received data to buffer
        char buffer[COMMAND_BUFFER_SIZE];
        size_t copy_len = p->len > (COMMAND_BUFFER_SIZE - 1) ? (COMMAND_BUFFER_SIZE - 1) : p->len;
        memset(buffer, 0, COMMAND_BUFFER_SIZE);
        memcpy(buffer, p->payload, copy_len);
        
        // Process command
        command_callback(buffer);
        
        // Free the packet buffer
        pbuf_free(p);
    }
}

// Initialize network subsystem
bool network_init(void) {
    // Initialize WiFi
    if (cyw43_arch_init()) {
        printf("Failed to initialize cyw43_arch\n");
        return false;
    }
    
    wifi_initialized = true;
    
    // Connect to WiFi
    if (!wifi_connect()) {
        printf("Failed to connect to WiFi\n");
        return false;
    }
    
    // Initialize UDP
    if (!udp_init()) {
        printf("Failed to initialize UDP\n");
        return false;
    }
    
    return true;
}

// Connect to WiFi network
bool wifi_connect(void) {
    if (!wifi_initialized) {
        return false;
    }
    
    printf("Connecting to WiFi...\n");
    
    cyw43_arch_enable_sta_mode();
    
    // Attempt to connect with timeout
    absolute_time_t timeout_time = make_timeout_time_ms(WIFI_CONNECT_TIMEOUT_MS);
    int result = cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, 
                                                  CYW43_AUTH_WPA2_AES_PSK, 
                                                  WIFI_CONNECT_TIMEOUT_MS);
    
    if (result) {
        printf("Failed to connect to WiFi (%d)\n", result);
        return false;
    }
    
    printf("Connected to WiFi\n");
    return true;
}

// Initialize UDP
bool udp_init(void) {
    // Create new UDP PCB
    udp_pcb = udp_new();
    if (!udp_pcb) {
        printf("Failed to create UDP PCB\n");
        return false;
    }
    
    // Bind to UDP port
    err_t err = udp_bind(udp_pcb, IP_ADDR_ANY, UDP_PORT);
    if (err) {
        printf("Failed to bind UDP PCB (%d)\n", err);
        udp_remove(udp_pcb);
        udp_pcb = NULL;
        return false;
    }
    
    // Set receive callback
    udp_recv(udp_pcb, udp_receive_callback, NULL);
    
    printf("UDP initialized on port %d\n", UDP_PORT);
    return true;
}

// Network polling
void network_poll(void) {
    if (wifi_initialized) {
        cyw43_arch_poll();
    }
}

// Cleanup network resources
void network_cleanup(void) {
    if (udp_pcb) {
        udp_remove(udp_pcb);
        udp_pcb = NULL;
    }
    
    if (wifi_initialized) {
        cyw43_arch_deinit();
        wifi_initialized = false;
    }
}

// Set command callback
void network_set_command_callback(command_callback_t callback) {
    command_callback = callback;
} 