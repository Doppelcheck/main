address = "localhost:8000";

function sendMessage(id) {
    const button = document.getElementById("sendButton" + id);
    button.disabled = true;

    const ws = new WebSocket(`wss://${address}/ws`);

    ws.onopen = function(event) {
        const input = document.getElementById("messageInput" + id);
        const message = { id: id, data: input.value };
        const jsonStr = JSON.stringify(message);
        ws.send(jsonStr);
        input.value = '';
    };

    ws.onmessage = function(event) {
        const response = JSON.parse(event.data);
        const messages = document.getElementById('messages' + response.id);
        const choice = response.data;
        console.log(choice);
        const finish_reason = choice.finish_reason;
        if (finish_reason === "stop") {
            messages.innerText += "\n";
            button.disabled = false;
            ws.close()

        } else {
            const delta = choice.delta;
            const content = delta.content;
            messages.innerText += content;
        }
    };

}