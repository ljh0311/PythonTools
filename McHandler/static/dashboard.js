// Dashboard-specific JavaScript with enhanced functionality

// Global state
let dashboardState = {
    lastUpdate: null,
    modCount: 0,
    shaderpackCount: 0,
    activityLog: [],
    recentMods: [],
    cache: new Map(),
    cacheTimeout: 30000 // 30 seconds
};

// Cache management
const cacheManager = {
    get(key) {
        const cached = dashboardState.cache.get(key);
        if (cached && Date.now() - cached.timestamp < dashboardState.cacheTimeout) {
            return cached.data;
        }
        dashboardState.cache.delete(key);
        return null;
    },
    
    set(key, data) {
        dashboardState.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    },
    
    clear() {
        dashboardState.cache.clear();
    }
};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupKeyboardShortcuts();
    loadActivityFromStorage();
    loadRecentModsFromStorage();
});

// Initialize dashboard components
function initializeDashboard() {
    // Check Ollama status
    checkOllamaStatus();
    
    // Update dashboard stats
    updateDashboardStats();
    
    // Load AI analysis
    loadAIAnalysis();
    
    // Setup action card click handlers
    setupActionCards();
    
    // Auto-refresh every 30 seconds
    setInterval(refreshDashboard, 30000);
    
    // Update last updated time
    updateLastUpdatedTime();
}

// Setup action card click handlers
function setupActionCards() {
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('click', function() {
            const action = this.dataset.action;
            if (action && typeof window[action] === 'function') {
                // Add visual feedback
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                    window[action]();
                }, 150);
            }
        });
    });
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or Cmd+R for refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            refreshDashboard();
            showToast('Dashboard refreshed', 'success');
        }
        
        // Number keys 1-4 for quick actions
        if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const actionCards = document.querySelectorAll('.action-card');
            const index = parseInt(e.key) - 1;
            if (actionCards[index]) {
                const action = actionCards[index].dataset.action;
                if (action) {
                    e.preventDefault();
                    actionCards[index].style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        actionCards[index].style.transform = '';
                        window[action]();
                    }, 150);
                }
            }
        }
    });
}

// Animated counter function
function animateCounter(element, target, duration = 1000) {
    const start = parseInt(element.dataset.current || 0) || 0;
    const end = parseInt(target) || 0;
    const increment = (end - start) / (duration / 16);
    let current = start;
    
    element.dataset.current = start;
    element.classList.add('animating');
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
            element.classList.remove('animating');
        }
        element.textContent = Math.floor(current);
        element.dataset.current = current;
    }, 16);
}

// Check Ollama status with enhanced display
function checkOllamaStatus() {
    fetch('/api/ollama/status')
        .then(response => response.json())
        .then(data => {
            const aiStatusElement = document.getElementById('ai-status');
            const aiModelsElement = document.getElementById('ai-models');
            const healthOllama = document.getElementById('health-ollama');
            
            if (data.connected) {
                aiStatusElement.textContent = 'Ready';
                aiStatusElement.className = 'stat-card-value';
                aiStatusElement.dataset.target = '1';
                if (aiModelsElement) {
                    aiModelsElement.textContent = `${data.models.length} models available`;
                }
                if (healthOllama) {
                    healthOllama.innerHTML = '<i class="fas fa-circle text-success"></i> Connected';
                }
            } else {
                aiStatusElement.textContent = 'Not Available';
                aiStatusElement.className = 'stat-card-value text-danger';
                aiStatusElement.dataset.target = '0';
                if (aiModelsElement) {
                    aiModelsElement.textContent = 'No models available';
                }
                if (healthOllama) {
                    healthOllama.innerHTML = '<i class="fas fa-circle text-danger"></i> Disconnected';
                }
            }
        })
        .catch(error => {
            console.error('Error checking Ollama status:', error);
            const aiStatusElement = document.getElementById('ai-status');
            const healthOllama = document.getElementById('health-ollama');
            aiStatusElement.textContent = 'Error';
            aiStatusElement.className = 'stat-card-value text-danger';
            if (healthOllama) {
                healthOllama.innerHTML = '<i class="fas fa-circle text-danger"></i> Error';
            }
        });
}

