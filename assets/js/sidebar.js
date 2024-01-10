console.log("sidebar.js loaded");

function startStreaming() {
    console.log("startStreaming() called");

    const loadButton = document.getElementById(`loadButton`);
    const processingIndicator = document.getElementById(`processingIndicator`);
    const dataArea = document.getElementById(`dataArea`);

    loadButton.style.display = 'none'
    processingIndicator.style.display = 'block';

    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onmessage = function(event) {
        console.log("Data received:", event.data);
        dataArea.innerText += event.data + "\n";
    };

    ws.onopen = function(event) {
        console.log("Connected to WebSocket.");
    };

    ws.onerror = function(event) {
        console.error("WebSocket error observed:", event);
    };

    ws.onclose = function(event) {
        console.log("WebSocket connection closed:", event);
        processingIndicator.style.display = 'none';
    };
}
