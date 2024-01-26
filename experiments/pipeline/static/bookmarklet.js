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

    addSidebarScopedCss() {
        const cssContent = InitializeDoppelcheck.getCSSContent(`https://${address}/static/pico.min.css`);
        const scopedCss = cssContent.replace(
            /(^|\s+|,)([a-zA-Z0-9*[_#:.-]+)/g, '$1#doppelcheck-sidebar $2'
        );

        const style = document.createElement('style');
        style.appendChild(document.createTextNode(scopedCss));
        document.head.appendChild(style);
    },

    createSidebar(container) {
        const sidebar = document.createElement("div");
        sidebar.id = "doppelcheck-sidebar";
        container.appendChild(sidebar);
        return sidebar;
    },

    moveBodyContentToContainer(container) {
        const body = document.body;
        while (body.firstChild) {
            container.appendChild(body.firstChild);
        }
        body.appendChild(container);
    },

    getCSSContent(url) {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', url, false);
        xhr.send();
        return xhr.responseText;
    },

    addDoppelcheckElements() {
        InitializeDoppelcheck.reduceZIndex(1000);

        const bodyWrapper = document.createElement("div");
        bodyWrapper.id = "doppelcheck-body-wrapper";

        const mainContent = document.createElement("div");
        mainContent.id = "doppelcheck-main-content";
        InitializeDoppelcheck.moveBodyContentToContainer(mainContent);
        bodyWrapper.appendChild(mainContent);

        const sidebar = InitializeDoppelcheck.createSidebar(bodyWrapper);

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
            ).catch(
                ProxyUrlServices.redirect
            )
        }
        sidebar.appendChild(button);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${address}/static/sidebar.css`;
        document.head.appendChild(sidebarStyle);

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
        eachClaimContainer.appendChild(claim);

        return claim;
    },

    extraction(response) {
        console.log("extraction");

        const claimSegment = response.segment;
        const lastClaim = response.last_message;
        const lastSegment = response.last_segment;

        const claimsContainer = document.getElementById("doppelcheck-claims-container");
        let claimId = claimsContainer.childElementCount;

        let claim;
        if (claimId < 1) {
            claim = ExtractClaims.addClaim(0, claimsContainer);
            claimId += 1;
        } else {
            const eachClaimContainer = claimsContainer.lastChild;
            claim = eachClaimContainer.firstChild;
        }
        claim.textContent += claimSegment;

        if (lastSegment) {
            if (lastClaim) {
                const subheading = document.getElementById("doppelcheck-subheading");
                subheading.innerText = subheading.innerText.replace("⏳", "✅");
            } else {
                ExtractClaims.addClaim(claimId, claimsContainer);
            }
            const eachClaimContainer = document.getElementById(
                `doppelcheck-each-claim-container${claimId - 1}`
            );
            eachClaimContainer.removeAttribute("onclick");
            const claim = document.getElementById(`doppelcheck-claim${claimId - 1}`);
            claim.onclick = function () {
                RetrieveDocuments.getDocuments(claimId - 1);
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
        const claim = document.getElementById(`doppelcheck-claim${claimId}`);
        claim.onclick = null;
        const claimText = claim.textContent;
        const data = {id: claimId, text: claimText}
        exchange("retrieve", data);
    },

    addDocumentsContainer(claimId) {
        const documentsContainer = document.createElement("ul");
        documentsContainer.id = `doppelcheck-documents-container${claimId}`;
        documentsContainer.classList.add("doppelcheck-documents-container");

        const eachClaimContainer = document.getElementById(
            `doppelcheck-each-claim-container${claimId}`
        );
        eachClaimContainer.appendChild(documentsContainer);

        const claim = document.getElementById(`doppelcheck-claim${claimId}`);
        claim.textContent += " ⏳";

        return documentsContainer;
    },

    retrieval(response) {
        console.log("retrieval");

        const documentSegment = response.segment;
        const lastClaim = response.last_message;
        const lastSegment = response.last_segment;
        const claimId = response.claim_id;

        // replace button with documents container
        let documentsContainer = document.getElementById(
            `doppelcheck-documents-container${claimId}`
        )
        if (!documentsContainer) {
            documentsContainer = RetrieveDocuments.addDocumentsContainer(claimId);
        }

        const documentCount = documentsContainer.childElementCount;

        let documentElement;
        if (documentCount < 1) {
            documentElement = RetrieveDocuments.addDocument(claimId, 0, documentsContainer);
        } else {
            documentElement = documentsContainer.lastChild;
        }

        documentElement.textContent += documentSegment;

        if (lastSegment) {
            if (lastClaim) {
                const claim = document.getElementById(`doppelcheck-claim${claimId}`);
                claim.textContent = claim.textContent.replace("⏳", "✅");

            } else {
                _ = RetrieveDocuments.addDocument(claimId, documentCount, documentsContainer);
            }

            const documentElement = document.getElementById(
                `doppelcheck-document${claimId}-${documentCount - 1}`
            );
            documentElement.onclick = function () {
                CompareDocuments.action(documentElement.textContent, claimId, documentCount - 1);
            }
            documentElement.textContent += " 🧐";
            documentElement.classList.add("doppelcheck-document-clickable");
        }
    }

}

const CompareDocuments = {
    action(documentText, claimId, documentId) {
        alert(`comparison of claim ${claimId} with document ${documentId}`);
        const documentElement = document.getElementById(
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
            InitializeDoppelcheck.addDoppelcheckElements();

        } catch (error) {
            ProxyUrlServices.redirect();
        }
    }
}


main().then(r => console.log("done"));
