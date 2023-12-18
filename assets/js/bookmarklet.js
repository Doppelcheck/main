function main() {
    // base parameters
    // (the string "http://localhost:8000/" is replaced in this script with the actual server URL)
    const server = "http://localhost:8000/";
    const endpoint = `${server}update_body/`;

    // set additional css styles
    const styleElement = document.createElement('style');
    styleElement.innerHTML = "" +
        ".doppelchecked-text {\n" +
        "    position: fixed; /* Fixed position to stay in place during scrolling */\n" +
        "    top: 50%; /* Center vertically */\n" +
        "    left: 50%; /* Center horizontally */\n" +
        "    transform: translate(-50%, -50%); /* Adjust for exact centering */\n" +
        "    color: white; /* Text color */\n" +
        "    font-size: 100px; /* Text size */\n" +
        "    z-index: 10001; /* Ensure it's above the overlay */\n" +
        "}\n" +
        "\n" +
        ".doppelchecked-overlay {\n" +
        "    position: fixed; \n" +
        "    top: 0; \n" +
        "    left: 0; \n" +
        "    width: 100%; \n" +
        "    height: 100%; \n" +
        "    background: rgba(0, 0, 0, 0.5); \n" +
        "    z-index: 10000; \n" +
        "    pointer-events: auto; \n" +
        "}\n";
    document.head.appendChild(styleElement);

    // build payload
    let payload = {
        url: window.location.href,
        html: document.documentElement.outerHTML
    };

    // get selected text
    const sel = document.getSelection();
    if (sel !== null) {
        const selectedText = sel.toString().trim();
        if (0 < selectedText.length) {
            payload.selected_text = selectedText;
        }
    }

    // add overlay
    const overlay = document.createElement('div');
    overlay.addEventListener('click', function(event) {
        event.preventDefault();
        event.stopPropagation();
    }, true);
    overlay.classList.add('doppelchecked-overlay');
    const textContainer = document.createElement('div');
    textContainer.classList.add('doppelchecked-text');
    textContainer.textContent = "Processing..."; // Your text here
    overlay.appendChild(textContainer);
    document.body.appendChild(overlay);

    // send request
    console.log("sending: ", JSON.stringify(payload))
    fetch(`${endpoint}`, {
        method: 'POST', // or 'PUT', depending on your API
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    })

    .then(response => response.json())

    .then(json_data => {
        // replace body
        console.log('Success:', json_data);
        if (json_data && "body" in json_data) {
            console.log("Replacing website body with new body");
            document.body.outerHTML = json_data.body;
        }

    })

    .catch((error) => {
        // revert to original body
        overlay.remove();
        styleElement.remove();

        console.error('Error:', error);
        alert(
            "An error occurred: Maybe the website's security policy is blocking the request. " +
            "Please copy and paste the relevant text or complete URL at http://localhost:8000/."
        );
    });
}

// Call the main function explicitly
main();
