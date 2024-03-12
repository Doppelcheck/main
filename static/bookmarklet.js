const serverHost = "[localhost:8000]";
const userID = "[unique user identification]";
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

    async createSidebar(container) {
        const sidebar = document.createElement("div");
        InitializeDoppelcheck.shadowElement = sidebar.attachShadow({ mode: 'open' });

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

    notifyUser(message, dismissable = true) {
        if (!dismissable) {
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
            config = await getConfig(userID);

        } catch (error) {
            // request failed, offer redirection
            ProxyUrlServices.corsError();
            return;
        }

        const configUrl = `https://${serverHost}/config/${userID}`;
        if (config["error"]) {
            // server setup problem
            ProxyUrlServices.setupError(config["error"], configUrl);
            return;
        }

        const heading = document.createElement("h1");
        heading.id = "doppelcheck-heading";
        heading.innerText = config["name_instance"];
        sidebar.appendChild(heading);

        const nameInstance = document.createElement("h2");
        nameInstance.id = "doppelcheck-version";
        nameInstance.innerText = `Client v${versionClient}`;
        sidebar.appendChild(nameInstance);

        const instanceId = document.createElement("div");
        instanceId.id = "doppelcheck-instance-id";
        instanceId.innerText = userID;
        sidebar.appendChild(instanceId);

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

        const claimContainer = document.createElement("div");
        claimContainer.id = "doppelcheck-claims-container";
        sidebar.appendChild(claimContainer);

        const button = document.createElement("button");
        button.id = "doppelcheck-button-start";
        button.innerText = "🤨 Extract keypoints";

        button.onclick = async function () {
            button.disabled = true;
            const selection = document.getSelection();
            if (selection === null || 20 >= selection.toString().trim().length) {
                button.innerText = "⏳ Extracting keypoints from website...";
                const fullHTML = document.documentElement.outerHTML;
                //try {
                exchange("keypoint", fullHTML);
                //} catch (error) {
                //    console.log('Websocket connection failed: ' + error);
                //    ProxyUrlServices.corsError();
                //}

            } else {
                button.innerText = "⏳ Extracting keypoints from selection...";
                const selectedText = selection.toString();
                exchange("keypoint_selection", selectedText);

            }
        }
        sidebar.appendChild(button);

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
    addKeypoint(keypointIndex, claimsContainer) {
        const eachClaimContainer = document.createElement("details");
        eachClaimContainer.classList.add("doppelcheck-each-claim-container");
        eachClaimContainer.id = `doppelcheck-each-claim-container${keypointIndex}`;
        eachClaimContainer.setAttribute("onclick", "return false;");
        claimsContainer.appendChild(eachClaimContainer);

        const claim = document.createElement("summary");
        claim.id = `doppelcheck-claim${keypointIndex}`;
        claim.classList.add("doppelcheck-claim");
        claim.classList.add(`doppelcheck-claim-${keypointIndex}`);
        eachClaimContainer.appendChild(claim);

        const getDocumentsButton = document.createElement("button");
        getDocumentsButton.innerText = "🕵 Find sources";
        getDocumentsButton.id = `doppelcheck-retrieve-button${keypointIndex}`;
        getDocumentsButton.onclick = function () {
            getDocumentsButton.disabled = true;
            claim.textContent = claim.textContent + " 🕵";
            getDocumentsButton.innerText = "⏳ Finding sources...";
            RetrieveSources.getDocuments(keypointIndex);
        }
        eachClaimContainer.appendChild(getDocumentsButton);

        return claim;
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
        const keypointIndex = response["keypoint_index"];

        const markInstance = new Mark(document.querySelector("#doppelcheck-main-content"));

        for (const regexPattern of ExtractKeypoints.segmentWords(highlight, 5)) {
            markInstance.markRegExp(regexPattern, {
                "acrossElements": true,
                "className": `doppelcheck-claim-${keypointIndex}`
            });
        }
    },

    processKeypointMessage(response) {
        const stopAllMessages = response["stop_all"];
        if (stopAllMessages) {
            const button = InitializeDoppelcheck.getElementById("doppelcheck-button-start");
            button.remove();
            return;
        }

        const keypointIndex = response["keypoint_index"];
        const stopMessage = response["stop"];
        if (stopMessage) {
            const eachKeypointContainer = InitializeDoppelcheck.getElementById(
                `doppelcheck-each-claim-container${keypointIndex}`
            );
            eachKeypointContainer.removeAttribute("onclick");
            return;
        }

        const messageContent = response["content"];

        const allKeypointsContainer = InitializeDoppelcheck.getElementById("doppelcheck-claims-container");

        let keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-claim${keypointIndex}`);
        if (!keypoint) {
            keypoint = ExtractKeypoints.addKeypoint(keypointIndex, allKeypointsContainer);
        }
        keypoint.textContent += messageContent;
    }
}

const RetrieveSources = {
    addSource(claimId, documentId, documentsContainer) {
        const documentContainer = document.createElement("div");
        documentContainer.classList.add("doppelcheck-document-container");
        documentContainer.id = `doppelcheck-document${claimId}-${documentId}`;
        documentsContainer.appendChild(documentContainer);
        return documentContainer;
    },

    getDocuments(keypointIndex) {
        console.log(`checking keypoint ${keypointIndex}`);
        const keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-claim${keypointIndex}`);
        keypoint.onclick = null;
        const keypointText = keypoint.textContent;
        const data = {"keypoint_index": keypointIndex, "keypoint_text": keypointText}
        exchange("sourcefinder", data);
    },

    addSourcesContainer(keypointIndex) {
        const sourcesContainer = document.createElement("div");
        sourcesContainer.id = `doppelcheck-documents-container${keypointIndex}`;
        sourcesContainer.classList.add("doppelcheck-documents-container");

        const eachKeypointContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-each-claim-container${keypointIndex}`
        );
        eachKeypointContainer.prepend(sourcesContainer);
        return sourcesContainer;
    },

    processSourcefinderMessage(response) {
        console.log("retrieval");

        const keypointIndex = response["keypoint_index"];
        const lastMessage = response["stop"];

        // replace button with documents container
        let allSourcesContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-documents-container${keypointIndex}`
        )
        if (!allSourcesContainer) {
            allSourcesContainer = RetrieveSources.addSourcesContainer(keypointIndex);
        }

        const sourceIndex = allSourcesContainer.childElementCount;
        const eachSourceContainer = RetrieveSources.addSource(keypointIndex, sourceIndex, allSourcesContainer);

        if (lastMessage) {
            if (sourceIndex === 0) {
                eachSourceContainer.innerText = "No documents found";
            }

            const retrieveButton = InitializeDoppelcheck.getElementById(`doppelcheck-retrieve-button${keypointIndex}`);
            retrieveButton.remove();

            const keypoint = InitializeDoppelcheck.getElementById(`doppelcheck-claim${keypointIndex}`);
            keypoint.textContent = keypoint.textContent.replace("🕵", "📑");
            return;
        }

        const buttonContainer = document.createElement("div");
        buttonContainer.id = `doppelcheck-button-container${keypointIndex}-${sourceIndex}`;

        const documentUri = response["content"];
        const documentTitle = response["title"] || documentUri;

        const link = document.createElement("a");
        link.id = `doppelcheck-document-link${keypointIndex}-${sourceIndex}`;
        link.href = documentUri;
        link.target = "_blank";
        link.textContent = documentTitle;
        eachSourceContainer.appendChild(link);

        const crosscheckButton = document.createElement("button");
        crosscheckButton.id = `doppelcheck-compare-button${keypointIndex}-${sourceIndex}`;
        crosscheckButton.classList.add("doppelcheck-compare-button");
        buttonContainer.appendChild(crosscheckButton);
        crosscheckButton.textContent = "Crosscheck";
        crosscheckButton.onclick = function () {
            crosscheckButton.disabled = true;
            crosscheckButton.textContent = "🧐 Crosschecking...";
            CrosscheckSources.initiateCrosscheck(keypointIndex, sourceIndex);
        }

        eachSourceContainer.appendChild(buttonContainer);

    }
}

