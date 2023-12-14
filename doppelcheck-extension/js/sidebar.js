console.log('Hello from the sidebar!');

// Inject sidebar HTML
const sidebar = document.createElement('div');
sidebar.id = 'my-extension-sidebar';
sidebar.innerHTML = `
    <div id="my-extension-sidebar-content">
        <h3>Highlights</h3>
        <ul id="highlight-list"></ul>
    </div>
`;
document.body.appendChild(sidebar);

// Function to add highlights to the sidebar
function addHighlightToSidebar(highlight) {
    console.log('Adding highlight to sidebar.');

    const list = document.getElementById('highlight-list');
    const listItem = document.createElement('li');
    listItem.textContent = highlight.text; // assuming 'highlight' has a 'text' property
    list.appendChild(listItem);
}

// Load highlights from storage and populate sidebar
// This is a placeholder - you'll need to replace it with your actual data retrieval logic
const highlights = [{ text: 'Example Highlight 1' }, { text: 'Example Highlight 2' }];
highlights.forEach(addHighlightToSidebar);

// Create a toggle button
const toggleButton = document.createElement('button');
toggleButton.id = 'my-extension-toggle';
toggleButton.textContent = 'Toggle Sidebar';
document.body.appendChild(toggleButton);

// Toggle sidebar visibility
function toggleSidebar() {
    const sidebar = document.getElementById('my-extension-sidebar');
    sidebar.style.display = sidebar.style.display === 'none' ? 'block' : 'none';
}

// Add click event listener to the toggle button
toggleButton.addEventListener('click', toggleSidebar);

// Initially hide the sidebar
document.getElementById('my-extension-sidebar').style.display = 'none';