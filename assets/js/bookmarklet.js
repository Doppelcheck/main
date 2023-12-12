const server = "http://localhost:8000/";
const endpoint = `${server}pass_source/`;
let payload = {
    url: window.location.href
};

const sel = document.getSelection();
if (sel !== null) {
    const selectedText = sel.toString().trim();
    if (0 < selectedText.length) {
        payload.text = selectedText;
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
    if (json_data && "redirect_to" in json_data) {
        const targetURL= `${server}${json_data.redirect_to}`;
        console.log("Opening redirect_to " + targetURL + " in new tab");
        window.open(targetURL, '_blank');
    }
})
.catch((error) => {
    console.error('Error:', error);
});
