const serverHost = "[localhost:8000]";
const userID = "[unique user identification]";
const versionClient = "[version number]";


const ProxyUrlServices = {
    localBypass(originalUrl) {
        const urlEncoded = encodeURIComponent(originalUrl);
        return `https://${serverHost}/get_content/?url=${urlEncoded}`;
    },

    corsError() {
        const proxyUrl = ProxyUrlServices.localBypass(window.location.href);

        InitializeDoppelcheck.notifyUser(
            `<p>Connection to <a href="${serverHost}">the Doppelcheck server</a> failed. This may be due to ` +
            `restrictive security settings on the current website.</p>${window.location.hostname}<p>Please use ` +
            `Doppelcheck on <a href="${proxyUrl}" target="_blank">an accessible version of this website.</a>`,
            false);
    },

    setupError(error, configUrl) {
        InitializeDoppelcheck.notifyUser(
            `Server error: ${error}. Please install the latest bookmarklet version from ` +
            `<a href="${configUrl}" target="_blank">here,</a> make sure all interfaces are configured, and ` +
            `<a href="${window.location.href}">refresh</a> this page.`);
        }
};

const InitializeDoppelcheck = {
    shadowElement: null,

    getElementById(id) {
        return InitializeDoppelcheck.shadowElement.getElementById(id);
    },

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

    async loadExternalStyles(url, shadowRoot) {
        try {
            const response = await fetch(url);
            const cssText = await response.text();

            const style = document.createElement('style');
            style.textContent = cssText;
            shadowRoot.appendChild(style);

        } catch (error) {
            console.error('Failed to load external styles:', error);
        }
    },

    async createSidebar(container) {
        const sidebar = document.createElement("div");
        InitializeDoppelcheck.shadowElement = sidebar.attachShadow({ mode: 'open' });

        //await InitializeDoppelcheck.loadExternalStyles(`https://${address}/static/pico.css`, InitializeDoppelcheck.shadowElement)

        const shadowContainer = document.createElement("div");
        shadowContainer.id = "doppelcheck-shadow-container";
        InitializeDoppelcheck.shadowElement.appendChild(shadowContainer);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${serverHost}/static/sidebar-content.css`;
        InitializeDoppelcheck.shadowElement.appendChild(sidebarStyle);

        /*
        const picoStyle = document.createElement("link");
        picoStyle.rel = "stylesheet";
        // picoStyle.href = `https://${address}/static/pico.css`;
        picoStyle.href = "https://unpkg.com/mvp.css";
        InitializeDoppelcheck.shadowElement.appendChild(picoStyle);
        */

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
        InitializeDoppelcheck.reduceZIndex(1000);

        const bodyWrapper = document.createElement("div");
        bodyWrapper.id = "doppelcheck-body-wrapper";

        const mainContent = document.createElement("div");
        mainContent.id = "doppelcheck-main-content";
        InitializeDoppelcheck.moveBodyContentToContainer(mainContent);
        bodyWrapper.appendChild(mainContent);

        const sidebar = await InitializeDoppelcheck.createSidebar(bodyWrapper);
        document.body.appendChild(bodyWrapper);
        InitializeDoppelcheck.addNotificationArea(sidebar);

        const heading = document.createElement("h1");
        heading.id = "doppelcheck-heading";
        heading.innerText = `Client v${versionClient}`;
        sidebar.appendChild(heading);

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

        const nameInstance = document.createElement("h2");
        nameInstance.id = "doppelcheck-name-instance";
        nameInstance.innerText = config["name_instance"];
        sidebar.appendChild(nameInstance);

        const subheading = document.createElement("h3");
        subheading.id = "doppelcheck-subheading";
        subheading.innerText = "Claims";
        sidebar.appendChild(subheading);

        const configure = document.createElement("a");
        configure.id = "doppelcheck-config";
        configure.innerText = "Config";
        configure.href = configUrl;
        configure.target = "_blank";
        sidebar.appendChild(configure);

        const claimContainer = document.createElement("div");
        claimContainer.id = "doppelcheck-claims-container";
        sidebar.appendChild(claimContainer);

        const button = document.createElement("button");
        button.id = "doppelcheck-button-start";
        button.innerText = "🤨 Extract Claims";

        button.onclick = async function () {
            button.disabled = true;
            const selection = document.getSelection();
            if (selection === null || 20 >= selection.toString().trim().length) {
                button.innerText = "⏳ Extracting claims from website...";
                const fullHTML = document.documentElement.outerHTML;
                // todo:
                //  1. save new claim count
                //  2. send claim count to extract
                try {
                    exchange("extract", fullHTML);
                } catch (error) {
                    console.log('Websocket connection failed: ' + error);
                    ProxyUrlServices.corsError();
                }
            } else {
                button.innerText = "⏳ Extracting claims from selection...";
                const selectedText = selection.toString();
                exchange("extract_selection", selectedText);

            }
        }
        sidebar.appendChild(button);

        /*
        const userIdField = document.createElement("div");
        userIdField.id = "doppelcheck-user-id";
        userIdField.innerText = userID;
        sidebar.appendChild(userIdField);
         */

        const doppelcheckStyle = document.createElement("link");
        doppelcheckStyle.rel = "stylesheet";
        doppelcheckStyle.href = `https://${serverHost}/static/main-content.css`;
        document.head.appendChild(doppelcheckStyle);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${serverHost}/static/sidebar.css`;
        document.head.appendChild(sidebarStyle);

        // add mark.js
        const markJs = document.createElement("script");
        markJs.src = `https://${serverHost}/static/mark.min.js`;
        markJs.defer = true;
        document.head.appendChild(markJs);

        // addSidebarScopedCss()

    }
}

