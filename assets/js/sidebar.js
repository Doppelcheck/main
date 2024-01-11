console.log("sidebar.js loaded");

function startStreaming(idSuffix) {
    console.log("startStreaming() called");

    const loadButton = document.getElementById(`loadButton${idSuffix}`);
    const processingIndicator = document.getElementById(`processingIndicator${idSuffix}`);
    const dataAreaUnorderedList = document.getElementById(`dataArea${idSuffix}`);

    loadButton.style.display = 'none'
    processingIndicator.style.display = 'block';

    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onmessage = function(event) {
        console.log("Data received:", event.data);

        const dataArea = document.createElement('li');
        dataArea.innerText = event.data;
        dataAreaUnorderedList.appendChild(dataArea);
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