// Update dashboard stats with animations and caching
function updateDashboardStats() {
    const savedDir = localStorage.getItem('minecraftDirectory');
    if (savedDir) {
        // Check cache first
        const cacheKey = `mods-${savedDir}`;
        const cachedMods = cacheManager.get(cacheKey);
        
        if (cachedMods) {
            updateModsDisplay(cachedMods);
        } else {
            // Load mods
            fetch('/api/mods/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ minecraft_dir: savedDir })
            })
        .then(response => response.json())
        .then(data => {
            if (data.mods) {
                cacheManager.set(cacheKey, data.mods);
                updateModsDisplay(data.mods);
            }
        })
        .catch(error => {
            console.log('Could not load mods:', error);
        });
        }
        
        // Check cache for shaderpacks
        const shaderCacheKey = `shaderpacks-${savedDir}`;
        const cachedShaders = cacheManager.get(shaderCacheKey);
        
        if (cachedShaders) {
            updateShaderpacksDisplay(cachedShaders);
        } else {
            // Load shaderpacks
            fetch('/api/shaderpacks/load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ minecraft_dir: savedDir })
        })
        .then(response => response.json())
        .then(data => {
            if (data.shaderpacks) {
                cacheManager.set(shaderCacheKey, data.shaderpacks);
                updateShaderpacksDisplay(data.shaderpacks);
            }
        })
        .catch(error => {
            console.log('Could not load shaderpacks:', error);
        });
        }
    }
    
    // Update health status
    updateSystemHealth();
}

// Update mods display (extracted for reuse)
function updateModsDisplay(mods) {
    const modCountElement = document.getElementById('mod-count');
    const oldCount = dashboardState.modCount;
    dashboardState.modCount = mods.length;
    
    if (modCountElement) {
        modCountElement.dataset.target = mods.length;
        animateCounter(modCountElement, mods.length);
        
        // Update trend
        updateTrend('mod-trend', oldCount, mods.length);
    }
    
    // Update recent mods
    updateRecentMods(mods);
}

// Update shaderpacks display (extracted for reuse)
function updateShaderpacksDisplay(shaderpacks) {
    const shaderpackCountElement = document.getElementById('shaderpack-count');
    const oldCount = dashboardState.shaderpackCount;
    dashboardState.shaderpackCount = shaderpacks.length;
    
    if (shaderpackCountElement) {
        shaderpackCountElement.dataset.target = shaderpacks.length;
        animateCounter(shaderpackCountElement, shaderpacks.length);
        
        // Update trend
        updateTrend('shaderpack-trend', oldCount, shaderpacks.length);
    }
}

// Update trend indicator
function updateTrend(elementId, oldValue, newValue) {
    const trendElement = document.getElementById(elementId);
    if (!trendElement) return;
    
    if (oldValue === 0 || oldValue === newValue) {
        trendElement.textContent = '';
        trendElement.className = 'stat-card-trend';
        return;
    }
    
    const diff = newValue - oldValue;
    if (diff > 0) {
        trendElement.textContent = `+${diff} from last check`;
        trendElement.className = 'stat-card-trend up';
    } else {
        trendElement.textContent = `${diff} from last check`;
        trendElement.className = 'stat-card-trend down';
    }
}

// Update system health
function updateSystemHealth() {
    const healthApi = document.getElementById('health-api');
    const healthLastUpdate = document.getElementById('health-last-update');
    
    if (healthApi) {
        healthApi.innerHTML = '<i class="fas fa-circle text-success"></i> Good';
    }
    
    if (healthLastUpdate) {
        const now = new Date();
        healthLastUpdate.textContent = now.toLocaleTimeString();
    }
}

// Update last updated time
function updateLastUpdatedTime() {
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) {
        const now = new Date();
        lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        dashboardState.lastUpdate = now;
    }
}

// Load AI analysis
function loadAIAnalysis() {
    const savedDir = localStorage.getItem('minecraftDirectory');
    if (savedDir) {
        loadPlayerProfile(savedDir);
        loadCrashAnalysis(savedDir);
    }
}

