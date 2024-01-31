const address = "localhost:8000";
const userID = "[unique user identification]";


const ProxyUrlServices = {
    get12ftProxyUrl(originalUrl) {
        return `https://12ft.io/${originalUrl}`;
    },

    getOutlineTTSProxyUrl(originalUrl) {
        const uri = new URL(originalUrl);
        const protocol = uri.protocol.slice(0, -1);
        originalUrl = originalUrl.replace(/(http(s?)):\/\//i, '');
        return `https://outlinetts.com/article/${protocol}/${originalUrl}`;
    },

    getPrintFriendlyProxyUrl(originalUrl) {
        return `https://www.printfriendly.com/print/?source=homepage&url=${encodeURIComponent(originalUrl)}`;
    },

    async getDarkreadProxyUrl(originalUrl) {
        const proxy = 'https://outliner-proxy-darkread.rodrigo-828.workers.dev/cors-proxy';
        const proxyUrl = `${proxy}/${originalUrl}`;

        const response = await fetch(proxyUrl).then(res => res.json());
        return `https://www.darkread.io/${response.uid}`;
    },

    redirect() {
        const proxyUrl = ProxyUrlServices.getPrintFriendlyProxyUrl(window.location.href);
        alert(
            `Connection to doppelcheck server ${address} failed. This may be due to restrictive security settings ` +
            `on the current website ${window.location.hostname}.\n\nWe'll try open the website on a proxy server\n\n` +
            `${proxyUrl}\n\nPlease allow this one popup and retry doppelcheck there.`);
        window.open(proxyUrl);
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
        shadowContainer.setAttribute("data-theme", "light")
        InitializeDoppelcheck.shadowElement.appendChild(shadowContainer);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${address}/static/sidebar-content.css`;
        InitializeDoppelcheck.shadowElement.appendChild(sidebarStyle);

        const picoStyle = document.createElement("link");
        picoStyle.rel = "stylesheet";
        picoStyle.href = `https://${address}/static/pico.css`;
        InitializeDoppelcheck.shadowElement.appendChild(picoStyle);

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

        const heading = document.createElement("h1");
        heading.id = "doppelcheck-heading";
        heading.innerText = "Doppelcheck";
        sidebar.appendChild(heading);

        const subheading = document.createElement("h2");
        subheading.id = "doppelcheck-subheading";
        subheading.innerText = "Claims";
        sidebar.appendChild(subheading);

        const config = document.createElement("a");
        config.id = "doppelcheck-config";
        config.innerText = "Config";
        config.href = `https://${address}/config/${userID}`;
        config.target = "_blank";
        sidebar.appendChild(config);

        const claimContainer = document.createElement("div");
        claimContainer.id = "doppelcheck-claims-container";
        sidebar.appendChild(claimContainer);

        const userIdField = document.createElement("div");
        userIdField.id = "doppelcheck-user-id";
        userIdField.innerText = userID;
        sidebar.appendChild(userIdField);

        const button = document.createElement("button");
        button.id = "doppelcheck-button-start";
        button.innerText = "Start Extraction";

        button.onclick = function () {
            button.remove();
            const configPromise = getConfig(userID)
            configPromise.then(function (config) {
                console.log("configuration ", config)
                subheading.textContent += " ⏳";
                const fullHTML = document.documentElement.outerHTML;
                exchange("extract", fullHTML);
            }
            ).catch(function (error) {
                console.error('There was a problem retrieving the config:', error);
                ProxyUrlServices.redirect();
            })
        }
        sidebar.appendChild(button);

        const doppelcheckStyle = document.createElement("link");
        doppelcheckStyle.rel = "stylesheet";
        doppelcheckStyle.href = `https://${address}/static/main-content.css`;
        document.head.appendChild(doppelcheckStyle);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${address}/static/sidebar.css`;
        document.head.appendChild(sidebarStyle);

        // add mark.js
        const markJs = document.createElement("script");
        markJs.src = `https://${address}/static/mark.min.js`;
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

    extraction(response) {
        console.log("extraction");

        const highlight = response.highlight;
        const claimId = response.claim_id;

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
                    const subheading = InitializeDoppelcheck.getElementById("doppelcheck-subheading");
                    subheading.innerText = subheading.innerText.replace("⏳", "✅");
                }
                const eachClaimContainer = InitializeDoppelcheck.getElementById(
                    `doppelcheck-each-claim-container${claimId}`
                );
                eachClaimContainer.removeAttribute("onclick");
                const claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
                claim.onclick = function () {
                    RetrieveDocuments.getDocuments(claimId);
                }
            }
        }
    }
}

