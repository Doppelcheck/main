address = "localhost:8000";


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
        alert(`Connection to doppelcheck server ${address} failed. This may be due to restrictive security settings on the current website ${window.location.hostname}.\n\nWe'll open the website on a proxy server\n\n${proxyUrl}\n\nPlease retry doppelcheck there.`);
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
        const scopedCss = cssContent.replace(/(^|\s+|,)([a-zA-Z0-9*[_#:.-]+)/g, '$1#doppelcheck-sidebar $2');

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
        heading.onclick = exchange;
        sidebar.appendChild(heading);

        const config = document.createElement("a");
        config.id = "doppelcheck-config";
        config.innerText = "Config";
        config.href = `https://${address}/config`;
        config.target = "_blank";
        sidebar.appendChild(config);

        const claimContainer = document.createElement("div");
        claimContainer.id = "doppelcheck-claims-container";
        sidebar.appendChild(claimContainer);

        const loading = document.createElement("div");
        loading.id = "doppelcheck-loading-claims";
        loading.innerText = "Loading claims...";
        sidebar.appendChild(loading);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${address}/static/sidebar.css`;
        document.head.appendChild(sidebarStyle);

        // addSidebarScopedCss()

        /*
        const sidebarScript = document.createElement("script");
        sidebarScript.src = `https://${address}/static/sidebar.js`;
        document.head.appendChild(sidebarScript);

        const htmxScript = document.createElement("script");
        htmxScript.src = `https://${address}/static/htmx.min.js`;
        document.head.appendChild(htmxScript);

        const htmxWsScript = document.createElement("script");
        htmxWsScript.src = `https://${address}/static/htmx-websocket-extension.js`;
        document.head.appendChild(htmxWsScript);
        */

    }
}

const ExtractClaims = {
    addClaim(claimId, claimsContainer) {
        const eachClaimContainer = document.createElement("div");
        eachClaimContainer.classList.add("doppelcheck-each-claim-container");
        eachClaimContainer.id = `doppelcheck-each-claim-container${claimId}`;
        claimsContainer.appendChild(eachClaimContainer);

        const claim = document.createElement("div");
        claim.id = `doppelcheck-claim${claimId}`;
        claim.classList.add("doppelcheck-claim");
        eachClaimContainer.appendChild(claim);

        const newButton = document.createElement("button");
        newButton.id = `doppelcheck-button${claimId}`;
        newButton.classList.add("doppelcheck-button");
        newButton.innerText = "Check";
        newButton.disabled = true;
        newButton.onclick = function () {
            RetrieveDocuments.getDocuments(claimId);
        }
        eachClaimContainer.appendChild(newButton);

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
                const loading = document.getElementById("doppelcheck-loading-claims");
                loading.remove();
            } else {
                ExtractClaims.addClaim(claimId, claimsContainer);
            }
            const button = document.getElementById(`doppelcheck-button${claimId - 1}`);
            button.disabled = false;
        }
    }
}

const RetrieveDocuments = {
    addDocument(claimId, documentId, documentsContainer) {
        const documentElement = document.createElement("div");
        documentElement.classList.add("doppelcheck-document");
        documentElement.id = `doppelcheck-document${claimId}-${documentId}`;
        documentsContainer.appendChild(documentElement);
        return documentElement;
    },

    getDocuments(claimId) {
        console.log(`checking claim ${claimId}`);
        const claim = document.getElementById(`doppelcheck-claim${claimId}`);
        const claimText = claim.textContent;
        const data = {id: claimId, text: claimText}
        exchange("retrieve", data);
    },

    replaceButtonWithDocumentsContainer(button, claimId) {
        button.remove();

        const documentsContainer = document.createElement("div");
        documentsContainer.id = `doppelcheck-documents-container${claimId}`;
        documentsContainer.classList.add("doppelcheck-documents-container");

        const eachClaimContainer = document.getElementById(`doppelcheck-each-claim-container${claimId}`);
        eachClaimContainer.appendChild(documentsContainer);

        const loading = document.createElement("div");
        loading.id = `doppelcheck-loading-documents${claimId}`;
        loading.innerText = "Loading documents...";
        eachClaimContainer.appendChild(loading);

        return documentsContainer;
    },

    retrieval(response) {
        console.log("retrieval");

        const documentSegment = response.segment;
        const lastClaim = response.last_message;
        const lastSegment = response.last_segment;
        const claimId = response.claim_id;

        // replace button with documents container
        let documentsContainer;
        const button = document.getElementById(`doppelcheck-button${claimId}`);
        if (button) {
            documentsContainer = RetrieveDocuments.replaceButtonWithDocumentsContainer(button, claimId);

        } else {
            documentsContainer = document.getElementById(`doppelcheck-documents-container${claimId}`);
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
                const loading = document.getElementById(`doppelcheck-loading-documents${claimId}`);
                loading.remove();

            } else {
                _ = RetrieveDocuments.addDocument(claimId, documentCount, documentsContainer);
            }
        }
    }

}

const CompareDocuments = {
    comparison(response){
        console.log("comparison");
        console.log(data);
    }
}

function exchange(purpose, data) {
    try {
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
                case "extract":
                    const sidebar = document.getElementById("doppelcheck-sidebar");
                    if (!sidebar) {
                        InitializeDoppelcheck.addDoppelcheckElements();
                    }
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
            console.log(event);
            ProxyUrlServices.redirect();
        }

    } catch (error) {
        ProxyUrlServices.redirect();
    }

}

function main() {
    const sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");

    } else {
        const fullHTML = document.documentElement.outerHTML;
        exchange("extract", fullHTML);
    }
}


main();