// Load player profile with enhanced display and lazy loading
function loadPlayerProfile(minecraftDir) {
    const profileDiv = document.getElementById('player-profile');
    const placeholder = document.getElementById('player-profile-placeholder');
    
    if (!profileDiv) return;
    
    // Check cache first
    const cacheKey = `player-profile-${minecraftDir}`;
    const cached = cacheManager.get(cacheKey);
    
    if (cached) {
        displayPlayerProfile(cached);
        return;
    }
    
    // Show loading state
    profileDiv.classList.add('loading');
    if (placeholder) placeholder.style.display = 'none';
    
    // Lazy load - only fetch if visible or after a delay
    const loadProfile = () => {
        fetch('/api/mods/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ minecraft_dir: minecraftDir })
        })
        .then(response => response.json())
        .then(data => {
            profileDiv.classList.remove('loading');
            console.log('Player profile analysis response:', data);
            
            if (data.success && data.analysis) {
                // Cache the result
                cacheManager.set(cacheKey, data);
                displayPlayerProfile(data);
                
                // Log activity
                logActivity('AI Player Profile generated', 'success');
            } else {
                profileDiv.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>AI Analysis Unavailable:</strong> ${data.error || 'Unable to generate player profile'}
                    </div>
                `;
            }
        })
        .catch(error => {
            profileDiv.classList.remove('loading');
            profileDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Error:</strong> ${error.message}
                </div>
            `;
        });
    };
    
    // Use Intersection Observer for lazy loading
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                loadProfile();
                observer.disconnect();
            }
        }, { rootMargin: '50px' });
        
        observer.observe(profileDiv);
        
        // Fallback: load after 1 second if still not visible
        setTimeout(() => {
            if (profileDiv.classList.contains('loading')) {
                loadProfile();
                observer.disconnect();
            }
        }, 1000);
    } else {
        // Fallback for browsers without IntersectionObserver
        loadProfile();
    }
}

// Display player profile (extracted for reuse)
function displayPlayerProfile(data) {
    const profileDiv = document.getElementById('player-profile');
    if (!profileDiv) return;
    
    // Format the AI analysis with better markdown support
    const formattedAnalysis = formatMarkdown(data.analysis);
    
    profileDiv.innerHTML = `
        <div class="ai-analysis-content">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">
                    <i class="fas fa-robot me-2"></i>AI-Generated Player Profile
                </h6>
                <small class="text-readable">
                    Model: ${data.model_used} | ${new Date(data.timestamp).toLocaleTimeString()}
                </small>
            </div>
            <div class="analysis-text">
                ${formattedAnalysis}
            </div>
        </div>
    `;
    
    // Show copy/export buttons
    const copyBtn = document.getElementById('copy-profile-btn');
    const exportBtn = document.getElementById('export-profile-btn');
    if (copyBtn) copyBtn.style.display = 'inline-block';
    if (exportBtn) exportBtn.style.display = 'inline-block';
    
    // Make sections collapsible
    makeSectionsCollapsible(profileDiv);
}

// Load crash analysis with lazy loading
function loadCrashAnalysis(minecraftDir) {
    const analysisDiv = document.getElementById('crash-analysis');
    const placeholder = document.getElementById('crash-analysis-placeholder');
    
    if (!analysisDiv) return;
    
    // Check cache first
    const cacheKey = `crash-analysis-${minecraftDir}`;
    const cached = cacheManager.get(cacheKey);
    
    if (cached) {
        displayCrashAnalysis(cached);
        return;
    }
    
    // Show loading state
    analysisDiv.classList.add('loading');
    if (placeholder) placeholder.style.display = 'none';
    
    // Lazy load - only fetch if visible or after a delay
    const loadAnalysis = () => {
        fetch('/api/crash/analyze_directory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ minecraft_dir: minecraftDir })
        })
        .then(response => response.json())
        .then(data => {
            analysisDiv.classList.remove('loading');
            
            if (data.success && data.analysis) {
                // Cache the result
                cacheManager.set(cacheKey, data);
                displayCrashAnalysis(data);
            } else if (data.error) {
                // Check if it's a "no crashes" message or a real error
                const errorLower = (data.error || '').toLowerCase();
                const messageLower = (data.message || '').toLowerCase();
                if (errorLower.includes('no crash') || messageLower.includes('no crash')) {
                    // No crashes found
                    if (placeholder) placeholder.style.display = 'block';
                    analysisDiv.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>No Recent Crashes:</strong> Your Minecraft instance has been stable!
                        </div>
                    `;
                } else {
                    // Real error
                    if (placeholder) placeholder.style.display = 'block';
                    analysisDiv.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Analysis Unavailable:</strong> ${data.error}
                        </div>
                    `;
                }
            } else {
                // Fallback - no crashes
                if (placeholder) placeholder.style.display = 'block';
                analysisDiv.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>No Recent Crashes:</strong> Your Minecraft instance has been stable!
                    </div>
                `;
            }
        })
        .catch(error => {
            analysisDiv.classList.remove('loading');
            if (placeholder) placeholder.style.display = 'block';
            analysisDiv.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Analysis Unavailable:</strong> ${error.message}
                </div>
            `;
        });
    };
    
    // Use Intersection Observer for lazy loading
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                loadAnalysis();
                observer.disconnect();
            }
        }, { rootMargin: '50px' });
        
        observer.observe(analysisDiv);
        
        // Fallback: load after 1 second if still not visible
        setTimeout(() => {
            if (analysisDiv.classList.contains('loading')) {
                loadAnalysis();
                observer.disconnect();
            }
        }, 1000);
    } else {
        // Fallback for browsers without IntersectionObserver
        loadAnalysis();
    }
}

