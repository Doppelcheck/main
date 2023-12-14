console.log("Hello from the content script!");

function changeTextColor() {
    console.log("Changing text color!");

    // Example: change the background color of all <p> elements
    let paragraphs = document.getElementsByTagName('p');
    for (let para of paragraphs) {
        para.style.backgroundColor = 'yellow'; // Change as needed
    }
}

// Listen for messages from the popup script
browser.runtime.onMessage.addListener((message) => {
    if (message.command === "changeColor") {
        changeTextColor();
    }
});
