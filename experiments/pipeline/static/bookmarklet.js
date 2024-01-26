const address = "localhost:8000";

const WebStorageAPIStuff = {
    hasAccess: false,

    updateCookiesOutput() {
      console.log("Reading local storage:", localStorage);
    },

    // This function is called by the refreshCookiesButton
    // It either already has access - in which case it can simply access the cookies
    // Or it doesn't have access because it was waiting for a prompt
    // We could just gate this on `hasAccess`
    async refreshCookies() {
      if (!WebStorageAPIStuff.hasAccess) {
        console.log(
          "Don't have access. Trying again within this click handler, in case it needed a prompt."
        );
        try {
          // This should now work if it was waiting a prompt
          await document.requestStorageAccess();
          WebStorageAPIStuff.hasAccess = true;  // Can assume this was true is above did not reject
          console.log("Have access now thanks to prompt");
        } catch (err) {
          console.log("requestStorageAccess Error:", err);
        }

        WebStorageAPIStuff.hasAccess = await document.hasStorageAccess();
        console.log("Updated hasAccess:", WebStorageAPIStuff.hasAccess);
      }
      WebStorageAPIStuff.updateCookiesOutput();
    },

    async hasCookieAccess() {
      // Check if Storage Access API is supported
      if (!document.requestStorageAccess) {
        // Storage Access API is not supported so best we can do is
        // hope it's an older browser that doesn't block 3P cookies
        console.log("Storage Acccess API not supported. Assume we have access.")
        return true;
      }

      // Check if access has already been granted
      if (await document.hasStorageAccess()) {
        console.log("Cookie access already granted");
        return true;
      }

      // Check the storage-access permission
      // Wrap this in a try/catch for browsers that support the
      // Storage Access API but not this permission check
      // (e.g. Safari and older versions of Firefox)
      try {
        const permission = await navigator.permissions.query({
          name: "storage-access",
        });
        console.log("permissions:", permission);
        // https://developers.google.com/privacy-sandbox/3pcd/related-website-sets-integration?hl=de#implementation_examples
        if (permission.state === "granted") {
          // Can just call requestStorageAccess() without a
          // user interaction and it will resolve automatically.
          try {
            console.log("Cookie access allowed. Calling requestStorageAccess()");
            await document.requestStorageAccess();
            console.log("Cookie access granted");
            return true;
          } catch (error) {
            // This shouldn't really fail if access is granted
            return false;
          }
        } else if (permission.state === "prompt") {
          // Need to call requestStorageAccess() after a user interaction
          // Can't do anything further here, so handle this in the click handler
          console.log("Cookie access requires a prompt");
          return false;
        } else if (permission.state === "denied") {
          // Currently not used. See:
          // https://github.com/privacycg/storage-access/issues/149
          console.log("Cookie access denied");
          return false;
        }
      } catch (error) {
        // storage-access permission not supported. Assume false.
          console.log("storage-access permission not supported. Assume no access.");
        return false;
      }

      // By default return false, though should really be caught by one of above.
      return false;
    },

    // This function runs as page loads to try to give access initially
    // This can make the click handler quicker as it doesn't need to
    // await the access request if it's already happened.
    async handleCookieAccessInit() {
      WebStorageAPIStuff.hasAccess = await WebStorageAPIStuff.hasCookieAccess();
      WebStorageAPIStuff.updateCookiesOutput();
    }
}

const IFrameCommunication = {
                // Create an IFrame and append it to the body
    initIframe() {
        const iframe = document.createElement('iframe');
        iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-storage-access-by-user-activation')
        iframe.style.display = 'none';
        iframe.id = 'doppelcheck-iframe';
        iframe.src = `https://${address}/helper`; // URL of your helper page
        document.body.appendChild(iframe);

        window.addEventListener('message', function (event) {
            if (event.origin !== `https://${address}`) {
                // Only accept messages from the IFrame's origin
                console.log(`Origin ${event.origin} not allowed`);
                return;
            }

            const data = event.data;
            if (data.type === 'loaded') {
                console.log("BOOKMARKLET: Data received from helper ", data);

            } else if (data.type === 'saved') {
                console.log("BOOKMARKLET: Data successfully saved in helper ", data);
            }
        });
    },
    async setHelper(key, value) {
        await WebStorageAPIStuff.refreshCookies();
        await WebStorageAPIStuff.handleCookieAccessInit();

        const iframe = document.getElementById('doppelcheck-iframe');
        const message = {type: 'save', key: key, value: value };
        console.log("BOOKMARKLET: Sending data to helper", message);
        iframe.contentWindow.postMessage(
            message,
            `https://${address}`
        );
    },
    async getHelper(key) {
        await WebStorageAPIStuff.refreshCookies();
        await WebStorageAPIStuff.handleCookieAccessInit();

        const iframe = document.getElementById('doppelcheck-iframe');
        const message = {type: 'load', key: key };
        console.log("BOOKMARKLET: Requesting data from helper ", message);
        iframe.contentWindow.postMessage(
            message,
            `https://${address}`
        );
    }

}

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

    async addDoppelcheckElements() {
        InitializeDoppelcheck.reduceZIndex(1000);

        IFrameCommunication.initIframe();

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
        config.href = `https://${address}/config`;
        config.target = "_blank";
        sidebar.appendChild(config);

        const button = document.createElement("button");
        button.id = "doppelcheck-button-start";
        button.innerText = "Start Extraction";
        button.onclick = function () {
            button.remove();
            subheading.textContent += " ⏳";
            const fullHTML = document.documentElement.outerHTML;
            exchange("extract", fullHTML);
        }
        sidebar.appendChild(button);

        const claimContainer = document.createElement("div");
        claimContainer.id = "doppelcheck-claims-container";
        sidebar.appendChild(claimContainer);

        const sidebarStyle = document.createElement("link");
        sidebarStyle.rel = "stylesheet";
        sidebarStyle.href = `https://${address}/static/sidebar.css`;
        document.head.appendChild(sidebarStyle);

        const testButton = document.createElement("button");
        testButton.id = "doppelcheck-test-button";
        testButton.innerText = "Test";
        testButton.onclick = function () {
            IFrameCommunication.getHelper("testkey");
        }
        sidebar.appendChild(testButton);

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

function main() {
    const sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");

    } else {
        try {
            exchange("ping", null);

        } catch (error) {
            ProxyUrlServices.redirect();
            return;
        }

        InitializeDoppelcheck.addDoppelcheckElements();
    }
}


main();
