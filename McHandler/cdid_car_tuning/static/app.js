// CDID Car Tuning Assistant - JavaScript

let ollamaStatusInterval;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check Ollama status
    checkOllamaStatus();
    
    // Set up status checking interval
    ollamaStatusInterval = setInterval(checkOllamaStatus, 30000); // Check every 30 seconds
    
    // Load available models
    loadOllamaModels();
    
    // ECU / Internal Electronics toggles
    setupEcuIeToggles();
    
    // Set up mode switching
    setupModeSwitching();
    
    // Set up form handlers
    setupFormHandlers();
}

// ECU / Internal Electronics toggles: show stage dropdown when available is on
function setupEcuIeToggles() {
    const ecuAvailable = document.getElementById('ecu-available');
    const ecuStageGroup = document.querySelector('.ecu-stage-group');
    const ieAvailable = document.getElementById('internal-electronics-available');
    const ieStageGroup = document.querySelector('.ie-stage-group');
    
    function toggleEcuStage() {
        if (ecuAvailable.checked) {
            ecuStageGroup.classList.remove('d-none');
        } else {
            ecuStageGroup.classList.add('d-none');
        }
    }
    function toggleIeStage() {
        if (ieAvailable.checked) {
            ieStageGroup.classList.remove('d-none');
        } else {
            ieStageGroup.classList.add('d-none');
        }
    }
    
    ecuAvailable.addEventListener('change', toggleEcuStage);
    ieAvailable.addEventListener('change', toggleIeStage);
    toggleEcuStage();
    toggleIeStage();
}

// Mode switching
function setupModeSwitching() {
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const tuneForm = document.getElementById('tune-form');
    const diagnoseForm = document.getElementById('diagnose-form');
    
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'tune') {
                tuneForm.classList.remove('d-none');
                diagnoseForm.classList.add('d-none');
            } else {
                tuneForm.classList.add('d-none');
                diagnoseForm.classList.remove('d-none');
            }
            // Hide results when switching modes
            document.getElementById('results-section').classList.add('d-none');
            document.getElementById('error-alert').classList.add('d-none');
        });
    });
}

// Form handlers
function setupFormHandlers() {
    // Tuning form
    document.getElementById('tuning-form').addEventListener('submit', function(e) {
        e.preventDefault();
        submitTuningRequest();
    });
    
    // Diagnosis form
    document.getElementById('diagnosis-form').addEventListener('submit', function(e) {
        e.preventDefault();
        submitDiagnosisRequest();
    });
    
    // Copy results button
    document.getElementById('copy-results-btn').addEventListener('click', copyResults);
}

// Check Ollama status
async function checkOllamaStatus() {
    try {
        const response = await fetch('/api/ollama/status');
        const data = await response.json();
        
        const statusElement = document.getElementById('ollama-status');
        const statusIcon = document.getElementById('ollama-status-icon');
        const statusText = document.getElementById('ollama-status-text');
        
        if (data.connected) {
            statusElement.classList.remove('bg-secondary', 'disconnected');
            statusElement.classList.add('connected');
            statusIcon.className = 'fas fa-circle me-1';
            statusText.textContent = `AI Ready (${data.model})`;
        } else {
            statusElement.classList.remove('bg-secondary', 'connected');
            statusElement.classList.add('disconnected');
            statusIcon.className = 'fas fa-circle me-1';
            statusText.textContent = 'AI Offline';
        }
    } catch (error) {
        console.error('Error checking Ollama status:', error);
        const statusElement = document.getElementById('ollama-status');
        const statusText = document.getElementById('ollama-status-text');
        statusElement.classList.remove('bg-secondary', 'connected');
        statusElement.classList.add('disconnected');
        statusText.textContent = 'AI Offline';
    }
}

