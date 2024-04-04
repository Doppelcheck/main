const serverHost = "[localhost:8000]";
const instanceID = "[unique instance identification]";
const versionClient = "[version number]";

const mainContentStyle = `[main content style]`;
const sidebarStyle = `[sidebar style]`;
const sidebarContentStyle = `[sidebar content style]`;


const ProxyUrlServices = {
    localBypass(originalUrl) {
        const urlEncoded = encodeURIComponent(originalUrl);
        return `https://${serverHost}/get_content/?url=${urlEncoded}`;
    },

    corsError() {
        const proxyUrl = ProxyUrlServices.localBypass(window.location.href);

        InitializeDoppelcheck.notifyUser(
            `<p>Connection to the Doppelcheck server failed. This may be due to ` +
            `restrictive security settings on the current website.</p>${window.location.hostname}<p>Please use ` +
            `Doppelcheck on <a href="${proxyUrl}" target="_blank">an accessible version of this website</a> and ` +
            `make sure the Doppelcheck server is running at ` +
            `<a href="https://${serverHost}" target="_blank">${serverHost}</a>.</p>`,
            false);
    },

    setupError(error, configUrl) {
        InitializeDoppelcheck.notifyUser(
            `Server error: ${error}. Please install the latest bookmarklet version from ` +
            `<a href="${configUrl}" target="_blank">here,</a> make sure all interfaces are configured, and ` +
            `<a href="${window.location.href}">refresh</a> this page.`);
    }
};

const CSSStyling = {
    reduceZIndex(maxZIndex) {
        const allElements = document.querySelectorAll('*');

        allElements.forEach(el => {
            const style = window.getComputedStyle(el);
            const zIndex = parseInt(style.zIndex, 10);
            if (!isNaN(zIndex) && zIndex > maxZIndex) {
                el.style.zIndex = maxZIndex;
            }
        });
    },

    addStyle(url, parentElement) {
        const doppelcheckStyle = document.createElement("link");
        doppelcheckStyle.rel = "stylesheet";
        doppelcheckStyle.href = url;
        parentElement.appendChild(doppelcheckStyle);
    },

    loadStyles(cssText, parentElement) {
        const style = document.createElement('style');
        style.textContent = cssText;
        parentElement.appendChild(style);
    },

    async loadExternalStyles(url, parentElement) {
        try {
            const response = await fetch(url);
            const cssText = await response.text();

            this.loadStyles(cssText, parentElement);

        } catch (error) {
            console.error('Failed to load external styles:', error);
        }
    },
}

