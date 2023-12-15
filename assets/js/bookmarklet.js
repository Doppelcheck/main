function main() {
    // the string "http://localhost:8000/" is replaced in this script with the actual server URL
    const server = "http://localhost:8000/";
    const endpoint = `${server}update_body/`;
    let payload = {
        url: window.location.href
    };

    const body = document.body;
    const sel = document.getSelection();
    if (sel !== null) {
        const selectedText = sel.toString().trim();
        if (0 < selectedText.length) {
            payload.text = selectedText;
            payload.body = body.innerHTML;
        }
    }

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
        console.log('Success:', json_data);
        if (json_data && "new_body" in json_data) {
            console.log("Replacing website body with new body");
            body.innerHTML = json_data.new_body;
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert(
            "An error occurred: The website's security policy is blocking the request. " +
            "Please copy and paste the relevant text or complete URL at http://localhost:8000/."
        );
    });
}

// Call the main function explicitly
main();