// Load available Ollama models
async function loadOllamaModels() {
    try {
        const response = await fetch('/api/ollama/models');
        const data = await response.json();
        
        const tuneSelect = document.getElementById('model-select');
        const diagnoseSelect = document.getElementById('model-select-diagnose');
        
        // Clear existing options
        tuneSelect.innerHTML = '';
        diagnoseSelect.innerHTML = '';
        
        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const option1 = document.createElement('option');
                option1.value = model;
                option1.textContent = model;
                if (model === data.current_model) {
                    option1.selected = true;
                }
                tuneSelect.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = model;
                option2.textContent = model;
                if (model === data.current_model) {
                    option2.selected = true;
                }
                diagnoseSelect.appendChild(option2);
            });
        } else {
            const option1 = document.createElement('option');
            option1.value = '';
            option1.textContent = 'No models available';
            tuneSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = '';
            option2.textContent = 'No models available';
            diagnoseSelect.appendChild(option2);
        }
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Submit tuning request
async function submitTuningRequest() {
    const carDescription = document.getElementById('car-description').value.trim();
    const tuningGoals = document.getElementById('tuning-goals').value.trim();
    const model = document.getElementById('model-select').value;
    
    // Get focus areas
    const focusAreas = [];
    if (document.getElementById('focus-engine').checked) {
        focusAreas.push('engine');
    }
    if (document.getElementById('focus-suspension').checked) {
        focusAreas.push('suspension');
    }
    
    // ECU & Internal Electronics
    const ecuAvailable = document.getElementById('ecu-available').checked;
    const ecuStage = ecuAvailable ? parseInt(document.getElementById('ecu-stage').value, 10) : null;
    const internalElectronicsAvailable = document.getElementById('internal-electronics-available').checked;
    const internalElectronicsStage = internalElectronicsAvailable ? parseInt(document.getElementById('internal-electronics-stage').value, 10) : null;
    
    // Current setup (optional): turbo, supercharger, differential
    const parseNum = (id) => {
        const v = document.getElementById(id).value.trim();
        if (v === '') return null;
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    };
    const turboCharger = parseNum('turbo-charger');
    const boostPerTurbo = parseNum('boost-per-turbo');
    const superCharger = parseNum('super-charger');
    const superChargerBoost = parseNum('super-charger-boost');
    const frontDiffPower = parseNum('front-diff-power');
    const frontDiffCoast = parseNum('front-diff-coast');
    const frontDiffPreload = parseNum('front-diff-preload');
    const rearDiffPower = parseNum('rear-diff-power');
    const rearDiffCoast = parseNum('rear-diff-coast');
    const rearDiffPreload = parseNum('rear-diff-preload');
    const frontStiffness = parseNum('front-stiffness');
    const frontRideHeight = parseNum('front-ride-height');
    const frontDamping = parseNum('front-damping');
    const rearStiffness = parseNum('rear-stiffness');
    const rearRideHeight = parseNum('rear-ride-height');
    const rearDamping = parseNum('rear-damping');
    
    if (!carDescription || !tuningGoals) {
        showError('Please fill in all required fields');
        return;
    }
    
    if (focusAreas.length === 0) {
        showError('Please select at least one focus area');
        return;
    }
    
    // Check Ollama status first
    const statusResponse = await fetch('/api/ollama/status');
    const statusData = await statusResponse.json();
    
    if (!statusData.connected) {
        showError('Ollama is not connected. Please start Ollama first.');
        return;
    }
    
    // Show loading state
    const submitBtn = document.getElementById('tune-submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';
    
    // Hide previous results/errors
    document.getElementById('results-section').classList.add('d-none');
    document.getElementById('error-alert').classList.add('d-none');
    
    try {
        const response = await fetch('/api/tune', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                car_description: carDescription,
                tuning_goals: tuningGoals,
                focus_areas: focusAreas,
                model: model,
                ecu_available: ecuAvailable,
                ecu_stage: ecuStage,
                internal_electronics_available: internalElectronicsAvailable,
                internal_electronics_stage: internalElectronicsStage,
                turbo_charger: turboCharger,
                boost_per_turbo: boostPerTurbo,
                super_charger: superCharger,
                super_charger_boost: superChargerBoost,
                front_diff_power: frontDiffPower,
                front_diff_coast: frontDiffCoast,
                front_diff_preload: frontDiffPreload,
                rear_diff_power: rearDiffPower,
                rear_diff_coast: rearDiffCoast,
                rear_diff_preload: rearDiffPreload,
                front_stiffness: frontStiffness,
                front_ride_height: frontRideHeight,
                front_damping: frontDamping,
                rear_stiffness: rearStiffness,
                rear_ride_height: rearRideHeight,
                rear_damping: rearDamping
            })
        });
        
        const data = await response.json();
        
        // Reset button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Get Tuning Suggestions';
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Display results
        displayResults(data.suggestions, 'Tuning Suggestions');
        
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Get Tuning Suggestions';
        showError('Error: ' + error.message);
    }
}

// Submit diagnosis request
async function submitDiagnosisRequest() {
    const problemDescription = document.getElementById('problem-description').value.trim();
    const currentSettings = document.getElementById('current-settings').value.trim();
    const model = document.getElementById('model-select-diagnose').value;
    
    if (!problemDescription) {
        showError('Please describe the problem');
        return;
    }
    
    // Check Ollama status first
    const statusResponse = await fetch('/api/ollama/status');
    const statusData = await statusResponse.json();
    
    if (!statusData.connected) {
        showError('Ollama is not connected. Please start Ollama first.');
        return;
    }
    
    // Show loading state
    const submitBtn = document.getElementById('diagnose-submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Diagnosing...';
    
    // Hide previous results/errors
    document.getElementById('results-section').classList.add('d-none');
    document.getElementById('error-alert').classList.add('d-none');
    
    try {
        const response = await fetch('/api/diagnose', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                problem_description: problemDescription,
                current_settings: currentSettings,
                model: model
            })
        });
        
        const data = await response.json();
        
        // Reset button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-search me-2"></i>Diagnose Problem';
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Display results
        displayResults(data.diagnosis, 'Problem Diagnosis');
        
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-search me-2"></i>Diagnose Problem';
        showError('Error: ' + error.message);
    }
}

// Display results
function displayResults(content, title) {
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results-content');
    
    // Format the content (convert markdown-like formatting)
    let formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^### (.*$)/gim, '<h5>$1</h5>')
        .replace(/^## (.*$)/gim, '<h4>$1</h4>')
        .replace(/^# (.*$)/gim, '<h3>$1</h3>')
        .replace(/^- (.*$)/gim, '<li>$1</li>')
        .replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>')
        .replace(/\n/g, '<br>');
    
    // Wrap list items in ul tags
    formattedContent = formattedContent.replace(/(<li>.*?<\/li>(?:<br>)?)+/g, function(match) {
        return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
    });
    
    resultsContent.innerHTML = formattedContent;
    resultsSection.classList.remove('d-none');
    resultsSection.classList.add('fade-in');
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show error
function showError(message) {
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    errorAlert.classList.add('fade-in');
    
    // Scroll to error
    errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Copy results to clipboard
async function copyResults() {
    const resultsContent = document.getElementById('results-content');
    const text = resultsContent.textContent || resultsContent.innerText;
    
    try {
        await navigator.clipboard.writeText(text);
        
        // Show temporary success message
        const copyBtn = document.getElementById('copy-results-btn');
        const originalHTML = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
        copyBtn.classList.add('btn-success');
        copyBtn.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHTML;
            copyBtn.classList.remove('btn-success');
            copyBtn.classList.add('btn-outline-secondary');
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        showError('Failed to copy results to clipboard');
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (ollamaStatusInterval) {
        clearInterval(ollamaStatusInterval);
    }
});