const InitializeDoppelcheck = {
    shadowElement: null,

    getElementById(id) {
        return InitializeDoppelcheck.shadowElement.getElementById(id);
    },

    getElementsByClassName(className) {
        return InitializeDoppelcheck.shadowElement.querySelectorAll(`.${className}`);
    },

    async createSidebar(container) {
        const sidebar = document.createElement("div");
        InitializeDoppelcheck.shadowElement = sidebar.attachShadow({mode: 'open'});

        //await InitializeDoppelcheck.loadExternalStyles(`https://${address}/static/pico.css`, InitializeDoppelcheck.shadowElement)

        const shadowContainer = document.createElement("div");
        shadowContainer.id = "doppelcheck-shadow-container";
        InitializeDoppelcheck.shadowElement.appendChild(shadowContainer);

        //CSSStyling.addStyle(`https://${serverHost}/static/sidebar-content.css`, InitializeDoppelcheck.shadowElement)
        CSSStyling.loadStyles(sidebarContentStyle, InitializeDoppelcheck.shadowElement)

        // CSSStyling.addStyle(`https://${address}/static/pico.css`, InitializeDoppelcheck.shadowElement)

        sidebar.id = "doppelcheck-sidebar";
        container.appendChild(sidebar);
        return shadowContainer;
    },

    moveBodyContentToContainer(container) {
        const body = document.body;
        while (body.firstChild) {
            container.appendChild(body.firstChild);
        }
        body.appendChild(container);
    },

    notifyUser(message, dismiss = true) {
        if (!dismiss) {
            const dismissButton = InitializeDoppelcheck.getElementById("doppelcheck-dismiss-button");
            dismissButton.disabled = true;
        }

        const notificationContent = InitializeDoppelcheck.getElementById("doppelcheck-notification-content");
        notificationContent.innerHTML = message;

        const notificationOverlay = InitializeDoppelcheck.getElementById("doppelcheck-notification-overlay");
        notificationOverlay.classList.remove("hidden");
    },

    addNotificationArea: function (sidebar) {
        const notificationOverlay = document.createElement("div");
        notificationOverlay.id = "doppelcheck-notification-overlay";
        notificationOverlay.classList.add("hidden");

        const notificationContent = document.createElement("div");
        notificationContent.id = "doppelcheck-notification-content";
        notificationOverlay.appendChild(notificationContent);

        const dismissButton = document.createElement("button");
        dismissButton.id = "doppelcheck-dismiss-button";
        dismissButton.innerText = "Dismiss";
        dismissButton.onclick = function () {
            notificationOverlay.classList.add("hidden");
        }
        notificationOverlay.appendChild(dismissButton);
        sidebar.appendChild(notificationOverlay);
    },

    async addDoppelcheckElements() {
        CSSStyling.reduceZIndex(1000);

        // CSSStyling.addStyle(`https://${serverHost}/static/main-content.css`, document.head)
        CSSStyling.loadStyles(mainContentStyle, document.head)

        // CSSStyling.addStyle(`https://${serverHost}/static/sidebar.css`, document.head)
        CSSStyling.loadStyles(sidebarStyle, document.head)

        const bodyWrapper = document.createElement("div");
        bodyWrapper.id = "doppelcheck-body-wrapper";

        const mainContent = document.createElement("div");
        mainContent.id = "doppelcheck-main-content";
        InitializeDoppelcheck.moveBodyContentToContainer(mainContent);
        bodyWrapper.appendChild(mainContent);

        const sidebar = await InitializeDoppelcheck.createSidebar(bodyWrapper);
        document.body.appendChild(bodyWrapper);
        InitializeDoppelcheck.addNotificationArea(sidebar);

        let config;
        try {
            config = await getConfig(instanceID);

        } catch (error) {
            // request failed, offer redirection
            ProxyUrlServices.corsError();
            return;
        }

        const configUrl = `https://${serverHost}/config/${instanceID}`;
        if (config["error"]) {
            // server setup problem
            ProxyUrlServices.setupError(config["error"], configUrl);
            return;
        }

        const heading = document.createElement("h1");
        heading.id = "doppelcheck-heading";
        heading.innerText = config["nameInstance"];
        sidebar.appendChild(heading);

        const nameInstance = document.createElement("h2");
        nameInstance.id = "doppelcheck-version";
        nameInstance.innerText = `Client v${versionClient}`;
        sidebar.appendChild(nameInstance);

        const instanceId = document.createElement("div");
        instanceId.id = "doppelcheck-instance-id";
        instanceId.innerText = instanceID;
        sidebar.appendChild(instanceId);

        const dataSourcesList = document.createElement("ol");
        dataSourcesList.id = "doppelcheck-data-sources-list";
        config["dataSources"].forEach(source => {
            const listItem = document.createElement("li");
            listItem.innerText = source;
            dataSourcesList.appendChild(listItem);
        });

        sidebar.appendChild(dataSourcesList);
        const menu = document.createElement("div");
        menu.id = "doppelcheck-menu";
        menu.innerHTML =
            `<a href="${configUrl}" target="_blank">config</a> | ` +
            `<a href="https://${serverHost}/doc/" target="_blank">doc</a> | ` +
            `<a href="https://github.com/Doppelcheck" target="_blank">github</a>`
        sidebar.appendChild(menu);

        const subheading = document.createElement("h3");
        subheading.id = "doppelcheck-subheading";
        subheading.innerText = "Keypoints";
        sidebar.appendChild(subheading);

        const extractKeypoints = document.createElement("button");
        extractKeypoints.id = "doppelcheck-button-start";
        extractKeypoints.innerText = "Full website";
        extractKeypoints.addEventListener("click", async function () {
            extractKeypoints.disabled = true;
            const fullHTML = document.documentElement.outerHTML;
            exchange("keypoint", fullHTML);
        });
        sidebar.appendChild(extractKeypoints);

        const addKeypoint = document.createElement("button");
        addKeypoint.id = "doppelcheck-button-add";
        addKeypoint.innerText = "Text selection";
        addKeypoint.disabled = true;
        addKeypoint.addEventListener("click", async function () {
            addKeypoint.disabled = true;
            extractKeypoints.disabled = true;
            // addKeypoint.innerText = "⏳ Adding keypoint from selection...";
            const selection = document.getSelection();
            const selectedText = selection.toString();
            exchange("keypoint_selection", selectedText);
        });
        sidebar.appendChild(addKeypoint);

        const clipboardKeypoint = document.createElement("button");
        clipboardKeypoint.id = "doppelcheck-button-clipboard";
        clipboardKeypoint.innerText = "From clipboard";
        clipboardKeypoint.disabled = true;
        clipboardKeypoint.addEventListener("click", async function () {
            clipboardKeypoint.disabled = true;
            extractKeypoints.disabled = true;
            // addKeypoint.innerText = "⏳ Adding keypoint from selection...";
            const selection = await navigator.clipboard.readText();
            const selectedText = selection.toString();
            exchange("keypoint_selection", selectedText);
        });
        sidebar.appendChild(clipboardKeypoint);

        document.addEventListener("selectionchange", function () {
            const selection = document.getSelection();
            if (selection === null || 100 >= selection.toString().trim().length) {
                addKeypoint.disabled = true;
            } else {
                addKeypoint.disabled = false;
            }
        });

        document.addEventListener("copy", async function () {
            const selection = await navigator.clipboard.readText();
            const selectedText = selection.toString();
            if (selection === null || 100 >= selectedText.trim().length) {
                clipboardKeypoint.disabled = true;
            } else {
                clipboardKeypoint.disabled = false;
            }
        });

        const keypointContainer = document.createElement("div");
        keypointContainer.id = "doppelcheck-keypoints-container";
        sidebar.appendChild(keypointContainer);

        // add disabled text area as log?

        // add mark.js
        const markJs = document.createElement("script");
        markJs.src = `https://${serverHost}/static/mark.min.js`;
        markJs.defer = true;
        document.head.appendChild(markJs);

        // addSidebarScopedCss()
    }
}

