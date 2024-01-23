const domain = "localhost";
const serverHttpURL = `https://${domain}:8000/`;
const serverWsURL = `wss://${domain}:8000/`;

const getSidebarHTMLEndpoint = `${serverHttpURL}get_sidebar_html/`;
const getClaimsEndpoint = `${serverWsURL}get_claims/`;
const getDocumentsEndpoint = `${serverWsURL}get_documents/`;

const sidebarScriptURL = `${serverHttpURL}assets/js/sidebar.js`;
const sidebarStyleURL = `${serverHttpURL}assets/css/sidebar.css`;

function addSidebarElement() {
    const messageID = "random";
    ws.send("get_sidebar_html", messageID);

    ws.onmessage = function(event) {
        console.log("Data received:", event.data);
        const jsonData = JSON.parse(event.data);
        if (jsonData.messageID !== messageID) {
            return;
        }
        const html = jsonData.html;
        // add sidebar element
        const sidebarElement = document.createElement('div');
        sidebarElement.innerHTML = html;
        document.body.appendChild(sidebarElement);
    }

}

function addSidebarStyle() {
    const sidebarStyle = document.createElement('link');
    sidebarStyle.rel = "stylesheet";
    sidebarStyle.href = sidebarStyleURL;
    document.head.appendChild(sidebarStyle);
}

function addSidebarScript() {
    const sidebarScript = document.createElement('script');
    sidebarScript.src = sidebarScriptURL;
    document.head.appendChild(sidebarScript);
}

function addHtmxScript() {
    const htmxScript = document.createElement('script');
    htmxScript.src = "https://unpkg.com/htmx.org/dist/htmx.js";
    document.head.appendChild(htmxScript);
}

function addSidebar(ws) {
    addSidebarElement(ws);
    addSidebarStyle();
    addHtmxScript();
    addSidebarScript();
}

function getBody() {
    const body = document.body.outerHTML;
    return body;
}

function getElementByXPath(xPath) {
    const element = document.evaluate(
        xPath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
    ).singleNodeValue;
    return element;
}

function highlightPart(element, startIndex, endIndex, claimIndex) {
    return
}

function highlight(xPathSlice, claimIndex) {

    xPathSlice = {
        "xPaths": [],
        "indexRange": [0, 0]
    }

    const xPaths = xPathSlice.xPaths;
    const indexRange = xPathSlice.indexRange;

    let noXPaths = xPaths.length;
    let i = 0;
    for (const eachXPath of xPaths) {
        let eachElement = getElementByXPath(eachXPath);

        let startIndex = 0 ? i === 0 : indexRange[0]
        let endIndex = -1 ? i === noXPaths - 1 : indexRange[1];

        highlightPart(eachElement, startIndex, endIndex, claimIndex)

        i += 1;
    }
}

function updateSidebar(originalBody) {
    // send body via websocket, update sidebar with data as it arrives
    return

function initWebsocket() {
    const ws = new WebSocket(getClaimsEndpoint);

    ws.onopen = function(event) {
        console.log(`Connected to WebSocket. Sending body to server.`);
    };

    ws.onmessage = function(event) {
        console.log("Data received:", event.data);
    }

    ws.onerror = function(event) {
        console.error("WebSocket error observed:", event);
    }

    ws.onclose = function(event) {
        console.log("WebSocket connection closed:", event);
    }

    return ws;
}


function main() {
    const ws = initWebsocket();
    const originalBody = getBody();
    addSidebar(ws);
    updateSidebar(originalBody);
    // send body
    // receive body
    // replace body
}

function _main() {
    // base parameters
    // (the string "https://localhost:8000/" is replaced in this script with the actual server URL)

    const sidebarScriptURL = `${serverHttpURL}assets/js/sidebar.js`;

    // set additional css styles
    const styleElement = document.createElement('style');
    styleElement.innerHTML = "" +
        ".doppelchecked-text {\n" +
        "    position: fixed; /* Fixed position to stay in place during scrolling */\n" +
        "    top: 50%; /* Center vertically */\n" +
        "    left: 50%; /* Center horizontally */\n" +
        "    transform: translate(-50%, -50%); /* Adjust for exact centering */\n" +
        "    color: white; /* Text color */\n" +
        "    font-size: 100px; /* Text size */\n" +
        "    z-index: 10001; /* Ensure it's above the overlay */\n" +
        "}\n" +
        "\n" +
        ".doppelchecked-overlay {\n" +
        "    position: fixed; \n" +
        "    top: 0; \n" +
        "    left: 0; \n" +
        "    width: 100%; \n" +
        "    height: 100%; \n" +
        "    background: rgba(0, 0, 0, 0.5); \n" +
        "    z-index: 10000; \n" +
        "    pointer-events: auto; \n" +
        "}\n";
    document.head.appendChild(styleElement);

    // build payload
    let payload = {
        url: window.location.href,
        html: document.documentElement.outerHTML
    };

    // get selected text
    const sel = document.getSelection();
    if (sel !== null) {
        const selectedText = sel.toString().trim();
        if (0 < selectedText.length) {
            payload.selected_text = selectedText;
        }
    }

    // add overlay
    // todo: instead of overlay, show sidebar immediately. populate sidebar with data as it arrives.
    const overlay = document.createElement('div');
    overlay.addEventListener('click', function(event) {
        event.preventDefault();
        event.stopPropagation();
    }, true);
    overlay.classList.add('doppelchecked-overlay');
    const textContainer = document.createElement('div');
    textContainer.classList.add('doppelchecked-text');
    textContainer.textContent = "Processing..."; // Your text here
    overlay.appendChild(textContainer);
    document.body.appendChild(overlay);

    // send request
    console.log("sending: ", JSON.stringify(payload))
    fetch(`${endpoint}`, {
        method: 'POST', // or 'PUT', depending on your API
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })

    .then(response => response.json())

    .then(json_data => {
        // replace body
        console.log('Success:', json_data);
        if (json_data && "body" in json_data) {
            console.log("Replacing website body with new body");
            document.body.outerHTML = json_data.body;
            // loading scripts, must be after body alterations!
            const sidebarScript = document.createElement('script');
            sidebarScript.src = sidebarScriptURL;
            document.head.appendChild(sidebarScript);
        }

    })

    .catch((error) => {
        // revert to original body
        overlay.remove();
        styleElement.remove();

        console.error('Error:', error);
        alert(
            "An error occurred: Maybe the website's security policy is blocking the request. " +
            `Please copy and paste the relevant text or complete URL at ${serverHttpURL}.`
        );
    });
}

main()