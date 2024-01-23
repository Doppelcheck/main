address = "localhost:8000";

function main() {
    let sidebar = document.getElementById("doppelcheck-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("doppelcheck-sidebar-hidden");
        return;
    }

    sidebar = document.createElement("div");
    sidebar.id = "doppelcheck-sidebar";
    sidebar.setAttribute("hx-trigger", "load");
    sidebar.setAttribute("hx-get", `https://${address}/htmx_test`);
    sidebar.setAttribute("hx-swap", "beforeend");
    document.body.appendChild(sidebar);

    const header = document.createElement("h1");
    header.innerText = "Doppelcheck";
    sidebar.appendChild(header);

    const sidebarStyle = document.createElement("link");
    sidebarStyle.rel = "stylesheet";
    sidebarStyle.href = `https://${address}/static/sidebar.css`;
    document.head.appendChild(sidebarStyle);

    const sidebarScript = document.createElement("script");
    sidebarScript.src = `https://${address}/static/sidebar.js`;
    document.head.appendChild(sidebarScript);

    // add htmx
    const htmxScript = document.createElement("script");
    htmxScript.src = `https://${address}/static/htmx.min.js`;
    document.head.appendChild(htmxScript);

}


main();
