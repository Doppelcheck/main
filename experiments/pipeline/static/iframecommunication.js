const address = window.location.host;

const IFrameCommunication = {
                // Create an IFrame and append it to the body
    initIframe() {

        const iframe = document.createElement('iframe');
        iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-storage-access-by-user-activation')
        iframe.style.display = 'none';
        iframe.id = 'doppelcheck-iframe';
        iframe.src = `https://${address}/helper`; // URL of your helper page
        document.body.appendChild(iframe);

        window.addEventListener('message', function (event) {
            if (event.origin !== `https://${address}`) {
                // Only accept messages from the IFrame's origin
                console.log(`Origin ${event.origin} not allowed`);
                return;
            }

            const data = event.data;

            if (data.type === 'settings') {
                // Handle the settings
                console.log("CONFIG: Settings received from helper", data);
                // update elements here

            } else if (data.type === 'saved') {
                console.log("CONFIG: Settings successfully saved in helper", data);
            }
        });

    },

    sendSettings(message) {
        const iframe = document.getElementById('doppelcheck-iframe');
        console.log("CONFIG: Sending settings to iframe", message);
        iframe.contentWindow.postMessage(
            {type: 'save', settings: message },
            `https://${address}`
        );
    },

    getSettings() {
        const iframe = document.getElementById('doppelcheck-iframe');
        console.log("CONFIG: Requesting settings from iframe");
        iframe.contentWindow.postMessage(
            {type: 'get'},
            `https://${address}`
        );
    }
}

IFrameCommunication.initIframe();