const ExtractKeypoints = {
    receivingKeypointIds: new Set(),

    removeKeypoint(keypointId) {
        console.log("removing keypoint", keypointId);

        const keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-each-keypoint-container-${keypointId}`);
        if (keypoint) {
            keypoint.remove();
        }
        this.removeHighlight(keypointId);

        const allKeypointsContainer = InitializeDoppelcheck.getElementById("doppelcheck-keypoints-container");
        if (allKeypointsContainer.childElementCount === 0) {
            const extractKeypoints = InitializeDoppelcheck.getElementById("doppelcheck-button-start");
            extractKeypoints.disabled = false;
        }
    },

    addKeypoint(keypointId, keypointsContainer) {
        const eachkeypointContainer = document.createElement("details");
        eachkeypointContainer.classList.add("doppelcheck-each-keypoint-container");
        eachkeypointContainer.id = `doppelcheck-each-keypoint-container-${keypointId}`;
        eachkeypointContainer.setAttribute("onclick", "return false;");
        keypointsContainer.appendChild(eachkeypointContainer);

        const keypoint = document.createElement("summary");
        keypoint.id = `doppelcheck-keypoint-${keypointId}`;
        keypoint.classList.add("doppelcheck-keypoint");
        keypoint.classList.add(`doppelcheck-keypoint-${keypointId}`);
        eachkeypointContainer.appendChild(keypoint);

        const getSourcesButton = document.createElement("button");
        getSourcesButton.innerText = "🕵 Find sources";
        getSourcesButton.id = `doppelcheck-retrieve-button-${keypointId}`;
        getSourcesButton.addEventListener("click", function () {
            getSourcesButton.disabled = true;
            keypoint.textContent = keypoint.textContent + " 🕵";
            getSourcesButton.innerText = "⏳ Finding sources...";
            RetrieveSources.getSources(keypointId);
        });
        eachkeypointContainer.appendChild(getSourcesButton);

        const removeKeypointButton = document.createElement("button");
        removeKeypointButton.innerText = "❌ Remove";
        removeKeypointButton.addEventListener("click", function () {
            ExtractKeypoints.removeKeypoint(keypointId);
        });
        eachkeypointContainer.appendChild(removeKeypointButton);

        return keypoint;
    },

    segmentWords(text, segmentLength) {
        const words = text.split(/\s+/);
        const segments = [];
        for (let i = 0; i <= words.length - segmentLength; i++) {
            // Join with a regular expression pattern as a string
            const regexPattern = words.slice(i, i + segmentLength).join('\\s+');
            segments.push(new RegExp(regexPattern, 'g')); // Create a RegExp object
        }
        return segments;
    },

    processQuoteMessage(response) {
        const highlight = response["content"]
        const keypointId = response["keypoint_id"] % 10;

        const markInstance = new Mark(document.querySelector("#doppelcheck-main-content"));

        for (const regexPattern of ExtractKeypoints.segmentWords(highlight, 5)) {
            markInstance.markRegExp(regexPattern, {
                "acrossElements": true,
                "className": `doppelcheck-keypoint-${keypointId}`
            });
        }
    },

    elevateChildrenOfElements(tagName, className) {
        // Select all elements with the specified tag and class
        const elements = document.querySelectorAll(`${tagName}.${className}`);

        // Iterate over the NodeList
        elements.forEach(element => {
            // While the element has child nodes, insert them before the element itself
            while (element.firstChild) {
                element.parentNode.insertBefore(element.firstChild, element);
            }
            // After moving all children, remove the element
            element.parentNode.removeChild(element);
        });
    },

    removeHighlight(keypointId) {
        this.elevateChildrenOfElements("mark", `doppelcheck-keypoint-${keypointId}`);
    },

    processKeypointMessage(response) {
        console.log("keypoint", response);

        const stopMessage = response["stop"];
        const stopAllMessages = response["stop_all"];

        const keypointId = response["keypoint_id"] % 10;

        if (stopMessage) {
            this.receivingKeypointIds.delete(keypointId);
            const eachKeypointContainer = InitializeDoppelcheck.getElementById(
                `doppelcheck-each-keypoint-container-${keypointId}`
            );
            eachKeypointContainer.removeAttribute("onclick");
            return;
        }

        const messageContent = response["content"];

        const allKeypointsContainer = InitializeDoppelcheck.getElementById("doppelcheck-keypoints-container");

        let keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-keypoint-${keypointId}`);
        if (!keypoint) {
            keypoint = ExtractKeypoints.addKeypoint(keypointId, allKeypointsContainer);
        }
        keypoint.textContent += messageContent;
    }
}