const CrosscheckSources = {
    initiateCrosscheck(keypointIndex, sourceIndex) {
        const keypointContainer = InitializeDoppelcheck.getElementById(`doppelcheck-claim${keypointIndex}`);

        const sourceLink = InitializeDoppelcheck.getElementById(`doppelcheck-document-link${keypointIndex}-${sourceIndex}`);
        if (!sourceLink) {
            alert(`Document URI not found for keypoint ${keypointIndex} and source ${sourceIndex}`);
            return;
        }
        const sourceUri = sourceLink.href;

        const keypoint = keypointContainer.textContent.replace("📑", "").trim();
        exchange("crosschecker",
            {
                "keypoint_index": keypointIndex,
                "keypoint_text": keypoint,
                "source_index": sourceIndex,
                "source_uri": sourceUri
            }
        );
    },

    processRatingMessage(response){
        console.log("comparison");

        const content = response["content"];
        const keypointIndex = response["keypoint_index"];
        const sourceIndex = response["source_index"]


        let sourceSummaryElement = InitializeDoppelcheck.getElementById(`doppelcheck-document-summary${keypointIndex}-${sourceIndex}`);
        if (!sourceSummaryElement) {
            const buttonContainer = InitializeDoppelcheck.getElementById(`doppelcheck-button-container${keypointIndex}-${sourceIndex}`);
            buttonContainer.remove();

            const sourceContainer = InitializeDoppelcheck.getElementById(`doppelcheck-document${keypointIndex}-${sourceIndex}`);

            const sourceDetailsElement = document.createElement("details");
            sourceDetailsElement.id = `doppelcheck-document-details${keypointIndex}-${sourceIndex}`;
            sourceDetailsElement.classList.add("doppelcheck-document-details");
            sourceContainer.appendChild(sourceDetailsElement);

            sourceSummaryElement = document.createElement("summary");
            sourceSummaryElement.id = `doppelcheck-document-summary${keypointIndex}-${sourceIndex}`;
            sourceSummaryElement.classList.add("doppelcheck-document-summary");
            sourceSummaryElement.textContent = "⏳ ";
            sourceDetailsElement.appendChild(sourceSummaryElement);

            const crosscheckExplanation = document.createElement("div");
            crosscheckExplanation.id = `doppelcheck-document-explanation${keypointIndex}-${sourceIndex}`;
            crosscheckExplanation.classList.add("doppelcheck-document-explanation", "doppelcheck-explanation-container");
            sourceDetailsElement.appendChild(crosscheckExplanation);

        }

        sourceSummaryElement.textContent += content;
    },

    processExplanationMessage(response){
        console.log("comparison");

        const content = response["content"];
        const lastMessage = response["stop"];
        const keypointIndex = response["keypoint_index"];
        const sourceIndex = response["source_index"]

        if (lastMessage) {
            const sourceSummaryElement = InitializeDoppelcheck.getElementById(`doppelcheck-document-summary${keypointIndex}-${sourceIndex}`);
            sourceSummaryElement.textContent = sourceSummaryElement.textContent.replace("⏳ ", "");
            return;
        }

        const matchExplanation = InitializeDoppelcheck.getElementById(`doppelcheck-document-explanation${keypointIndex}-${sourceIndex}`);
        matchExplanation.textContent += content;
    }
}

function exchange(messageType, content) {
    try {
        const ws = new WebSocket(`wss://${serverHost}/talk`);

        const message = {
            "message_type": messageType,
            "user_id": userID,
            "original_url": window.location.href,
            "content": content
        };

        const messageStr = JSON.stringify(message);

        ws.onopen = function(event) {
            ws.send(messageStr);
        }

        ws.onmessage = function(event) {
            const response = JSON.parse(event.data);
            switch (response["message_type"]) {
                case "pong_message":
                    if (messageType === "ping") {
                        console.log(`Communication with ${response["user_id"]} established`);
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

        ws.onerror = function(event) {
            console.log("Error performing WebSocket communication ", event);
            ProxyUrlServices.corsError();
        }


    } catch (error) {
        console.error("Websocket connection failed: ", error);
        ProxyUrlServices.corsError();
    }

}


async function getConfig(userId) {
    const configUrl = `https://${serverHost}/get_config/`;
    const userData = { user_id: userId, version: versionClient };
    console.log("user data ", userData)

    const response = await fetch(configUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
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
