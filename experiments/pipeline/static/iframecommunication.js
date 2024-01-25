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
            if (data.type === 'loaded') {
                console.log("CONFIG: Settings received from helper ", data);

            } else if (data.type === 'saved') {
                console.log("CONFIG: Settings successfully saved in helper ", data);
            }
        });
    },
    setHelper(key, value) {
        const iframe = document.getElementById('doppelcheck-iframe');
        const message = {type: 'save', key: key, value: value };
        console.log("CONFIG: Sending settings to iframe", message);
        iframe.contentWindow.postMessage(
            message,
            `https://${address}`
        );
    },
    getHelper(key) {
        const iframe = document.getElementById('doppelcheck-iframe');
        const message = {type: 'load', key: key };
        console.log("CONFIG: Requesting settings from iframe ", message);
        iframe.contentWindow.postMessage(
            message,
            `https://${address}`
        );
    }
}

IFrameCommunication.initIframe();