/**
 * not working:
 *   - NS_ERROR_CONTENT_BLOCKED:
 *     - https://www.tagesspiegel.de/potsdam/landeshauptstadt/nach-rechtem-geheimtreffen-potsdamer-versammeln-sich-zu-spontandemo-an-der-villa-adlon-11034931.html
 * working:
 *   - https://www.derstandard.de/story/3000000202667/warum-sich-suedafrika-im-gazakrieg-so-sehr-gegen-israel-stellt
 *   - https://www.zeit.de/politik/ausland/2024-01/rotes-meer-huthis-grossbritannien-usa-angriffe-jemen
 */

function startStreaming(idSuffix) {
    console.log("startStreaming() called");

    const loadButton = document.getElementById(`loadButton${idSuffix}`);
    const processingIndicator = document.getElementById(`processingIndicator${idSuffix}`);
    const dataAreaUnorderedList = document.getElementById(`dataArea${idSuffix}`);

    loadButton.style.display = 'none'
    processingIndicator.style.display = 'block';

    try {
        const ws = new WebSocket("wss://localhost:8000/ws");

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
    } catch (error) {
        alert("An error occurred while starting the WebSocket: " + error.toString());
        // Handle or report the error as needed
        loadButton.style.display = 'inline';
        processingIndicator.style.display = 'none';
        // Additional error handling code here
    }
}