const RetrieveDocuments = {
    addDocument(claimId, documentId, documentsContainer) {
        const documentElement = document.createElement("li");
        documentElement.classList.add("doppelcheck-document");
        documentElement.id = `doppelcheck-document${claimId}-${documentId}`;
        documentsContainer.appendChild(documentElement);
        return documentElement;
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
        eachClaimContainer.appendChild(documentsContainer);

        const claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
        claim.textContent += " ⏳";

        return documentsContainer;
    },

    retrieval(response) {
        console.log("retrieval");

        const documentSegment = response.segment;
        const lastMessage = response.last_message;
        const claimId = response.claim_id;
        const documentId = response.document_id;
        const documentUri = response.document_uri;

        // replace button with documents container
        let documentsContainer = InitializeDoppelcheck.getElementById(
            `doppelcheck-documents-container${claimId}`
        )
        if (!documentsContainer) {
            documentsContainer = RetrieveDocuments.addDocumentsContainer(claimId);
        }

        const documentElement = RetrieveDocuments.addDocument(claimId, documentId, documentsContainer);
        documentElement.textContent += documentUri + " 🧐";

        if (!documentSegment) {
            documentElement.classList.add("doppelcheck-no-document");
        }

        if (lastMessage) {
            const claim = InitializeDoppelcheck.getElementById(`doppelcheck-claim${claimId}`);
            if (!claim.classList.contains("doppelcheck-no-document")) {
                claim.textContent = claim.textContent.replace("⏳", "✅");
                documentElement.onclick = function () {
                    CompareDocuments.action(documentElement.textContent, claimId, documentId);
                }
                documentElement.classList.add("doppelcheck-document-clickable");
            }
        }

        if (documentId >= 1) {
            const lastDocumentElement = InitializeDoppelcheck.getElementById(
                `doppelcheck-document${claimId}-${documentId - 1}`
            );
            lastDocumentElement.onclick = function () {
                CompareDocuments.action(lastDocumentElement.textContent, claimId, documentId - 1);
            }
            lastDocumentElement.classList.add("doppelcheck-document-clickable");
        }
    }
}

const CompareDocuments = {
    action(documentText, claimId, documentId) {
        alert(`comparison of claim ${claimId} with document ${documentId}`);
        const documentElement = InitializeDoppelcheck.getElementById(
            `doppelcheck-document${claimId}-${documentId}`
        );
        documentElement.textContent = documentElement.textContent.replace("🧐", "⏳");
        documentElement.onclick = null;
        documentElement.classList.remove("doppelcheck-document-clickable");
        // 🟢​ 🟡​ 🟠​ 🔴 🚨
    },

    comparison(response){
        console.log("comparison");
        console.log(data);
    }
}

function exchange(purpose, data) {
    const ws = new WebSocket(`wss://${address}/talk`);

    const message = {
        purpose: purpose,
        data: data
    };
    const messageStr = JSON.stringify(message);

    ws.onopen = function(event) {
        console.log(`sending for ${purpose}`);
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
                ExtractClaims.extraction(response);
                break;

            case "retrieve":
                RetrieveDocuments.retrieval(response);
                break;

            case "compare":
                CompareDocuments.comparison(response);
                break;

            default:
                console.log(`unknown purpose: ${response.purpose}`);
        }
    }

    ws.onerror = function(event) {
        console.log("error");
        console.log(event);
    }
}


async function getConfig(userId) {
    const configUrl = `https://${address}/get_config/`;
    const userData = { user_id: userId };

    try {
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

    } catch (error) {
        console.error('There was a problem retrieving the config:', error);
    }
}

async function main() {
    const sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");

    } else {
        try {
            exchange("ping", null);
            await InitializeDoppelcheck.addDoppelcheckElements();

        } catch (error) {
            console.error('There was a problem connecting to the server:', error);
            ProxyUrlServices.redirect();
        }
    }
    // todo:
    //  monocle when clickable
    //  replace checkmark with "done" emoji
}


main().then(r => console.log("done"));
