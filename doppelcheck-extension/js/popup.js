document.getElementById("changeColor").addEventListener("click", () => {

    console.log("Hello from the popup!");

    // Send a message to the content script
    browser.tabs.query({active: true, currentWindow: true}, (tabs) => {
        browser.tabs.sendMessage(tabs[0].id, {
            command: "changeColor",
        });
    });
});