const RetrieveSources = {
    addSource(keypointId, sourceId, sourcesContainer) {
        const sourceContainer = document.createElement("div");
        sourceContainer.classList.add("doppelcheck-source-container");
        sourceContainer.id = `doppelcheck-source-${keypointId}-${sourceId}`;
        sourcesContainer.appendChild(sourceContainer);
        return sourceContainer;
    },

    getSources(keypointId) {
        console.log(`checking keypoint ${keypointId}`);
        const keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-keypoint-${keypointId}`);
        keypoint.onclick = null;
        const keypointText = keypoint.textContent;
        const data = {"keypoint_id": keypointId, "keypoint_text": keypointText}
        exchange("sourcefinder", data);
    },

    addSourcesContainer(keypointId) {
        const sourcesContainer = document.createElement("div");
        sourcesContainer.id = `doppelcheck-sources-container-${keypointId}`;
        sourcesContainer.classList.add("doppelcheck-sources-container");

        const eachKeypointContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-each-keypoint-container-${keypointId}`
        );
        eachKeypointContainer.prepend(sourcesContainer);
        return sourcesContainer;
    },

    processSourcefinderMessage(response) {
        console.log("retrieval");

        const keypointId = response["keypoint_id"] % 10;
        const sourceId = response["source_id"];
        const lastMessage = response["stop"];
        const dataSource = response["data_source"];
        const query = response["query"];

        // replace button with sources container
        let allSourcesContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-sources-container-${keypointId}`
        )
        if (!allSourcesContainer) {
            allSourcesContainer = RetrieveSources.addSourcesContainer(keypointId);
        }

        const eachSourceContainer = RetrieveSources.addSource(keypointId, sourceId, allSourcesContainer);

        if (lastMessage) {
            const retrieveButton = InitializeDoppelcheck.getElementById(`doppelcheck-retrieve-button-${keypointId}`);
            retrieveButton.remove();

            const keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-keypoint-${keypointId}`);
            keypoint.textContent = keypoint.textContent.replace("🕵", "📑");
            return;
        }

        const buttonContainer = document.createElement("div");
        buttonContainer.id = `doppelcheck-button-container-${keypointId}-${sourceId}`;

        const sourceUri = response["content"];
        const sourceTitle = response["title"] || sourceUri;

        const link = document.createElement("a");
        link.id = `doppelcheck-source-link-${keypointId}-${sourceId}`;
        link.href = sourceUri;
        link.target = "_blank";
        link.innerHTML = `${dataSource}:<br />${sourceTitle}`;
        link.title = query;
        link.setAttribute("data-source", dataSource);

        eachSourceContainer.appendChild(link);

        const crosscheckButton = document.createElement("button");
        crosscheckButton.id = `doppelcheck-compare-button-${keypointId}-${sourceId}`;
        crosscheckButton.classList.add("doppelcheck-compare-button");
        buttonContainer.appendChild(crosscheckButton);
        crosscheckButton.textContent = "Crosscheck";
        crosscheckButton.onclick = function () {
            crosscheckButton.disabled = true;
            crosscheckButton.textContent = "🧐 Crosschecking...";
            CrosscheckSources.initiateCrosscheck(keypointId, sourceId);
        }

        eachSourceContainer.appendChild(buttonContainer);

    }
}

