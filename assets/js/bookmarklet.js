const endpoint = "http://localhost:8000/pass_source/";
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

console.log(JSON.stringify(payload))

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
        console.log("Opening redirect_to");
        window.open(json_data.redirect_to, '_blank');
    }
})
.catch((error) => {
    console.error('Error:', error);
});
