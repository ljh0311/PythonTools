const { spawn } = require('child_process');
const path = require('path');

console.log('Starting Image Merger Application...\n');

// Function to start a process
function startProcess(command, args, name, cwd = process.cwd()) {
    console.log(`Starting ${name}...`);
    
    const process = spawn(command, args, {
        cwd: cwd,
        stdio: 'inherit',
        shell: true
    });

    process.on('error', (error) => {
        console.error(`Error starting ${name}:`, error);
    });

    process.on('close', (code) => {
        console.log(`${name} process exited with code ${code}`);
    });

    return process;
}

// Start backend server
const backendProcess = startProcess('python', ['backend.py'], 'Backend Server');

// Wait a bit for backend to start
setTimeout(() => {
    // Start frontend server
    const frontendProcess = startProcess('npm', ['start'], 'Frontend Server');
    
    console.log('\nBoth servers are starting...');
    console.log('Backend will be available at: http://localhost:5000');
    console.log('Frontend will be available at: http://localhost:3000');
    console.log('\nPress Ctrl+C to stop all servers\n');
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
        console.log('\nShutting down servers...');
        backendProcess.kill('SIGINT');
        frontendProcess.kill('SIGINT');
        process.exit(0);
    });
    
}, 3000); 