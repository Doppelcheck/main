address = "localhost:8000";


function checkClaim(id) {
    console.log(`checking claim ${id}`);
}

function extraction(response) {
    console.log("extraction");
    const data = response.data;
    const extractedClaim = data.extractedClaim;
    const done = response.done;

    /*
    const claimDone = data.claimDone;
    append to last claim
    if claimDone and not done:
        create new claim element
    */

    const claimsContainer = document.getElementById("doppelcheck-claims-container");
    const claimCount = claimsContainer.childElementCount;

    const eachClaimContainer = document.createElement("div");
    eachClaimContainer.classList.add("doppelcheck-each-claim-container");
    claimsContainer.appendChild(eachClaimContainer);

    const newClaim = document.createElement("div");
    newClaim.id = `doppelcheck-claim${claimCount}`;
    newClaim.classList.add("doppelcheck-claim");
    newClaim.innerText = extractedClaim;

    eachClaimContainer.appendChild(newClaim);

    const newButton = document.createElement("button");
    newButton.id = `doppelcheck-button${claimCount}`;
    newButton.classList.add("doppelcheck-button");
    newButton.innerText = "Check";
    newButton.onclick = function() {
        checkClaim(claimCount);
    }
    eachClaimContainer.appendChild(newButton);

    if (done) {
        const loading = document.getElementById("doppelcheck-loading");
        loading.remove();
    }

    console.log(data);
}

function retrieval(response) {
    console.log("retrieval");
    console.log(data);
}

function comparison(response) {
    console.log("comparison");
    console.log(data);
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
        console.log(event);
        const response = JSON.parse(event.data);
        switch (response.purpose) {
            case "extract":
                extraction(response);
                break

            case "retrieve":
                retrieval(response);
                break

            case "compare":
                comparison(response);
                break

            default:
                console.log(`unknown purpose: ${response.purpose}`);
        }
    }
}

function main() {
    let sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");
        return;
    }

    const fullHTML = document.documentElement.outerHTML;

    sidebar = document.createElement("div");
    sidebar.id = "doppelcheck-sidebar";
    document.body.appendChild(sidebar);

    const heading = document.createElement("h1");
    heading.id = "doppelcheck-heading";
    heading.innerText = "Doppelcheck";
    heading.onclick = exchange;
    sidebar.appendChild(heading);

    const claimContainer = document.createElement("div");
    claimContainer.id = "doppelcheck-claims-container";
    sidebar.appendChild(claimContainer);

    const loading = document.createElement("div");
    loading.id = "doppelcheck-loading";
    loading.innerText = "Loading...";
    sidebar.appendChild(loading);

    const sidebarStyle = document.createElement("link");
    sidebarStyle.rel = "stylesheet";
    sidebarStyle.href = `https://${address}/static/sidebar.css`;
    document.head.appendChild(sidebarStyle);

    const sidebarScript = document.createElement("script");
    sidebarScript.src = `https://${address}/static/sidebar.js`;
    document.head.appendChild(sidebarScript);

    const htmxScript = document.createElement("script");
    htmxScript.src = `https://${address}/static/htmx.min.js`;
    document.head.appendChild(htmxScript);

    const htmxWsScript = document.createElement("script");
    htmxWsScript.src = `https://${address}/static/htmx-websocket-extension.js`;
    document.head.appendChild(htmxWsScript);

    exchange("extract", fullHTML);
}


main();