// Display crash analysis (extracted for reuse)
function displayCrashAnalysis(data) {
    const analysisDiv = document.getElementById('crash-analysis');
    if (!analysisDiv) return;
    
    const formattedAnalysis = formatMarkdown(data.analysis);
    
    analysisDiv.innerHTML = `
        <div class="ai-analysis-content">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">
                    <i class="fas fa-chart-line me-2"></i>AI Crash Analysis
                </h6>
                <small class="text-readable">
                    Model: ${data.model_used} | ${new Date(data.timestamp).toLocaleTimeString()}
                </small>
            </div>
            <div class="analysis-text">
                ${formattedAnalysis}
            </div>
        </div>
    `;
    
    // Show copy button
    const copyBtn = document.getElementById('copy-crash-btn');
    if (copyBtn) copyBtn.style.display = 'inline-block';
    
    // Make sections collapsible
    makeSectionsCollapsible(analysisDiv);
}

// Format markdown text
function formatMarkdown(text) {
    return text
        .replace(/### (.*?)(\n|$)/g, '<h6 class="mt-3 mb-2 text-primary">$1</h6>')
        .replace(/## (.*?)(\n|$)/g, '<h5 class="mt-4 mb-3 text-primary">$1</h5>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code class="bg-light px-1 rounded">$1</code>')
        .replace(/\n/g, '<br>');
}

// Make sections collapsible
function makeSectionsCollapsible(container) {
    const h5Elements = container.querySelectorAll('h5');
    h5Elements.forEach(h5 => {
        if (h5.nextElementSibling && !h5.classList.contains('collapsible')) {
            h5.classList.add('collapsible');
            h5.style.cursor = 'pointer';
            h5.innerHTML = `<i class="fas fa-chevron-down me-2"></i>${h5.textContent}`;
            
            let expanded = true;
            h5.addEventListener('click', function() {
                expanded = !expanded;
                const content = h5.nextElementSibling;
                if (content) {
                    if (expanded) {
                        content.style.maxHeight = content.scrollHeight + 'px';
                        h5.querySelector('i').className = 'fas fa-chevron-down me-2';
                    } else {
                        content.style.maxHeight = '0';
                        h5.querySelector('i').className = 'fas fa-chevron-right me-2';
                    }
                }
            });
        }
    });
}

// Copy analysis to clipboard
function copyAnalysis(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const textContent = container.textContent || container.innerText;
    
    if (textContent.trim()) {
        navigator.clipboard.writeText(textContent)
            .then(() => {
                showToast('Analysis copied to clipboard!', 'success');
            })
            .catch(() => {
                showToast('Failed to copy analysis', 'danger');
            });
    } else {
        showToast('No analysis to copy', 'warning');
    }
}

// Export analysis
function exportAnalysis(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const textContent = container.textContent || container.innerText;
    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Analysis exported!', 'success');
}

// Refresh dashboard
function refreshDashboard() {
    // Clear cache on manual refresh
    cacheManager.clear();
    
    checkOllamaStatus();
    updateDashboardStats();
    loadAIAnalysis();
    updateLastUpdatedTime();
    
    // Show refresh feedback
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        const originalHTML = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
        refreshBtn.disabled = true;
        
        setTimeout(() => {
            refreshBtn.innerHTML = originalHTML;
            refreshBtn.disabled = false;
        }, 1000);
    }
    
    logActivity('Dashboard refreshed', 'info');
}

// Refresh player profile
function refreshPlayerProfile() {
    const savedDir = localStorage.getItem('minecraftDirectory');
    if (savedDir) {
        loadPlayerProfile(savedDir);
        showToast('Refreshing player profile...', 'info');
    } else {
        showToast('Please set your Minecraft directory first', 'warning');
    }
}

// Navigation functions
function loadMods() {
    logActivity('Navigated to Mod Management', 'info');
    window.location.href = '/mods';
}

function loadShaderpacks() {
    logActivity('Navigated to Shaderpack Management', 'info');
    window.location.href = '/shaders';
}

function checkCompatibility() {
    logActivity('Navigated to Compatibility Check', 'info');
    window.location.href = '/compatibility';
}

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="toast-header bg-${type} text-white">
            <i class="fas fa-${getToastIcon(type)} me-2"></i>
            <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function getToastIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Activity logging
function logActivity(message, type = 'info') {
    const activity = {
        message,
        type,
        timestamp: new Date().toISOString()
    };
    
    dashboardState.activityLog.unshift(activity);
    if (dashboardState.activityLog.length > 10) {
        dashboardState.activityLog.pop();
    }
    
    saveActivityToStorage();
    updateActivityFeed();
}

function updateActivityFeed() {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;
    
    if (dashboardState.activityLog.length === 0) {
        feed.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-stream fa-2x mb-2"></i>
                <p class="mb-0">No recent activity</p>
            </div>
        `;
        return;
    }
    
    feed.innerHTML = dashboardState.activityLog.map(activity => `
        <div class="activity-item">
            <div>${activity.message}</div>
            <div class="activity-item-time">${new Date(activity.timestamp).toLocaleTimeString()}</div>
        </div>
    `).join('');
}

function saveActivityToStorage() {
    try {
        localStorage.setItem('dashboardActivity', JSON.stringify(dashboardState.activityLog));
    } catch (e) {
        console.error('Failed to save activity:', e);
    }
}

function loadActivityFromStorage() {
    try {
        const saved = localStorage.getItem('dashboardActivity');
        if (saved) {
            dashboardState.activityLog = JSON.parse(saved);
            updateActivityFeed();
        }
    } catch (e) {
        console.error('Failed to load activity:', e);
    }
}

// Recent mods management
function updateRecentMods(mods) {
    // Get recently modified mods (last 5)
    const recent = mods
        .sort((a, b) => {
            const aTime = new Date(a.modified || 0).getTime();
            const bTime = new Date(b.modified || 0).getTime();
            return bTime - aTime;
        })
        .slice(0, 5);
    
    dashboardState.recentMods = recent;
    saveRecentModsToStorage();
    updateRecentModsDisplay();
}

function updateRecentModsDisplay() {
    const list = document.getElementById('recent-mods-list');
    const count = document.getElementById('recent-mods-count');
    
    if (!list) return;
    
    if (dashboardState.recentMods.length === 0) {
        list.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-inbox fa-2x mb-2"></i>
                <p class="mb-0">No recent mods</p>
            </div>
        `;
        if (count) count.textContent = '0';
        return;
    }
    
    if (count) count.textContent = dashboardState.recentMods.length;
    
    list.innerHTML = dashboardState.recentMods.map(mod => {
        const name = mod.display_name || mod.name || 'Unknown';
        const time = mod.modified ? new Date(mod.modified).toLocaleDateString() : 'Unknown';
        return `
            <div class="recent-item">
                <div class="recent-item-name">${name}</div>
                <div class="recent-item-time">${time}</div>
            </div>
        `;
    }).join('');
}

function saveRecentModsToStorage() {
    try {
        localStorage.setItem('recentMods', JSON.stringify(dashboardState.recentMods));
    } catch (e) {
        console.error('Failed to save recent mods:', e);
    }
}

function loadRecentModsFromStorage() {
    try {
        const saved = localStorage.getItem('recentMods');
        if (saved) {
            dashboardState.recentMods = JSON.parse(saved);
            updateRecentModsDisplay();
        }
    } catch (e) {
        console.error('Failed to load recent mods:', e);
    }
}

// Listen for storage changes
window.addEventListener('storage', function(e) {
    if (e.key === 'minecraftDirectory') {
        updateDashboardStats();
        loadAIAnalysis();
    }
});