const CrosscheckSources = {
    initiateCrosscheck(keypointId, sourceId) {
        const keypointContainer = InitializeDoppelcheck.getElementById(`doppelcheck-keypoint-${keypointId}`);

        const sourceLink = InitializeDoppelcheck.getElementById(`doppelcheck-source-link-${keypointId}-${sourceId}`);
        if (!sourceLink) {
            alert(`Source URI not found for keypoint ${keypointId} and source ${sourceId}`);
            return;
        }
        const sourceUri = sourceLink.href;
        const dataSource = sourceLink.getAttribute('data-source');

        const keypoint = keypointContainer.textContent.replace("📑", "").trim();
        exchange("crosschecker",
            {
                "keypoint_id": keypointId,
                "keypoint_text": keypoint,
                "source_id": sourceId,
                "source_uri": sourceUri,
                "data_source": dataSource
            }
        );
    },

    processRatingMessage(response) {
        console.log("comparison");

        const content = response["content"];
        const keypointId = response["keypoint_id"] % 10;
        const sourceId = response["source_id"]


        let sourceSummaryElement = InitializeDoppelcheck.getElementById(`doppelcheck-source-summary-${keypointId}-${sourceId}`);
        if (!sourceSummaryElement) {
            const buttonContainer = InitializeDoppelcheck.getElementById(`doppelcheck-button-container-${keypointId}-${sourceId}`);
            buttonContainer.remove();

            const sourceContainer = InitializeDoppelcheck.getElementById(`doppelcheck-source-${keypointId}-${sourceId}`);

            const sourceDetailsElement = document.createElement("details");
            sourceDetailsElement.id = `doppelcheck-source-details-${keypointId}-${sourceId}`;
            sourceDetailsElement.classList.add("doppelcheck-source-details");
            sourceContainer.appendChild(sourceDetailsElement);

            sourceSummaryElement = document.createElement("summary");
            sourceSummaryElement.id = `doppelcheck-source-summary-${keypointId}-${sourceId}`;
            sourceSummaryElement.classList.add("doppelcheck-source-summary");
            sourceSummaryElement.textContent = "⏳ ";
            sourceDetailsElement.appendChild(sourceSummaryElement);

            const crosscheckExplanation = document.createElement("div");
            crosscheckExplanation.id = `doppelcheck-source-explanation-${keypointId}-${sourceId}`;
            crosscheckExplanation.classList.add("doppelcheck-source-explanation", "doppelcheck-explanation-container");
            sourceDetailsElement.appendChild(crosscheckExplanation);

        }

        sourceSummaryElement.textContent += content;
    },

    processExplanationMessage(response) {
        console.log("comparison");

        const content = response["content"];
        const lastMessage = response["stop"];
        const keypointId = response["keypoint_id"] % 10;
        const sourceId = response["source_id"]

        if (lastMessage) {
            const sourceSummaryElement = InitializeDoppelcheck.getElementById(`doppelcheck-source-summary-${keypointId}-${sourceId}`);
            sourceSummaryElement.textContent = sourceSummaryElement.textContent.replace("⏳ ", "");
            return;
        }

        const matchExplanation = InitializeDoppelcheck.getElementById(`doppelcheck-source-explanation-${keypointId}-${sourceId}`);
        matchExplanation.textContent += content;
    }
}

