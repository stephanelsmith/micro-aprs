// static/js/scripts.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // Elements
    const transmissionStatus = document.getElementById('transmission-status');
    const receptionStatus = document.getElementById('reception-status');
    const restartReceptionBtn = document.getElementById('restart-reception');
    const configForm = document.getElementById('config-form');
    const saveConfigBtn = document.getElementById('save-config');
    const receivedMessages = document.getElementById('received-messages');

    // Fetch and display configuration
    fetch('/api/config')
        .then(response => response.json())
        .then(config => {
            populateConfigForm(config);
        })
        .catch(error => console.error('Error fetching config:', error));

    // Populate the configuration form
    function populateConfigForm(config) {
        const configParams = [
            { label: "Frequency (Hz)", key: "frequency_hz", type: "number" },
            { label: "Gain", key: "gain", type: "number" },
            { label: "IF Gain", key: "if_gain", type: "number" },
            { label: "Source Callsign", key: "callsign_source", type: "text" },
            { label: "Destination Callsign", key: "callsign_dest", type: "text" },
            { label: "Flags Before", key: "flags_before", type: "number" },
            { label: "Flags After", key: "flags_after", type: "number" },
            { label: "Send IP", key: "send_ip", type: "text" },
            { label: "Send Port", key: "send_port", type: "number" },
            { label: "Carrier Only", key: "carrier_only", type: "checkbox" },
            { label: "Device Index", key: "device_index", type: "number" },
        ];

        configParams.forEach(param => {
            const div = document.createElement('div');
            div.classList.add('form-group');

            const label = document.createElement('label');
            label.textContent = param.label + ":";
            label.htmlFor = param.key;
            div.appendChild(label);

            if (param.type === 'checkbox') {
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.id = param.key;
                input.name = param.key;
                input.checked = config[param.key];
                div.appendChild(input);
            } else {
                const input = document.createElement('input');
                input.type = param.type;
                input.id = param.key;
                input.name = param.key;
                input.value = config[param.key];
                div.appendChild(input);
            }

            configForm.appendChild(div);
        });
    }

    // Save configuration
    saveConfigBtn.addEventListener('click', () => {
        const formData = new FormData(configForm);
        const config = {};

        formData.forEach((value, key) => {
            const input = document.getElementById(key);
            if (input.type === 'checkbox') {
                config[key] = input.checked;
            } else if (input.type === 'number') {
                config[key] = parseFloat(value);
            } else {
                config[key] = value.trim();
            }
        });

        fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Configuration updated successfully.');
                // Optionally, refresh the page or fetch updated config
                location.reload();
            } else {
                alert('Error updating configuration: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error saving config:', error);
            alert('An error occurred while saving the configuration.');
        });
    });

    // Handle WebSocket messages for APRS messages
    socket.on('aprs_message', data => {
        receivedMessages.value += data.message + '\n';
        receivedMessages.scrollTop = receivedMessages.scrollHeight;

        // Optionally enforce maximum message limit
        const maxMessages = 1000;
        const messages = receivedMessages.value.split('\n');
        if (messages.length > maxMessages) {
            receivedMessages.value = messages.slice(messages.length - maxMessages).join('\n');
        }
    });

    // Handle status updates
    socket.on('transmission_status', data => {
        if (data.status === 'active') {
            transmissionStatus.textContent = 'Transmission: Active';
            transmissionStatus.style.color = 'red';
        } else {
            transmissionStatus.textContent = 'Transmission: Idle';
            transmissionStatus.style.color = 'green';
        }
    });

    socket.on('reception_status', data => {
        if (data.status === 'active') {
            receptionStatus.textContent = 'Reception: Active';
            receptionStatus.style.color = 'blue';
        } else if (data.status === 'stopped') {
            receptionStatus.textContent = 'Reception: Stopped';
            receptionStatus.style.color = 'gray';
        } else {
            receptionStatus.textContent = 'Reception: Idle';
            receptionStatus.style.color = 'green';
        }
    });

    socket.on('udp_listener_status', data => {
        // Implement similar to transmission and reception statuses if needed
        console.log('UDP Listener Status:', data.status);
    });

    socket.on('carrier_status', data => {
        // Implement similar to transmission and reception statuses if needed
        console.log('Carrier Status:', data.status);
    });

    socket.on('system_status', data => {
        console.log('System Status:', data.status);
    });

    socket.on('backend_restarted', data => {
        alert(data.message);
    });

    socket.on('system_error', data => {
        alert('System Error: ' + data.message);
    });

    // Handle restart reception button
    restartReceptionBtn.addEventListener('click', () => {
        fetch('/api/restart_reception', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Reception restarted successfully.');
            } else {
                alert('Error restarting reception: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error restarting reception:', error);
            alert('An error occurred while restarting reception.');
        });
    });
});