const ExtractClaims = {
    addClaim(claimId, claimsContainer) {
        const eachClaimContainer = document.createElement("details");
        eachClaimContainer.classList.add("doppelcheck-each-claim-container");
        eachClaimContainer.id = `doppelcheck-each-claim-container${claimId}`;
        eachClaimContainer.setAttribute("onclick", "return false;");
        claimsContainer.appendChild(eachClaimContainer);

        const claim = document.createElement("summary");
        claim.id = `doppelcheck-claim${claimId}`;
        claim.classList.add("doppelcheck-claim");
        claim.classList.add(`doppelcheck-claim-${claimId}`);
        eachClaimContainer.appendChild(claim);

        const getDocumentsButton = document.createElement("button");
        getDocumentsButton.innerText = "🕵 Retrieve Documents";
        getDocumentsButton.id = `doppelcheck-retrieve-button${claimId}`;
        getDocumentsButton.onclick = function () {
            getDocumentsButton.disabled = true;
            claim.textContent = claim.textContent + " 🕵";
            getDocumentsButton.innerText = "⏳ Retrieving...";

            RetrieveDocuments.getDocuments(claimId);
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

    processExtractionMessage(response) {
        console.log("extraction");

        const highlight = response.highlight;
        const claimId = response.claim_id;
        console.log(`claim id: ${claimId}, last message: ${response.last_message}, last segment: ${response.last_segment}`);

        if (highlight) {
            // console.log("highlighting: ", highlight);
            const markInstance = new Mark(document.querySelector("#doppelcheck-main-content"));

            for (const regexPattern of ExtractClaims.segmentWords(highlight, 5)) {
                // console.log("regex pattern: ", regexPattern);
                markInstance.markRegExp(regexPattern, {
                    "acrossElements": true,
                    "className": `doppelcheck-claim-${claimId}`
                });
            }

        } else {
            const claimSegment = response.segment;

            const claimsContainer = InitializeDoppelcheck.getElementById("doppelcheck-claims-container");

            let claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
            if (!claim) {
                claim = ExtractClaims.addClaim(claimId, claimsContainer);
            }
            claim.textContent += claimSegment;

            const lastClaim = response.last_message;
            const lastSegment = response.last_segment;
            if (lastSegment) {
                if (lastClaim) {
                    const button = InitializeDoppelcheck.getElementById("doppelcheck-button-start");
                    button.remove();
                }
                const eachClaimContainer = InitializeDoppelcheck.getElementById(
                    `doppelcheck-each-claim-container${claimId}`
                );
                eachClaimContainer.removeAttribute("onclick");
            }
        }
    }
}

const RetrieveDocuments = {
    addDocument(claimId, documentId, documentsContainer) {
        const documentContainer = document.createElement("li");
        documentContainer.classList.add("doppelcheck-document-container");
        documentContainer.id = `doppelcheck-document${claimId}-${documentId}`;
        documentsContainer.appendChild(documentContainer);
        return documentContainer;
    },

    getDocuments(claimId) {
        console.log(`checking claim ${claimId}`);
        const claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
        claim.onclick = null;
        const claimText = claim.textContent;
        const data = {id: claimId, text: claimText}
        exchange("retrieve", data);
    },

    addDocumentsContainer(claimId) {
        const documentsContainer = document.createElement("ul");
        documentsContainer.id = `doppelcheck-documents-container${claimId}`;
        documentsContainer.classList.add("doppelcheck-documents-container");

        const eachClaimContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-each-claim-container${claimId}`
        );
        eachClaimContainer.prepend(documentsContainer);
        return documentsContainer;
    },

    processRetrievalMessage(response) {
        console.log("retrieval");

        const documentSegment = response.segment;
        const lastMessage = response.last_message;
        const claimId = response.claim_id;
        const documentId = response.document_id;
        const documentUri = response.document_uri;
        const success = response.success;

        // replace button with documents container
        let documentsContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-documents-container${claimId}`
        )
        if (!documentsContainer) {
            documentsContainer = RetrieveDocuments.addDocumentsContainer(claimId);
        }

        const documentContainer = RetrieveDocuments.addDocument(claimId, documentId, documentsContainer);
        const buttonContainer = document.createElement("div");
        buttonContainer.id = `doppelcheck-button-container${claimId}-${documentId}`;

        if (success) {
            const link = document.createElement("a");
            link.id = `doppelcheck-document-link${claimId}-${documentId}`;
            link.href = documentUri;
            link.target = "_blank";
            link.textContent = documentSegment;
            documentContainer.appendChild(link);

            const compareButton = document.createElement("button");
            compareButton.id = `doppelcheck-compare-button${claimId}-${documentId}`;
            compareButton.classList.add("doppelcheck-compare-button");
            buttonContainer.appendChild(compareButton);
            compareButton.textContent = "Compare with claim";
            compareButton.onclick = function () {
                compareButton.disabled = true;
                compareButton.textContent = "🧐 Comparing...";
                CompareDocuments.initiateComparison(claimId, documentId);
            }

        } else {
            const text = document.createElement("span");
            text.classList.add("doppelcheck-document");
            text.textContent = documentSegment;
            buttonContainer.appendChild(text);

            const compareButton = document.createElement("button");
            compareButton.id = `doppelcheck-compare-button${claimId}-${documentId}`;
            compareButton.classList.add("doppelcheck-compare-button");
            documentContainer.appendChild(compareButton);
            compareButton.textContent = "Document content cannot be retrieved";
            compareButton.disabled = true;
        }

        documentContainer.appendChild(buttonContainer);

        if (lastMessage) {
            const retrieveButton = InitializeDoppelcheck.getElementById(`doppelcheck-retrieve-button${claimId}`);
            retrieveButton.remove();

            const claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
            if (!claim.classList.contains("doppelcheck-no-document")) {
                claim.textContent = claim.textContent.replace("🕵", "📑");
            }
        }
    }
}

const CompareDocuments = {
    initiateComparison(claimId, documentId) {
        const claimContainer = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);

        const documentLink = InitializeDoppelcheck.getElementById(`doppelcheck-document-link${claimId}-${documentId}`);
        if (!documentLink) {
            alert(`Document URI not found for claim ${claimId} and document ${documentId}`);
            return;
        }
        const documentUri = documentLink.href;

        const claimText = claimContainer.textContent.replace("📑", "").trim();
        exchange("compare",
            {claim_id: claimId, claim_text: claimText, document_id: documentId, document_uri: documentUri}
        );
    },

    processComparisonMessage(response){
        console.log("comparison");

        const segment = response.segment;
        const lastSegment = response.last_segment;
        const lastMessage = response.last_message;
        const claimId = response.claim_id;
        const documentId = response.document_id;
        const matchValue = response.match_value;

        // ========

        let documentSummary, documentExplanation;

        const documentContainer = InitializeDoppelcheck.getElementById(`doppelcheck-document${claimId}-${documentId}`);
        const buttonContainer = InitializeDoppelcheck.getElementById(`doppelcheck-button-container${claimId}-${documentId}`);
        if (buttonContainer) {
            buttonContainer.remove();

            const documentDetails = document.createElement("details");
            documentDetails.id = `doppelcheck-document-details${claimId}-${documentId}`;
            documentDetails.classList.add("doppelcheck-document-details");
            documentContainer.appendChild(documentDetails);

            documentSummary = document.createElement("summary");
            documentSummary.id = `doppelcheck-document-summary${claimId}-${documentId}`;
            documentSummary.classList.add("doppelcheck-document-summary");
            documentSummary.textContent = "⏳ Comparing...";
            documentDetails.appendChild(documentSummary);

            documentExplanation = document.createElement("div");
            documentExplanation.id = `doppelcheck-document-explanation${claimId}-${documentId}`;
            documentExplanation.classList.add("doppelcheck-document-explanation", "doppelcheck-explanation-container");
            documentDetails.appendChild(documentExplanation);

            if (matchValue >= 2) {
                documentSummary.textContent = "⏳ 🟩 Strong support";
            } else if (matchValue >= 1) {
                documentSummary.textContent = "⏳ 🟨 Some support";
            } else if (matchValue >= 0) {
                documentSummary.textContent = "⏳ ⬜️ No mention";
            } else if (matchValue >= -1) {
                documentSummary.textContent = "⏳ 🟧​ Some contradiction";
            } else {
                documentSummary.textContent = "⏳ 🟥 Strong contradiction";
            }

        } else {
            documentExplanation = InitializeDoppelcheck.getElementById(`doppelcheck-document-explanation${claimId}-${documentId}`);
            documentSummary = InitializeDoppelcheck.getElementById(`doppelcheck-document-summary${claimId}-${documentId}`);
        }
        // ===========

        documentExplanation.textContent += segment;
        if (lastSegment && lastMessage) {
            documentSummary.textContent = documentSummary.textContent.replace("⏳ ", "");
        }
    }
}

function exchange(purpose, data) {
    const ws = new WebSocket(`wss://${serverHost}/talk`);

    const message = {
        purpose: purpose,
        data: data,
        user_id: userID,
        url: window.location.href
    };
    const messageStr = JSON.stringify(message);

    ws.onopen = function(event) {
        console.log(`sending for ${purpose} `, message);
        ws.send(messageStr);
    }

    ws.onmessage = function(event) {
        const response = JSON.parse(event.data);
        switch (response.purpose) {
            case "pong":
                if (purpose === "ping") {
                    console.log("Communication established");
                } else {
                    console.log(`unexpected pong response to: ${purpose}`);
                }
                break;

            case "extract":
                ExtractClaims.processExtractionMessage(response);
                break;

            case "retrieve":
                RetrieveDocuments.processRetrievalMessage(response);
                break;

            case "compare":
                CompareDocuments.processComparisonMessage(response);
                break;

            case "log":
                console.error("logs not implemented");
                break;

            default:
                console.log(`unknown purpose: ${response.purpose}`);
        }
    }

    ws.onerror = function(event) {
        console.log("Error performing WebSocket communication ", event);
        // await ProxyUrlServices.redirect();
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