function exchange(messageType, content) {
    try {
        const ws = new WebSocket(`wss://${serverHost}/talk`);

        const message = {
            "message_type": messageType,
            "instance_id": instanceID,
            "original_url": window.location.href,
            "content": content
        };

        const messageStr = JSON.stringify(message);

        ws.onopen = function (event) {
            ws.send(messageStr);
        }

        ws.onmessage = function (event) {
            const response = JSON.parse(event.data);
            switch (response["message_type"]) {
                case "pong_message":
                    if (messageType === "ping") {
                        console.log(`Communication with ${response["instance_id"]} established`);
                    } else {
                        console.log(`unexpected pong response to: ${messageType}`);
                    }
                    break;

                case "error_message":
                    console.error("error message: ", response);
                    InitializeDoppelcheck.notifyUser("<p>Server error!</p>" + response["content"], false);
                    break;

                case "quote_message":
                    // [x]
                    ExtractKeypoints.processQuoteMessage(response);
                    break;

                case "keypoint_message":
                    // [x]
                    ExtractKeypoints.processKeypointMessage(response);
                    break;

                case "sources_message":
                    // [x]
                    RetrieveSources.processSourcefinderMessage(response);
                    break;

                case "rating_message":
                    // [x]
                    CrosscheckSources.processRatingMessage(response);
                    break;

                case "explanation_message":
                    // [x]
                    CrosscheckSources.processExplanationMessage(response);
                    break;

                case "log_message":
                    // [ ]
                    console.error("logs not implemented");
                    InitializeDoppelcheck.notifyUser("<p>Server logs:</p>" + response["content"], false);
                    break;

                default:
                    console.log(`unknown message type: ${response["message_type"]}`);
                    InitializeDoppelcheck.notifyUser(
                        `<p>Unknown message type: ${response["message_type"]}</p>`, false);
            }
        }

        ws.onerror = function (event) {
            console.log("Error performing WebSocket communication ", event);
            ProxyUrlServices.corsError();
        }


    } catch (error) {
        console.error("Websocket connection failed: ", error);
        ProxyUrlServices.corsError();
    }

}


async function getConfig(instanceId) {
    const configUrl = `https://${serverHost}/get_config/`;
    const instanceData = {instance_id: instanceId, version: versionClient};
    console.log("instance data ", instanceData)

    const response = await fetch(configUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(instanceData)
    });

    if (!response.ok) {
        console.warn(`HTTP error! status: ${response.status}`);
        return;
    }

    return await response.json();
}

async function main() {
    const sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");

    } else {
        await InitializeDoppelcheck.addDoppelcheckElements();
    }
}

main().then(r => console.log("doppelcheck main done"));
