const endpoint = "http://localhost:8000/api/"

const sel = document.getSelection();
let url = `${endpoint}url?value=${encodeURIComponent(window.location.href)}`;

if (sel !== null) {
    const selectedText = sel.toString().trim();
    if (0 < selectedText.length) {
        url = `${endpoint}selection?value=${encodeURIComponent(selectedText)}`;
    }
}

window.open(url, '_blank');