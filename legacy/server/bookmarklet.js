/**
 * Web Content Analysis Bookmarklet
 *
 * This bookmarklet adds a sidebar to web pages to analyze content
 * with LLM assistance for extracting, retrieving, and comparing information.
 */

(function() {
    // Configuration
    const SERVER_BASE_URL = '__SERVER_BASE_URL__'; // Will be replaced by the server
    const SIDEBAR_WIDTH = '450px';
    const HIGHLIGHT_COLOR = 'rgba(255, 255, 0, 0.3)';
    const SIDEBAR_Z_INDEX = 2147483647; // Maximum z-index value
    const MINI_INDICATOR_WIDTH = '30px';
    const SAME_DOMAIN_BACKGROUND = '#ffebee'; // Light red background for same domain evidence


    // Global state
    let relevantChunks = [];
    let highlightedElements = [];
    let originalBodyStyles = {}; // Store original body margin-right
    let originalElementStyles = []; // Store original fixed element styles
    let isSidebarVisible = true;
    let isProcessingInitial = false; // Flag for initial content extraction
    let activeAsyncTaskCount = 0; // Count active search/compare/query tasks for indicator
    let currentScrollPosition = 0;
    let lastUsedQuery = {}; // Store the last used query for each chunk

    /**
     * Main initialization function
     */
    function init() {
        // Check if the bookmarklet is already loaded
        const existingSidebar = document.getElementById('content-analysis-sidebar');
        const miniIndicator = document.getElementById('content-analysis-mini-indicator');

        if (existingSidebar || miniIndicator) {
            toggleSidebarVisibility();
            return;
        }

        currentScrollPosition = window.scrollY;
        storeOriginalStyles();
        createSidebar(); // Includes URL section

        // Start initial processing
        isProcessingInitial = true;
        activeAsyncTaskCount++; // Increment for initial extraction
        updateMiniIndicatorState();

        extractContent().then(displayResults).catch(error => {
            // Catch errors during initial extraction/display if not handled earlier
            console.error("Error during initial content processing:", error);
            showError(`Initial analysis failed: ${error.message || 'Unknown error'}`);
        }).finally(() => {
            isProcessingInitial = false;
            activeAsyncTaskCount--; // Decrement for initial extraction
            updateMiniIndicatorState();
            // Restore scroll position
            if (document.getElementById('content-analysis-sidebar')) {
                window.scrollTo(0, currentScrollPosition);
            }
        });

        document.addEventListener('selectionchange', handleSelectionChange);
        window.addEventListener('resize', debouncedAdjustStyles); // Add resize listener here
    }

    // --- Task Counter Functions ---
    function startAsyncTask() {
        activeAsyncTaskCount++;
        updateMiniIndicatorState();
    }

    function endAsyncTask() {
        activeAsyncTaskCount = Math.max(0, activeAsyncTaskCount - 1); // Prevent going below 0
        updateMiniIndicatorState();
    }
    // -----------------------------


    /**
     * Generate and store the search query for a chunk AND update the UI if possible.
     * Includes re-fetching the element before final update for robustness.
     * Makes the query display editable upon successful generation.
     */
    async function generateAndStoreQuery(chunk) {
        const queryDisplayId = `query-display-${chunk.id}`;

        // Prevent duplicate generation if already stored or actively generating
        if (lastUsedQuery[chunk.id] && lastUsedQuery[chunk.id] !== 'Generating...') {
             const currentElement = document.getElementById(queryDisplayId);
             if (currentElement) {
                 const queryState = lastUsedQuery[chunk.id];
                 // Ensure it's an editable input reflecting the state
                 if (currentElement.tagName !== 'INPUT' || currentElement.value !== (queryState.startsWith('Error:') ? '' : queryState)) {
                      const queryInput = createEditableQueryInput(chunk.id, queryState);
                      currentElement.parentNode?.replaceChild(queryInput, currentElement);
                 }
             }
            return; // Don't regenerate
        }
        if (lastUsedQuery[chunk.id] === 'Generating...') {
             return;
        }

        // Mark as generating and update UI
        lastUsedQuery[chunk.id] = 'Generating...';
        const placeholderElement = document.getElementById(queryDisplayId);
        if (placeholderElement && placeholderElement.tagName !== 'INPUT') {
            placeholderElement.textContent = '[Generating query...]';
            placeholderElement.style.fontStyle = 'italic';
            placeholderElement.style.color = '#666';
        } else if (!placeholderElement) {
            console.warn(`generateAndStoreQuery: Placeholder ${queryDisplayId} not found at 'Generating...' stage.`);
            // Attempt to find header and insert if placeholder truly missing
            const header = document.getElementById(chunk.id)?.querySelector('.chunk-header');
            const controls = header?.querySelector('.controlsDiv');
            if(header && controls) {
                const generatingDiv = document.createElement('div');
                generatingDiv.id = queryDisplayId;
                generatingDiv.textContent = '[Generating query...]';
                generatingDiv.style.cssText = `font-size: 11px; color: #666; font-style: italic; margin-right: 10px; flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 3px 0; min-width: 50px;`;
                header.insertBefore(generatingDiv, controls);
            }
        }

        startAsyncTask(); // Indicate query generation started

        try {
            const context = {
                url: window.location.href, title: document.title, author: getAuthor(), date: getPublishedDate()
             };
            const queryResponse = await fetch(`${SERVER_BASE_URL}/api/retrieve/query`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chunk_id: chunk.id, chunk_content: chunk.content, context: context })
            });

            let finalQueryState = '';
            if (!queryResponse.ok) {
                const errorText = await queryResponse.text();
                console.error(`Failed query gen chunk ${chunk.id}: ${queryResponse.status}. ${errorText}`);
                finalQueryState = `Error: Query generation failed (${queryResponse.status})`;
            } else {
                 const query = await queryResponse.text();
                 let cleanQuery = query.replace(/^["'](.*?)["']$/, '$1').trim();
                 finalQueryState = cleanQuery || 'Error: Generated query was empty.';
            }

            // Store result and update UI
            lastUsedQuery[chunk.id] = finalQueryState;
            const finalElement = document.getElementById(queryDisplayId);
            if (finalElement) {
                 const queryInput = createEditableQueryInput(chunk.id, finalQueryState);
                 finalElement.parentNode?.replaceChild(queryInput, finalElement);
            } else {
                 console.warn(`generateAndStoreQuery: Placeholder ${queryDisplayId} NOT FOUND for final UI update.`);
            }

        } catch (error) {
             console.error(`Network error during query generation for chunk ${chunk.id}:`, error);
             const errorMsg = 'Error: Network issue during query generation.';
             lastUsedQuery[chunk.id] = errorMsg;

             const errorElement = document.getElementById(queryDisplayId);
             if (errorElement) {
                  const queryInput = createEditableQueryInput(chunk.id, errorMsg);
                  errorElement.parentNode?.replaceChild(queryInput, errorElement);
             } else {
                  console.warn(`generateAndStoreQuery: Placeholder ${queryDisplayId} NOT FOUND for CATCH ERROR UI update.`);
             }
        } finally {
            endAsyncTask(); // Indicate query generation finished
        }
    }

    /**
     * Helper function to create the editable input element for the query.
     */
    function createEditableQueryInput(chunkId, queryValue) {
        const queryInput = document.createElement('input');
        queryInput.type = 'text';
        queryInput.id = `query-display-${chunkId}`; // Use the standard ID
        const isError = queryValue.startsWith('Error:');
        queryInput.value = isError ? '' : queryValue; // Don't prefill input with error message text
        queryInput.placeholder = isError ? '[Query generation failed]' : 'Enter search query';
        queryInput.title = `Editable query. ${isError ? queryValue : 'Press Enter or click header outside input to finalize search.'}`;
        queryInput.style.cssText = `
            font-size: 11px; color: #333; font-style: normal; margin-right: 10px;
            flex-grow: 1; border: 1px solid ${isError ? 'red' : '#aaa'}; padding: 2px 4px; border-radius: 3px;
            background-color: #fff; font-family: inherit; line-height: normal; height: auto;
            min-width: 50px; /* Ensure it doesn't collapse too small */
        `;

        queryInput.addEventListener('input', (e) => {
            lastUsedQuery[chunkId] = e.target.value;
            queryInput.style.borderColor = '#aaa'; // Reset border on typing
        });
         queryInput.addEventListener('keypress', (e) => {
             if (e.key === 'Enter') {
                 e.preventDefault();
                 lastUsedQuery[chunkId] = e.target.value; // Store final value
                 document.getElementById(chunkId)?.querySelector('.chunk-header')?.click(); // Simulate header click
             }
         });
        queryInput.addEventListener('click', (e) => e.stopPropagation());

        return queryInput;
    }

    /**
    * Helper function to create the non-editable div element for the query display.
    */
    function createNonEditableQueryDiv(chunkId, queryValue) {
        const queryDiv = document.createElement('div');
        queryDiv.id = `query-display-${chunkId}`;
        queryDiv.style.cssText = `
            font-size: 11px; color: #333; font-style: normal; margin-right: 10px;
            flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            padding: 3px 0; min-width: 50px;
        `;
        let displayQuery = '[No query entered]';
        let titleQuery = 'Click "Reset" to edit query';
        let isError = false;

        if (queryValue) {
            if (queryValue.startsWith('Error:')) {
                displayQuery = '[Query generation failed]'; titleQuery = queryValue; isError = true;
            } else {
                 displayQuery = `Query: "${queryValue}"`; titleQuery = `Searched query: "${queryValue}". Click "Reset" to edit.`;
            }
        }
        queryDiv.textContent = displayQuery;
        queryDiv.title = titleQuery;
        if (!queryValue || isError) { queryDiv.style.fontStyle = 'italic'; queryDiv.style.color = isError ? 'red' : '#888'; }
        if (isError) { queryDiv.style.fontStyle = 'normal'; }

        return queryDiv;
    }

    /**
     * Handle selection change to enable/disable the summarize selection button
     */
    function handleSelectionChange() {
        const summarizeSelectionButton = document.getElementById('summarize-selection-button');
        if (summarizeSelectionButton) {
            const selection = window.getSelection();
            summarizeSelectionButton.disabled = !(selection && selection.toString().trim() !== '');
        }
    }

    /**
    * Store original styles for later restoration
    */
    function storeOriginalStyles() {
        originalBodyStyles = { marginRight: document.body.style.marginRight || '' };
        const fixedElements = document.querySelectorAll('body *');
        originalElementStyles = [];
        fixedElements.forEach(elem => {
            // Ensure element is not part of the sidebar UI itself
            if (elem.id === 'content-analysis-sidebar' || elem.id === 'content-analysis-mini-indicator' || elem.closest('#content-analysis-sidebar')) return;

            const computedStyle = window.getComputedStyle(elem);
            // Check if position is fixed and element is still in the DOM
            if (computedStyle.position === 'fixed' && document.body.contains(elem)) {
                originalElementStyles.push({
                    element: elem, right: computedStyle.right, marginRight: computedStyle.marginRight
                });
            }
        });
    }

    /**
     * Restore original styles
     */
    function restoreOriginalStyles() {
        document.body.style.marginRight = originalBodyStyles.marginRight;
        originalElementStyles.forEach(item => {
            // Check if element still exists before trying to restore styles
            if (item.element && document.body.contains(item.element)) {
                 // Restore computed styles - use empty string for 'auto'
                 item.element.style.right = item.right === 'auto' ? '' : item.right;
                 item.element.style.marginRight = item.marginRight;
            }
        });
    }

    /**
     * Toggle sidebar visibility
     */
    function toggleSidebarVisibility() {
        const sidebar = document.getElementById('content-analysis-sidebar');
        let miniIndicator = document.getElementById('content-analysis-mini-indicator');

        if (sidebar) {
            if (isSidebarVisible) { // Hiding
                sidebar.style.display = 'none';
                isSidebarVisible = false;
                currentScrollPosition = window.scrollY;
                restoreOriginalStyles();
                if (!miniIndicator) createMiniIndicator(); // Creates and updates state/text
                else miniIndicator.style.display = 'flex'; updateMiniIndicatorState(); // Update existing
                window.scrollTo(0, currentScrollPosition);
            } else { // Showing
                sidebar.style.display = 'flex';
                isSidebarVisible = true;
                currentScrollPosition = window.scrollY;
                storeOriginalStyles(); // Store before adjusting
                adjustPageForSidebar();
                if (miniIndicator) miniIndicator.style.display = 'none';
                updateMiniIndicatorState(); // Update text (will hide indicator)
                window.scrollTo(0, currentScrollPosition);
            }
        } else if (miniIndicator) { // Only indicator exists, create sidebar
            currentScrollPosition = window.scrollY;
            storeOriginalStyles();
            createSidebar(); // Creates sidebar, adjusts page, sets state
            miniIndicator.style.display = 'none';
            updateMiniIndicatorState();
            window.scrollTo(0, currentScrollPosition);
        }
    }

     /**
     * Update mini indicator text based on state
     */
    function updateMiniIndicatorState() {
         const miniIndicator = document.getElementById('content-analysis-mini-indicator');
         if (miniIndicator) {
             if (!isSidebarVisible) { // Indicator should be shown
                let text = 'Analysis';
                if (isProcessingInitial) text = 'Analyzing...';
                else if (activeAsyncTaskCount > 0) {
                     // Check for specific tasks (can be refined)
                     if (document.querySelector('.search-results .spinner')) text = 'Searching...';
                     else if (document.querySelector('.result-item div[style*="Checking alignment"]')) text = 'Checking...';
                     else text = 'Working...'; // Generic for query gen or comparison
                }
                miniIndicator.innerHTML = `<div style="transform: rotate(-90deg); white-space: nowrap; font-size: 12px;">${text}</div>`;
                miniIndicator.style.display = 'flex';
             } else { // Indicator should be hidden
                 miniIndicator.style.display = 'none';
             }
         }
    }

    /**
     * Create mini indicator to show when sidebar is hidden
     */
    function createMiniIndicator() {
        const existingIndicator = document.getElementById('content-analysis-mini-indicator');
        if (existingIndicator) existingIndicator.remove();

        const indicator = document.createElement('div');
        indicator.id = 'content-analysis-mini-indicator';
        indicator.style.cssText = `
            position: fixed; top: 100px; right: 0; width: ${MINI_INDICATOR_WIDTH}; height: 80px;
            background-color: rgba(70, 130, 180, 0.9); border-radius: 5px 0 0 5px;
            box-shadow: -2px 0 5px rgba(0, 0, 0, 0.2); z-index: ${SIDEBAR_Z_INDEX}; cursor: pointer;
            display: none; /* Start hidden, shown by updateMiniIndicatorState */ align-items: center; justify-content: center; color: white;
            font-weight: bold; font-family: Arial, sans-serif; transition: background-color 0.3s ease;
        `;
        indicator.addEventListener('mouseenter', () => indicator.style.backgroundColor = 'rgba(70, 130, 180, 1)');
        indicator.addEventListener('mouseleave', () => indicator.style.backgroundColor = 'rgba(70, 130, 180, 0.9)');
        indicator.addEventListener('click', toggleSidebarVisibility);

        document.body.appendChild(indicator);
        updateMiniIndicatorState(); // Set initial text and visibility based on current state
    }


    /**
    * Adjust page layout to make room for sidebar (simplified)
    */
    function adjustPageForSidebar() {
        document.body.style.marginRight = SIDEBAR_WIDTH;
        originalElementStyles.forEach(item => {
            if (item.element && document.body.contains(item.element)) {
                const computedStyle = window.getComputedStyle(item.element);
                 if (computedStyle.position === 'fixed') {
                     // Check if element's right edge is potentially within the sidebar space
                     const elementRect = item.element.getBoundingClientRect();
                     const viewportWidth = window.innerWidth;
                     // Adjust if right edge is within sidebar width from viewport right edge, and not explicitly left-anchored
                     if ((viewportWidth - elementRect.right) < parseInt(SIDEBAR_WIDTH) && computedStyle.left !== '0px') {
                         const originalRightValue = parseFloat(item.right) || 0; // Use stored computed value
                         item.element.style.right = `${originalRightValue + parseFloat(SIDEBAR_WIDTH)}px`;
                     }
                 }
            }
        });
    }

    /**
    * Create and add the sidebar to the page
    */
    function createSidebar() {
        const sidebar = document.createElement('div');
        sidebar.id = 'content-analysis-sidebar';
        sidebar.style.cssText = `
            position: fixed; top: 0; right: 0; width: ${SIDEBAR_WIDTH}; height: 100%;
            background-color: white; border-left: 1px solid #ccc; box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
            z-index: ${SIDEBAR_Z_INDEX}; font-family: Arial, sans-serif; font-size: 14px; color: #333;
            display: flex; flex-direction: column;
        `;

        // --- Header ---
        const header = document.createElement('div');
        header.style.cssText = `padding: 10px; background-color: #f8f8f8; border-bottom: 1px solid #ccc; display: flex; justify-content: space-between; align-items: center; z-index: 1; flex-shrink: 0;`;
        const title = document.createElement('h2'); title.textContent = 'Content Analysis'; title.style.cssText = `margin: 0; font-size: 16px;`;
        const buttonContainer = document.createElement('div'); buttonContainer.style.display = 'flex';
        const minimizeButton = document.createElement('button'); minimizeButton.textContent = '−'; minimizeButton.title = 'Minimize'; minimizeButton.style.cssText = `background: none; border: none; font-size: 20px; cursor: pointer; color: #777; margin-left: 10px; padding: 0 5px; line-height: 1;`; minimizeButton.addEventListener('click', toggleSidebarVisibility);
        const closeButton = document.createElement('button'); closeButton.textContent = '×'; closeButton.title = 'Close and remove'; closeButton.style.cssText = `background: none; border: none; font-size: 20px; cursor: pointer; color: #777; padding: 0 5px; line-height: 1;`; closeButton.addEventListener('click', closeSidebar);
        buttonContainer.appendChild(minimizeButton); buttonContainer.appendChild(closeButton);
        header.appendChild(title); header.appendChild(buttonContainer);
        sidebar.appendChild(header);

        // --- URL Input Section ---
        const urlInputSection = document.createElement('div'); urlInputSection.className = 'url-input-section'; urlInputSection.style.cssText = `padding: 10px 15px; background-color: #f5f5f5; border-bottom: 1px solid #e0e0e0; flex-shrink: 0;`;
        const urlInputTitle = document.createElement('div'); urlInputTitle.textContent = 'Custom Search Sources (Domains)'; urlInputTitle.style.cssText = `font-weight: bold; margin-bottom: 8px; font-size: 13px;`; urlInputSection.appendChild(urlInputTitle);
        const urlList = document.createElement('div'); urlList.id = 'custom-url-list'; urlList.style.cssText = `margin-top: 5px; max-height: 100px; overflow-y: auto; font-size: 12px; padding-right: 5px;`; urlList.innerHTML = '<div style="font-size:11px; color:#888; text-align:center; padding: 5px 0;"><i>Loading sources...</i></div>'; urlInputSection.appendChild(urlList);
        sidebar.appendChild(urlInputSection);

        // --- Main Content Area (Results) ---
        const content = document.createElement('div'); content.id = 'content-analysis-results'; content.style.cssText = `padding: 15px; flex-grow: 1; overflow-y: auto;`;
        // Add initial loading indicator
        const loading = document.createElement('div'); loading.id = 'content-analysis-loading'; loading.style.cssText = `text-align: center; padding: 20px;`; loading.innerHTML = `<div style="margin-bottom: 10px;">Analyzing content...</div><div class="spinner"></div><style>.spinner{border:4px solid #f3f3f3;border-top:4px solid #3498db;border-radius:50%;width:30px;height:30px;animation:spin 1s linear infinite;margin:0 auto;}@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}</style>`; content.appendChild(loading);
        sidebar.appendChild(content);

        // Add to page and final setup
        document.body.appendChild(sidebar);
        adjustPageForSidebar(); // Adjust page layout AFTER adding to DOM
        isSidebarVisible = true; // Set state

        // Load Saved URLs (now that container exists)
        setTimeout(() => { loadSavedUrls(); }, 50);
    }

    /**
     * Close the sidebar and clean up
     */
    function closeSidebar() {
        currentScrollPosition = window.scrollY; // Save scroll before potential style changes
        const sidebar = document.getElementById('content-analysis-sidebar');
        if (sidebar) sidebar.remove();
        const miniIndicator = document.getElementById('content-analysis-mini-indicator');
        if (miniIndicator) miniIndicator.remove();

        restoreOriginalStyles(); // Restore body margin etc.
        removeHighlights();
        document.removeEventListener('selectionchange', handleSelectionChange);
        window.removeEventListener('resize', debouncedAdjustStyles); // Remove listener

        window.scrollTo(0, currentScrollPosition); // Restore scroll after style changes

        // Reset state
        isSidebarVisible = false; relevantChunks = []; lastUsedQuery = {};
        originalElementStyles = []; originalBodyStyles = {}; activeAsyncTaskCount = 0; isProcessingInitial = false;
    }

     /**
     * Extract content from the page and send to server for analysis
     */
    async function extractContent() {
        const metadata = {
             html: document.documentElement.outerHTML, url: window.location.href, title: document.title, author: getAuthor(), date: getPublishedDate()
        };
        try {
            const response = await fetch(`${SERVER_BASE_URL}/api/extract`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(metadata)
            });
            if (!response.ok) {
                 if (response.status === 403) { console.warn("Extract 403: Offering proxy."); showProxyNavigationDialog(); return []; }
                 else { const err = await response.text(); throw new Error(`Server Error ${response.status}: ${err}`); }
            }
            return await response.json();
        } catch (error) {
            console.error('extractContent Error:', error);
             if (error instanceof TypeError && (error.message.includes('fetch') || error.message.includes('NetworkError'))) {
                  console.warn("Extract network/CORS error: Offering proxy.");
                  showProxyNavigationDialog();
             } else {
                  // Re-throw other errors to be caught by the caller (init)
                  throw error;
             }
             return []; // Return empty on handled errors like proxy dialog
        }
    }

    /**
     * Show dialog asking user if they want to navigate via proxy
     */
    function showProxyNavigationDialog() {
         const resultsContainer = document.getElementById('content-analysis-results');
         if (!resultsContainer) {
             if (confirm("Error analyzing page (maybe CORS?). Reload via proxy?")) navigateToProxyUrl();
             return;
         }
         // Clear results area and show dialog
         resultsContainer.innerHTML = '';
         const dialog = document.createElement('div'); dialog.id = 'proxy-navigation-dialog'; dialog.style.cssText = `background-color: #fff7e6; border: 1px solid #ffcc80; border-radius: 5px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; color: #333;`;
         dialog.innerHTML = `<p style="margin:0 0 10px 0;font-size:16px;font-weight:bold;">Extraction Error</p><p style="margin:0 0 15px 0;font-size:14px;">Could not directly analyze this page (maybe security/CORS).</p><p style="margin:0 0 15px 0;font-size:14px;">Reload via analysis proxy?</p><button id="dialog-yes" style="margin:5px;padding:8px 15px;background-color:#4CAF50;color:white;border:none;border-radius:3px;cursor:pointer;font-size:13px;">Yes, Reload via Proxy</button><button id="dialog-no" style="margin:5px;padding:8px 15px;background-color:#f44336;color:white;border:none;border-radius:3px;cursor:pointer;font-size:13px;">No, Close Analysis</button>`;
         resultsContainer.appendChild(dialog);
         // Add listeners AFTER appending
         document.getElementById('dialog-yes')?.addEventListener('click', navigateToProxyUrl);
         document.getElementById('dialog-no')?.addEventListener('click', closeSidebar);
    }


    function navigateToProxyUrl() {
        const currentUrl = window.location.href;
        const proxyUrl = `${SERVER_BASE_URL}/proxy?url=${encodeURIComponent(currentUrl)}`;
        window.location.href = proxyUrl;
    }

    /**
      * Summarize selected text
      */
    async function summarizeSelection() {
        const selection = window.getSelection();
        if (!selection) return;
        const selectedText = selection.toString().trim();
        if (!selectedText) return;

        const summarizeButton = document.getElementById('summarize-selection-button');
        const resultsContainer = document.getElementById('content-analysis-results');
        if (!resultsContainer) return;

        if(summarizeButton) summarizeButton.disabled = true;
        const tempMessage = document.createElement('div'); tempMessage.id = 'summarize-temp-message'; tempMessage.textContent = 'Summarizing selection...'; tempMessage.style.cssText = `padding: 10px; font-style: italic; text-align: center; border-bottom: 1px solid #eee; margin-bottom: 15px;`;
        summarizeButton?.parentNode?.parentNode?.insertBefore(tempMessage, summarizeButton.parentNode.nextSibling);

        startAsyncTask(); // Indicate summary started

        try {
            const response = await fetch(`${SERVER_BASE_URL}/api/extract/selection`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: selectedText })
            });
            tempMessage.remove();
            if (!response.ok) { const err = await response.text(); throw new Error(`Server Error ${response.status}: ${err}`); }

            const newChunk = await response.json();
            relevantChunks.unshift(newChunk);
            displayResults(relevantChunks); // Re-display all results

        } catch (error) {
             tempMessage.remove();
             console.error('Error summarizing selection:', error);
             // Show transient error message below button
             const errorDiv = document.createElement('div'); errorDiv.style.cssText = `color:red;padding:10px;border:1px solid #fcc;background-color:#ffebee;border-radius:3px;margin-top:10px;text-align:center;`; errorDiv.textContent = `Failed to summarize selection: ${error.message}`;
             summarizeButton?.parentNode?.parentNode?.insertBefore(errorDiv, summarizeButton.parentNode.nextSibling);
             setTimeout(() => errorDiv.remove(), 5000); // Remove after 5s
        } finally {
             endAsyncTask(); // Indicate summary finished
             handleSelectionChange(); // Re-check selection state for button
        }
    }

    /** Helper function to extract the domain from a URL */
    function extractDomain(url) {
        try {
            if (!url) return null;
            let fullUrl = url;
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                fullUrl = 'https://' + url;
            }
            const parsedUrl = new URL(fullUrl);
            let domain = parsedUrl.hostname.replace(/^www\./, '');
            return domain.toLowerCase();
        } catch (e) {
            console.warn("Failed URL parse/domain extract:", url, e);
             const match = url.match(/^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/?#\s]+)/im);
             return match?.[1]?.toLowerCase() || null;
        }
    }

    /** Check if URL is from the same domain as the current page */
    function isSameDomain(url, currentUrl) {
        const urlDomain = extractDomain(url);
        const currentDomain = extractDomain(currentUrl);
        return urlDomain && currentDomain && urlDomain === currentDomain;
    }

    /** Check if a domain is already in the custom URL list */
    function isDomainInCustomUrls(domain) {
        const customUrls = getCustomUrls(); // Gets full URLs like https://domain.com
        const normalizedDomainToCheck = domain?.toLowerCase().replace(/^https?:\/\/(www\.)?/i, '');
         if (!normalizedDomainToCheck) return false;
        return customUrls.some(fullUrl => extractDomain(fullUrl) === normalizedDomainToCheck);
    }

    /**
    * Display the analysis results in the sidebar
    */
    function displayResults(chunks) {
        relevantChunks = chunks; // Update global state
        const resultsContainer = document.getElementById('content-analysis-results');
        if (!resultsContainer || !document.body.contains(resultsContainer)) {
             console.warn("displayResults called but results container missing");
             return;
        }

        // --- *** FIX: Explicitly remove loading indicator *** ---
        const loadingIndicator = resultsContainer.querySelector('#content-analysis-loading');
        if (loadingIndicator) {
            loadingIndicator.remove();
            // console.log("Removed loading indicator."); // Debug log
        }
        // -------------------------------------------------------

        // Clear previous results content (button/chunks)
        resultsContainer.innerHTML = '';

        // --- Add Summarize Selection Button ---
        const summarizeButtonContainer = document.createElement('div'); summarizeButtonContainer.style.cssText = `padding-bottom: 15px; border-bottom: 1px solid #eee; margin-bottom: 15px;`;
        const summarizeSelectionButton = document.createElement('button'); summarizeSelectionButton.id = 'summarize-selection-button'; summarizeSelectionButton.textContent = 'Summarize Selected Text'; summarizeSelectionButton.disabled = true; summarizeSelectionButton.style.cssText = `width: 100%; padding: 8px 12px; background-color: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; transition: background-color 0.2s ease;`; summarizeSelectionButton.addEventListener('click', summarizeSelection); summarizeSelectionButton.onmouseover = () => { if (!summarizeSelectionButton.disabled) summarizeSelectionButton.style.backgroundColor = '#5a6268'; }; summarizeSelectionButton.onmouseout = () => { if (!summarizeSelectionButton.disabled) summarizeSelectionButton.style.backgroundColor = '#6c757d'; };
        if (!document.getElementById('summarize-button-disabled-style')) { /* Add disabled style if needed */ const style = document.createElement('style'); style.id = 'summarize-button-disabled-style'; style.textContent = `#summarize-selection-button:disabled { background-color: #adb5bd !important; cursor: not-allowed; opacity: 0.7; }`; document.head.appendChild(style); }
        summarizeButtonContainer.appendChild(summarizeSelectionButton);
        resultsContainer.appendChild(summarizeButtonContainer);
        handleSelectionChange(); // Set initial button state

         // If no chunks, show message
         if (!chunks || chunks.length === 0) {
              const noChunksMsg = document.createElement('div'); noChunksMsg.style.cssText = `text-align: center; padding: 20px; font-style: italic;`; noChunksMsg.textContent = 'No relevant content points identified on this page.';
              resultsContainer.appendChild(noChunksMsg);
             return; // Stop here if no chunks
         }

        // --- Create accordion for each chunk ---
        chunks.forEach((chunk, index) => {
            // Generate query immediately (don't await, handles own async/state)
            generateAndStoreQuery(chunk);

            const chunkContainer = document.createElement('div'); chunkContainer.id = chunk.id; chunkContainer.className = 'chunk-container'; chunkContainer.style.cssText = `margin-bottom: 15px; border: 1px solid #e0e0e0; border-radius: 4px; background-color: #f9f9f9; overflow: hidden;`;
            // --- Summary Section ---
            const summaryContainer = document.createElement('div'); summaryContainer.className = 'chunk-summary'; summaryContainer.style.cssText = `padding: 10px; background-color: #f1f1f1; border-bottom: 1px solid #e0e0e0; font-size: 14px;`;
            const summaryText = document.createElement('span'); summaryText.textContent = chunk.summary || `(No summary for Point ${index + 1})`; summaryText.style.cssText = `display: block; margin-bottom: 8px;`; summaryContainer.appendChild(summaryText);
            // Compare Checkbox
            const compareImmediatelyLabel = document.createElement('label'); compareImmediatelyLabel.style.cssText = `display: flex; align-items: center; font-size: 11px; color: #555; cursor: pointer; margin-top: 5px;`;
            const compareImmediatelyCheckbox = document.createElement('input'); compareImmediatelyCheckbox.type = 'checkbox'; compareImmediatelyCheckbox.id = `compare-immediately-${chunk.id}`; compareImmediatelyCheckbox.style.marginRight = '4px'; compareImmediatelyCheckbox.title = 'Auto-check alignment for search results'; compareImmediatelyLabel.appendChild(compareImmediatelyCheckbox); compareImmediatelyLabel.appendChild(document.createTextNode('Compare immediately')); summaryContainer.appendChild(compareImmediatelyLabel); chunkContainer.appendChild(summaryContainer);
            // --- Header (Query + Controls) ---
            const chunkHeader = document.createElement('div'); chunkHeader.className = 'chunk-header'; chunkHeader.style.cssText = `padding: 8px 10px; background-color: #e9e9ed; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e0e0e0;`;
            // Query Placeholder/Input (dynamic update via generateAndStoreQuery)
             let initialQueryElement; // Create the initial element based on current state
             if (lastUsedQuery[chunk.id] && lastUsedQuery[chunk.id] !== 'Generating...') { initialQueryElement = createEditableQueryInput(chunk.id, lastUsedQuery[chunk.id]); }
             else { /* Create "Generating..." div */ initialQueryElement = document.createElement('div'); initialQueryElement.id = `query-display-${chunk.id}`; initialQueryElement.textContent = '[Generating query...]'; initialQueryElement.style.cssText = `font-size: 11px; color: #666; font-style: italic; margin-right: 10px; flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 3px 0; min-width: 50px;`; if (!lastUsedQuery[chunk.id]) lastUsedQuery[chunk.id] = 'Generating...'; }
             chunkHeader.appendChild(initialQueryElement); // Add the starting element
            // Controls
            const controlsDiv = document.createElement('div'); controlsDiv.style.cssText = `display: flex; align-items: center; flex-shrink: 0;`;
            const removeChunkButton = document.createElement('button'); removeChunkButton.textContent = '×'; removeChunkButton.title = 'Remove this point'; removeChunkButton.style.cssText = `background: none; border: none; font-size: 18px; font-weight: bold; cursor: pointer; color: #f44336; padding: 0 5px; line-height: 1; margin-right: 5px; order: -1;`; removeChunkButton.addEventListener('click', (e) => { e.stopPropagation(); removeChunk(chunk.id); }); controlsDiv.appendChild(removeChunkButton);
            const toggleIcon = document.createElement('span'); toggleIcon.className = 'toggle-icon'; toggleIcon.textContent = '▶'; toggleIcon.style.cssText = `margin-left: 8px; width: 10px; text-align: center;`; controlsDiv.appendChild(toggleIcon); chunkHeader.appendChild(controlsDiv); chunkContainer.appendChild(chunkHeader);
            // --- Content Section (Results) ---
            const chunkContent = document.createElement('div'); chunkContent.className = 'chunk-content'; chunkContent.style.cssText = `padding: 15px; display: none; position: relative; background-color: white;`;
            const searchResultsContainer = document.createElement('div'); searchResultsContainer.className = 'search-results'; searchResultsContainer.id = `search-results-${chunk.id}`; searchResultsContainer.style.display = 'none'; chunkContent.appendChild(searchResultsContainer);
            // Reset Button
            const resetButtonContainer = document.createElement('div'); resetButtonContainer.className = 'reset-button-container'; resetButtonContainer.id = `reset-button-container-${chunk.id}`; resetButtonContainer.style.cssText = `display: none; margin-top: 15px; text-align: right;`;
            const resetButton = document.createElement('button'); resetButton.className = 'reset-search-button'; resetButton.textContent = 'Reset'; resetButton.title = 'Clear results and edit query'; resetButton.style.cssText = `padding: 5px 10px; background-color: #ff9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;`;
            resetButton.addEventListener('click', (e) => { /* Reset logic */
                e.stopPropagation(); searchResultsContainer.innerHTML = ''; searchResultsContainer.style.display = 'none';
                const currentQueryDisplay = document.getElementById(`query-display-${chunk.id}`);
                if (currentQueryDisplay && currentQueryDisplay.tagName === 'DIV') { const currentQuery = lastUsedQuery[chunk.id] || ''; const editableInput = createEditableQueryInput(chunk.id, currentQuery); currentQueryDisplay.parentNode?.replaceChild(editableInput, currentQueryDisplay); }
                else if (!currentQueryDisplay) { console.warn(`Reset chunk ${chunk.id}: Could not find query display.`); } // Do nothing if already input
                chunkContent.style.display = 'none'; toggleIcon.textContent = '▶'; resetButtonContainer.style.display = 'none'; removeHighlights();
            });
            resetButtonContainer.appendChild(resetButton); chunkContent.appendChild(resetButtonContainer); chunkContainer.appendChild(chunkContent);

            // --- Header Click Listener (Toggle Expand/Collapse/Search) ---
            chunkHeader.addEventListener('click', () => {
                const queryElement = document.getElementById(`query-display-${chunk.id}`);
                let currentQueryValue = lastUsedQuery[chunk.id] || '';

                if (queryElement?.tagName === 'INPUT') { /* Finalize edit */
                     currentQueryValue = queryElement.value.trim(); lastUsedQuery[chunk.id] = currentQueryValue; const queryDisplayDiv = createNonEditableQueryDiv(chunk.id, currentQueryValue); queryElement.parentNode?.replaceChild(queryDisplayDiv, queryElement);
                } else if (queryElement) { /* Already DIV, ensure value sync */
                     currentQueryValue = lastUsedQuery[chunk.id] || '';
                } else { console.warn(`Header click chunk ${chunk.id}: Query element missing.`); return; }

                // Check query state before proceeding
                if (currentQueryValue === 'Generating...') { console.log(`Chunk ${chunk.id}: Query generating.`); return; }
                if (!currentQueryValue) { console.log(`Chunk ${chunk.id}: Query empty.`); /* Maybe add visual cue? */ return; }
                const queryHasError = currentQueryValue.startsWith('Error:');

                // Toggle Content Visibility
                if (chunkContent.style.display === 'none') { // --- Expand ---
                    chunkContent.style.display = 'block'; toggleIcon.textContent = '▼'; highlightChunk(chunk);
                    // Check if fetch needed
                    const isLoading = searchResultsContainer.querySelector('.spinner') !== null;
                    const hasRealContent = Array.from(searchResultsContainer.childNodes).some(n => n.nodeType !== Node.COMMENT_NODE && (n.nodeType !== Node.ELEMENT_NODE || !n.classList.contains('reset-button-container')) && n.textContent?.trim() !== '');
                    const hasErrorDisplayed = searchResultsContainer.querySelector('[style*="color:red"]') !== null;

                    // Fetch evidence if query valid, no content/error yet, not loading
                    if (!queryHasError && !hasRealContent && !isLoading) {
                         retrieveEvidence(chunk, chunkContent);
                    }
                    // Show stored query error if not already shown
                    else if (queryHasError && !hasErrorDisplayed && !isLoading) {
                         retrieveEvidence(chunk, chunkContent); // Call to display the error
                    }
                    // Ensure reset button visible if content exists (and no error displayed)
                    else if (hasRealContent && !hasErrorDisplayed) {
                         resetButtonContainer.style.display = 'block';
                    }
                } else { // --- Collapse ---
                    chunkContent.style.display = 'none'; toggleIcon.textContent = '▶'; removeHighlights();
                }
            });

            // Append completed chunk container to results area
            resultsContainer.appendChild(chunkContainer);
        });

    } // End of displayResults function


    /**
    * Remove a specific chunk by ID with animation
    */
    function removeChunk(chunkId) {
      const chunkElement = document.getElementById(chunkId);
      if (chunkElement) {
          chunkElement.style.transition = 'opacity 0.3s ease-out, height 0.3s ease-out, margin 0.3s ease-out, padding 0.3s ease-out, border 0.3s ease-out';
          requestAnimationFrame(() => { // Ensure transition starts after styles are set
              chunkElement.style.opacity = '0'; chunkElement.style.height = '0'; chunkElement.style.margin = '0'; chunkElement.style.padding = '0'; chunkElement.style.borderWidth = '0';
          });
          setTimeout(() => {
              relevantChunks = relevantChunks.filter(c => c.id !== chunkId); delete lastUsedQuery[chunkId];
              chunkElement.remove();
              if (relevantChunks.length === 0) { /* Show "All points removed" message */
                   const resultsContainer = document.getElementById('content-analysis-results');
                   if (resultsContainer && !resultsContainer.querySelector('.chunk-container')) {
                        const noChunksMsg = document.createElement('div'); noChunksMsg.style.cssText = `text-align: center; padding: 20px; font-style: italic;`; noChunksMsg.textContent = 'All points removed.';
                        const buttonContainer = document.getElementById('summarize-selection-button')?.parentNode;
                        if (buttonContainer) buttonContainer.parentNode.insertBefore(noChunksMsg, buttonContainer.nextSibling);
                        else resultsContainer.appendChild(noChunksMsg);
                   }
              }
          }, 310); // Slightly longer than transition
      } else { /* Fallback re-render */
           console.warn(`Attempted to remove chunk ${chunkId} but element not found.`);
           relevantChunks = relevantChunks.filter(c => c.id !== chunkId); delete lastUsedQuery[chunkId];
           displayResults(relevantChunks); // Less smooth, but recovers state
      }
    }

    /**
    * Retrieve supporting evidence for a chunk using the stored query.
    * Displays results or error messages. Handles the "Compare Immediately" logic.
    */
    async function retrieveEvidence(chunk, chunkContent) {
        const searchResultsContainer = chunkContent.querySelector('.search-results');
        const resetButtonContainer = chunkContent.querySelector('.reset-button-container');
        const queryDisplayElement = document.getElementById(`query-display-${chunk.id}`); // Should be DIV here
        if (!searchResultsContainer || !resetButtonContainer || !queryDisplayElement) {
             console.warn("retrieveEvidence called with missing elements for chunk:", chunk.id);
             return;
        }

        let queryState = lastUsedQuery[chunk.id];

        // Handle query error state immediately
        if (queryState && queryState.startsWith('Error:')) {
             searchResultsContainer.style.display = 'block';
             searchResultsContainer.innerHTML = `<div style="color:red; padding:10px; border: 1px solid #fcc; background-color: #ffebee; border-radius: 3px;">Could not retrieve evidence: ${queryState.replace('Error: ', '')}</div>`;
             resetButtonContainer.style.display = 'block';
             return;
        }
        // Handle empty/generating state
        if (!queryState || queryState === 'Generating...') {
             searchResultsContainer.style.display = 'block';
             searchResultsContainer.innerHTML = `<div style="padding:10px; text-align: center; font-style: italic;">${queryState === 'Generating...' ? 'Query generating...' : 'Query empty.'}</div>`;
             resetButtonContainer.style.display = queryState ? 'block' : 'none'; // Show reset if empty
             return;
        }

        // Proceed with valid query
        const cleanQuery = queryState;
        searchResultsContainer.style.display = 'block';
        searchResultsContainer.innerHTML = `<div style="text-align:center; padding:10px;"><div style="margin-bottom: 10px; font-size: 13px;">Searching for evidence: "${cleanQuery}"...</div><div class="spinner"></div></div>`;
        resetButtonContainer.style.display = 'none';

        startAsyncTask(); // Indicate search started

        try {
            const context = { url: window.location.href, title: document.title, author: getAuthor(), date: getPublishedDate() };
            const customUrls = getCustomUrls();
            const searchResponse = await fetch(`${SERVER_BASE_URL}/api/retrieve/search?query=${encodeURIComponent(cleanQuery)}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ context, custom_urls: customUrls })
            });

            if (!searchResponse.ok) { const err = await searchResponse.text(); throw new Error(`Search failed ${searchResponse.status}: ${err}`); }

            const searchResults = await searchResponse.json();
            searchResultsContainer.innerHTML = ''; // Clear loading
            const resultsList = document.createElement('div'); resultsList.className = 'results-list';

            if (!searchResults || searchResults.length === 0) {
                resultsList.innerHTML = `<div style="padding:10px; text-align: center; font-style:italic;">No evidence found for: "${cleanQuery}".</div>`;
            } else {
                const resultsHeader = document.createElement('div'); resultsHeader.style.cssText = `font-weight: bold; margin: 0 0 10px 0; font-size: 13px;`; resultsHeader.textContent = 'Supporting Evidence:'; resultsList.appendChild(resultsHeader);
                const currentPageDomain = extractDomain(window.location.href);
                const compareImmediatelyCheckbox = document.getElementById(`compare-immediately-${chunk.id}`);
                const shouldCompareImmediately = compareImmediatelyCheckbox?.checked || false;

                // --- Process each search result ---
                searchResults.forEach((result, index) => {
                    const resultDomain = extractDomain(result.url);
                    const displayDomain = resultDomain ? resultDomain.split('.').slice(-2).join('.') : 'Source';
                    const isSameDomainResult = resultDomain && currentPageDomain && resultDomain === currentPageDomain;

                    // --- Create Result Item Structure ---
                    const resultItem = document.createElement('div'); resultItem.className = 'result-item'; resultItem.style.cssText = `margin-bottom: 15px; padding: 10px; border: 1px solid #e0e0e0; border-radius: 4px; background-color: ${isSameDomainResult ? SAME_DOMAIN_BACKGROUND : 'white'};`; resultItem.dataset.domain = resultDomain || ''; resultItem.dataset.url = result.url;
                    // Title
                    const title = document.createElement('a'); title.href = result.url; title.target = '_blank'; title.rel = 'noopener noreferrer'; title.textContent = result.title || 'Untitled'; title.style.cssText = `color: #1a0dab; font-weight: bold; text-decoration: none; display: block; margin-bottom: 4px; font-size: 14px;`; title.addEventListener('mouseover', () => title.style.textDecoration = 'underline'); title.addEventListener('mouseout', () => title.style.textDecoration = 'none'); resultItem.appendChild(title);
                    // Snippet
                    const snippet = document.createElement('div'); snippet.innerHTML = result.snippet ? result.snippet.replace(/</g, "<").replace(/>/g, ">") : '(No snippet)'; snippet.style.cssText = `margin-top: 5px; font-size: 13px; color: #555; line-height: 1.4;`; resultItem.appendChild(snippet);
                    // Buttons & Alignment Area
                    const buttonContainer = document.createElement('div'); buttonContainer.style.cssText = `margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;`;
                    const alignmentResult = document.createElement('div'); alignmentResult.id = `alignment-${chunk.id}-${index}`; alignmentResult.style.cssText = `display: none; margin-top: 8px;`; // Alignment results go here

                    // --- Add Buttons Conditionally ---
                    // Compare Button (only if checkbox NOT checked)
                    if (!shouldCompareImmediately) {
                        const compareButton = document.createElement('button');
                        compareButton.textContent = 'Check alignment';
                        compareButton.className = 'compare-button';
                        compareButton.style.cssText = `padding: 3px 8px; background-color: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; transition: background-color 0.2s;`;
                        compareButton.onmouseover = () => compareButton.style.backgroundColor = '#1976D2';
                        compareButton.onmouseout = () => compareButton.style.backgroundColor = '#2196F3';
                        compareButton.addEventListener('click', (e) => {
                            e.stopPropagation();
                            compareButton.disabled = true; // Button deaktivieren
                            compareContent(chunk, result.url, alignmentResult);
                        });
                        buttonContainer.appendChild(compareButton);
                    }
                    // Source Button (if domain valid)
                    if (resultDomain) {
                        const sourceButton = document.createElement('button'); sourceButton.className = 'source-button'; sourceButton.style.cssText = `padding: 3px 8px; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; white-space: nowrap; transition: background-color 0.2s;`; updateSourceButtonState(sourceButton, resultDomain, displayDomain); buttonContainer.appendChild(sourceButton);
                    }
                    if (buttonContainer.hasChildNodes()) resultItem.appendChild(buttonContainer); // Add container only if it has buttons

                    resultItem.appendChild(alignmentResult); // Add alignment container (initially hidden)
                    resultsList.appendChild(resultItem); // Add completed item to list

                    // --- *** FIX: Trigger Automatic Comparison *** ---
                    if (shouldCompareImmediately) {
                         // *** ADD THIS LOGGING ***
                         console.log(`[Chunk ${chunk.id}] Result ${index}: Checkbox checked. Calling compareContent for URL: ${result.url}`);
                         // *** Defer the call slightly using setTimeout ***
                        setTimeout(() => {
                            // *** Re-fetch and re-check container existence INSIDE the timeout ***
                            //    It's crucial because the user might interact between scheduling and execution.
                            const currentAlignmentResultContainer = document.getElementById(`alignment-${chunk.id}-${index}`);
                            if (currentAlignmentResultContainer && document.body.contains(currentAlignmentResultContainer)) {
                                 // console.log(`[Chunk ${chunk.id}] Result ${index}: setTimeout executing. Calling compareContent for URL: ${result.url}`);
                                 compareContent(chunk, result.url, currentAlignmentResultContainer); // Pass the freshly fetched container
                            } else {
                                 console.warn(`[Chunk ${chunk.id}] Result ${index}: setTimeout skipped. Container removed before compareContent execution for URL: ${result.url}`);
                            }
                        }, 0); // Delay of 0ms pushes execution to the next event loop cycle
                    }
                    // ---------------------------------------------
                });
            }
            searchResultsContainer.appendChild(resultsList);
            updateAllSourceButtons(); // Ensure button states correct
            resetButtonContainer.style.display = 'block'; // Show reset button

        } catch (error) {
            console.error(`Error retrieving evidence chunk ${chunk.id}:`, error);
            searchResultsContainer.innerHTML = `<div style="color:red; padding:10px; border: 1px solid #fcc; background-color: #ffebee; border-radius: 3px;">Error finding evidence: ${error.message}</div>`;
            resetButtonContainer.style.display = 'block'; // Show reset on error too
        } finally {
            endAsyncTask(); // Indicate search finished
        }
    } // End of retrieveEvidence function

    /**
     * Updates the state of the source button (Add/Remove) and sets onclick
     */
    function updateSourceButtonState(button, domain, displayDomain) {
         if (!domain) { button.style.display = 'none'; return; }
         button.style.display = ''; // Ensure visible

        const normalizedDomain = domain.toLowerCase().replace(/^https?:\/\/(www\.)?/i, '');
        const isInCustomUrls = isDomainInCustomUrls(normalizedDomain);
        button.onclick = null; // Clear previous

        const urlWithProto = domain.startsWith('http') ? domain : `https://${domain}`; // Use consistent URL with protocol

        if (isInCustomUrls) { /* Remove button setup */
            button.textContent = `Remove ${displayDomain}`; button.title = `Remove ${displayDomain}`; button.style.backgroundColor = '#f44336';
            button.onmouseover = () => button.style.backgroundColor = '#d32f2f'; button.onmouseout = () => button.style.backgroundColor = '#f44336';
            button.onclick = (e) => { e.stopPropagation(); removeCustomUrl(urlWithProto); };
        } else { /* Add button setup */
            button.textContent = `Add ${displayDomain}`; button.title = `Add ${displayDomain}`; button.style.backgroundColor = '#4CAF50';
            button.onmouseover = () => button.style.backgroundColor = '#388E3C'; button.onmouseout = () => button.style.backgroundColor = '#4CAF50';
            button.onclick = (e) => { e.stopPropagation(); addDomainToCustomUrls(urlWithProto); };
        }
    }

    /**
     * Compare original content with content from a search result
     */
    async function compareContent(chunk, url, resultContainer) {
        // Check if container still exists in DOM before proceeding
        console.log(`[Chunk ${chunk.id}] compareContent called for URL: ${url}`);
        if (!resultContainer || !document.body.contains(resultContainer)) {
             console.warn(`[Chunk ${chunk.id}] CompareContent skipped: Result container removed or not found for URL: ${url}`);
             return; // Exit early if container invalid
        }

        resultContainer.style.display = 'block'; // Ensure visible
        resultContainer.innerHTML = `<div style="text-align:center; padding:5px; font-size: 12px; font-style: italic; color: #666;">Checking alignment...</div>`;

        // console.log(`compareContent started for chunk ${chunk.id}, url ${url}`); // Debugging line
        startAsyncTask(); // Indicate comparison started

        try {
            const context = { url: window.location.href, title: document.title, author: getAuthor(), date: getPublishedDate() };
            const requestBody = JSON.stringify({ original_chunk: chunk, search_result_url: url, query: lastUsedQuery[chunk.id] || '', context });
            // console.log(`compareContent fetching for chunk ${chunk.id}`); // Debugging line

            // *** ADD FETCH LOG ***
            console.log(`[Chunk ${chunk.id}] Fetching /api/compare for URL: ${url}`);
            // -------------------
            const response = await fetch(`${SERVER_BASE_URL}/api/compare/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: requestBody
            });

            // *** ADD RESPONSE STATUS LOG ***
            console.log(`[Chunk ${chunk.id}] /api/compare response status: ${response.status} for URL: ${url}`);
            // -----------------------------

            // Check moved *after* fetch, but before processing response body
            if (!document.body.contains(resultContainer)) {
                console.warn(`[Chunk ${chunk.id}] CompareContent: Result container removed *during* fetch for URL: ${url}`);
                return; // Exit if container disappeared during await
            }

            if (!response.ok) {
                const err = await response.text();
                throw new Error(`Compare failed ${response.status}: ${err}`); // This doesn't seem to happen
            }

            // *** ADD PARSING LOG ***
            console.log(`[Chunk ${chunk.id}] Parsing JSON response for URL: ${url}`);
            // ----------------------
            const alignment = await response.json(); // <<< POTENTIAL ISSUE: Is the response valid JSON?

            // *** ADD ALIGNMENT DATA LOG ***
            console.log(`[Chunk ${chunk.id}] Alignment data received:`, alignment, `for URL: ${url}`);
            // ---------------------------

            // Check container again before displaying
            if (document.body.contains(resultContainer)) {
                 // *** ADD DISPLAY LOG ***
                 console.log(`[Chunk ${chunk.id}] Calling displayAlignmentResult for URL: ${url}`);
                 // ----------------------
                 displayAlignmentResult(alignment, resultContainer); // <<< POTENTIAL ISSUE: Does this update the UI?
            } else {
                 console.warn(`[Chunk ${chunk.id}] CompareContent: Result container removed before displaying result for URL: ${url}`);
            }

        } catch (error) { // <<< POTENTIAL ISSUE: Does an error happen *here*? (e.g., JSON parsing)
            console.error(`Error comparing chunk ${chunk.id}, url ${url}:`, error);
            if (document.body.contains(resultContainer)) {
                resultContainer.innerHTML = `<div style="color:red; padding:5px; font-size: 12px;">Error checking alignment: ${error.message}</div>`;
            }
        } finally {
             endAsyncTask(); // Comparison finished (success or fail)
        }
    }

    /** Display alignment results */
    function displayAlignmentResult(alignment, container) {
        // Final check if container exists
        if (!container || !document.body.contains(container)) {
            // *** ADD DISPLAY SKIP LOG ***
            console.warn(`[DisplayAlignment] Skipped display: Container removed.`);
            // -------------------------
            return;
        }

        // *** ADD DISPLAY EXECUTION LOG ***
        console.log(`[DisplayAlignment] Updating container innerHTML.`);
        // ------------------------------

        container.style.display = 'block';
        const scoreColor = getScoreColor(alignment.score);
        const scorePercent = (alignment.score * 100).toFixed(0);
        let alignmentHtml = `<div style="margin-top:8px; padding:8px; border-radius:4px; background-color:#f9f9f9; border: 1px solid #eee;">`;
        // ... construct HTML ...
        alignmentHtml += `<div style="font-weight:bold; font-size: 13px;">Alignment: <span style="color:${scoreColor}">${scorePercent}%</span></div>`;
        if (alignment.explanation) { const escaped = alignment.explanation.replace(/</g, "<").replace(/>/g, ">"); alignmentHtml += `<div style="margin-top:5px; font-size:12px; line-height: 1.4;">${escaped}</div>`; }
        if (alignment.matching_content) { const escaped = alignment.matching_content.replace(/</g, "<").replace(/>/g, ">"); alignmentHtml += `<div style="margin-top:5px; font-size:12px; border-left:3px solid ${scoreColor}; padding-left:8px; font-style: italic; color:#666;">"...${escaped}..."</div>`; }
        alignmentHtml += `</div>`;
        // --- The actual UI update ---
        container.innerHTML = alignmentHtml; // <<< THIS IS THE KEY UI UPDATE STEP
        // ----------------------------
    }

    /** Highlight the selected chunk in the original page */
    function highlightChunk(chunk) {
        removeHighlights(); // Clear previous highlights first
        if (!chunk?.content) return; // Check chunk and content existence

        const textNodes = getAllTextNodes(document.body); // Get relevant text nodes
        const chunkText = chunk.content.trim().toLowerCase(); // Normalize chunk text
        if (!chunkText) return; // Don't highlight empty content

        let firstHighlightElement = null; // To scroll to the first match

        for (const node of textNodes) {
            // Basic checks for relevance and visibility
            if (!node.parentElement || node.parentElement.closest('#content-analysis-sidebar')) continue;
            const nodeText = node.textContent.trim().toLowerCase();
            if (!nodeText || nodeText.length < 5) continue; // Ignore very short nodes
            if (!isElementVisible(node.parentElement)) continue; // Skip if parent hidden

            // Simple substring check (most common case)
            if (nodeText.includes(chunkText)) {
                const hl = highlightNode(node); // Highlight the node (wraps in span)
                if (hl && !firstHighlightElement) { // Track the first successfully highlighted element
                    firstHighlightElement = hl;
                }
            }
            // Consider adding fuzzy matching or partial phrase matching here if needed
        }

        // Scroll to the first found highlight if it exists and is still visible
        if (firstHighlightElement && isElementVisible(firstHighlightElement)) {
             firstHighlightElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
        }
    }

    /** Check if an element or its parent is reasonably visible */
    function isElementVisible(el) {
        if (!el) return false;
        let current = el;
        // Check visibility up the DOM tree
        while (current && current !== document.body) {
            const style = window.getComputedStyle(current);
            if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity || '1') === 0) return false;
            current = current.parentElement;
        }
        // Check if element has dimensions (might be display: contents)
        const rect = el.getBoundingClientRect();
        // Also check if parent has dimensions if element itself doesn't
        return (rect.width > 0 || rect.height > 0) || (el.parentElement ? isElementVisible(el.parentElement) : false);
    }

    /** Highlight a specific text node by wrapping it */
    function highlightNode(node) {
        // Validate node and context
         if (!node?.parentElement || node.nodeType !== Node.TEXT_NODE || node.parentElement.closest('#content-analysis-sidebar') || node.parentElement.classList.contains('content-analysis-highlight') || node.parentElement.isContentEditable) {
            return null;
         }
         try {
             const span = document.createElement('span');
             span.className = 'content-analysis-highlight';
             span.style.cssText = `background-color:${HIGHLIGHT_COLOR}; border-radius:2px; box-shadow:0 0 0 1px ${HIGHLIGHT_COLOR};`;
             // Wrap node
             node.parentNode.insertBefore(span, node);
             span.appendChild(node);
             highlightedElements.push(span); // Track the SPAN element
             return span; // Return the created span
         } catch (e) {
             console.warn("Highlight wrap failed:", node.textContent.substring(0, 50), e);
             return null;
         }
    }

    /** Remove all highlights */
    function removeHighlights() {
        // Iterate through the SPANs we created
        highlightedElements.forEach(span => {
             if (span?.parentNode && document.body.contains(span)) {
                 const textNode = span.firstChild; // The original text node should be inside
                 if (textNode) {
                     // Replace the span with its text node content
                     span.parentNode.replaceChild(textNode, span);
                 } else {
                      // If somehow the text node is gone, just remove the span
                      span.remove();
                 }
             }
        });
        highlightedElements = []; // Clear the tracking array
    }

     /** Show an error message in the sidebar results area */
    function showError(message) {
        const resultsContainer = document.getElementById('content-analysis-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = ''; // Clear previous content
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = `color:#d32f2f; padding:20px; margin:0; border:1px solid #fcc; background-color:#ffebee; border-radius:4px; text-align:center;`;
            errorDiv.innerHTML = `<div style="font-weight:bold; margin-bottom:10px; font-size:16px;">Error</div><div>${message}</div>`;
            resultsContainer.appendChild(errorDiv);
        }
        // Reset processing flags on error display
        isProcessingInitial = false;
        activeAsyncTaskCount = 0;
        updateMiniIndicatorState(); // Update indicator to show default state or hide
    }

    /** Get all non-empty text nodes within an element, skipping script/style/sidebar/noscrpit/editable */
    function getAllTextNodes(element) {
        const textNodes = [];
        // NodeFilter function to skip unwanted nodes
        const filter = { acceptNode: (node) => {
            // Early exit for non-text nodes
            if (node.nodeType !== Node.TEXT_NODE || !node.nodeValue.trim()) {
                return NodeFilter.FILTER_SKIP;
            }
            // Check parents for excluded tags/IDs/attributes
            let current = node.parentElement;
            while (current && current !== document.body) {
                const tag = current.tagName.toUpperCase();
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || current.id === 'content-analysis-sidebar' || current.closest('#content-analysis-sidebar') || current.isContentEditable || current.getAttribute('aria-hidden') === 'true') {
                    return NodeFilter.FILTER_REJECT; // Reject node and subtree
                }
                current = current.parentElement;
            }
            return NodeFilter.FILTER_ACCEPT; // Accept the text node
        }};
        // Use TreeWalker with the filter
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, filter, false);
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        return textNodes;
    }

    /** Attempt to extract author */
    function getAuthor() {
        // Prioritize specific meta tags
        let author = document.querySelector('meta[name="author"]')?.content || document.querySelector('meta[property="article:author"]')?.content || document.querySelector('meta[property="og:author"]')?.content; if (author) return author.trim();
        // Schema.org Person name
        author = document.querySelector('[itemtype*="schema.org/Person"] [itemprop="name"]')?.textContent; if(author) return author.trim();
        // Common class patterns (simplified)
        author = document.querySelector('.author .fn, .author .vcard .fn, .byline .author, .post-author, .article-author .author-name, a[rel="author"]')?.textContent; if (author) return author.replace(/^(by|von)\s+/i, '').trim();
        return null;
    }

    /** Attempt to extract published date */
    function getPublishedDate() {
        // Prioritize specific meta tags
        let date = document.querySelector('meta[property="article:published_time"]')?.content ||
                   document.querySelector('meta[name="datePublished"]')?.content ||
                   document.querySelector('meta[property="og:published_time"]')?.content ||
                   document.querySelector('meta[name="dc.date.issued"]')?.content;
        if (date) return date.trim();

        // Schema.org itemprop
        let el = document.querySelector('[itemprop="datePublished"]');
        if (el) return el.content || el.getAttribute('datetime') || el.textContent.trim();

        // <time> element with datetime and hints
        el = document.querySelector('time[datetime][pubdate], time[datetime].published, time[datetime].date');
        if (el) return el.getAttribute('datetime')?.trim() || el.textContent.trim();

        // Fallback: First <time> element with datetime
        el = document.querySelector('time[datetime]');
        if (el) return el.getAttribute('datetime')?.trim() || el.textContent.trim();

        // Fallback: Common date classes
        date = document.querySelector('.published, .post-date, .entry-date')?.textContent;
        if (date) return date.trim();

        return null;
    }

    /** Get color for score visualization */
    function getScoreColor(score) { const s = Math.max(0, Math.min(1, score)); let r, g, b; if (s < 0.5) { r = 255; g = Math.round(255 * (s * 2)); b = 0; } else { r = Math.round(255 * (1 - (s - 0.5) * 2)); g = 255; b = 0; } return `rgb(${r}, ${g}, ${b})`; }

     /** Add a domain to custom URLs list */
     function addDomainToCustomUrls(url) {
         const urlList = document.getElementById('custom-url-list'); if (!urlList) return;
         try {
            const domain = extractDomain(url); if (!domain) { console.warn("Add failed: Invalid domain for", url); return; }
            // Check for visual duplicates
            if (Array.from(urlList.querySelectorAll('.custom-url-item span')).some(span => span.textContent === domain)) { /* console.log("Skip adding duplicate:", domain); */ return; }
            urlList.querySelector('div[style*="no custom sources"]')?.remove(); // Clear empty message
            const urlItem = createUrlListItem(domain, url); urlList.appendChild(urlItem); // Add new item
            saveCustomUrls(); updateAllSourceButtons(); // Save and update UI
         } catch(e) { console.error("Error adding domain:", e); }
     }

    /** Remove a custom URL from the list */
    function removeCustomUrl(url) {
        const urlList = document.getElementById('custom-url-list'); if (!urlList) return;
         try {
            const domainToRemove = extractDomain(url); if (!domainToRemove) { console.warn("Remove failed: Invalid domain for", url); return; }
            let itemRemoved = false;
            urlList.querySelectorAll('.custom-url-item').forEach(item => { if (item.querySelector('span')?.textContent === domainToRemove) { item.remove(); itemRemoved = true; } });
            if (itemRemoved) {
                 if (urlList.children.length === 0) { /* Show empty message */ urlList.innerHTML = '<div style="font-size:11px; color:#888; text-align:center; padding: 5px 0;"><i>No custom sources saved.</i></div>'; }
                 saveCustomUrls(); updateAllSourceButtons(); // Save and update UI
            }
         } catch (e) { console.error("Error removing domain:", e); }
    }

    /** Helper to create a list item element for the custom URL list */
    function createUrlListItem(domain, fullUrl) {
        const item = document.createElement('div'); item.className = 'custom-url-item'; item.style.cssText = `display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px dotted #eee; font-size: 12px; line-height: 1.3;`;
        const text = document.createElement('span'); text.textContent = domain; text.style.cssText = `word-break: break-all; margin-right: 10px;`; item.appendChild(text);
        const btn = document.createElement('button'); btn.textContent = '×'; btn.title = `Remove ${domain}`; btn.style.cssText = `background: none; border: 1px solid #ccc; color: #f44336; border-radius: 50%; cursor: pointer; font-size: 12px; line-height: 1; width: 18px; height: 18px; padding: 0; flex-shrink: 0; transition: background-color 0.2s, color 0.2s;`; btn.onmouseover = () => { btn.style.backgroundColor = '#f44336'; btn.style.color = 'white'; }; btn.onmouseout = () => { btn.style.backgroundColor = 'transparent'; btn.style.color = '#f44336'; }; btn.onclick = (e) => { e.stopPropagation(); removeCustomUrl(fullUrl); }; item.appendChild(btn);
        return item;
    }


    /** Update state of ALL source buttons */
    function updateAllSourceButtons() {
        document.querySelectorAll('.source-button').forEach(button => {
             const item = button.closest('.result-item');
             if (item?.dataset.domain) { // Check dataset.domain has a value
                  const domain = item.dataset.domain;
                  const display = domain.split('.').slice(-2).join('.') || domain; // Basic display name
                  updateSourceButtonState(button, domain, display);
             } else if (item && !item.dataset.domain) {
                  button.style.display = 'none'; // Hide if domain is missing/empty
             }
        });
    }

    /** Get custom URLs from UI (returns full URLs) */
    function getCustomUrls() {
        const list = document.getElementById('custom-url-list'); if (!list) return [];
        // Get domain text, ensure it's valid, then prepend https://
        return Array.from(list.querySelectorAll('.custom-url-item span'))
            .map(span => span.textContent?.trim())
            .filter(domain => domain) // Filter out empty/null domains
            .map(domain => `https://${domain}`);
    }

    /** Save custom URLs (full URLs) to server */
    async function saveCustomUrls() {
        const urls = getCustomUrls();
        // console.log("Saving URLs:", urls); // Debugging
        try {
            const resp = await fetch(`${SERVER_BASE_URL}/api/config/urls`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ urls }) });
            if (!resp.ok) { const err = await resp.text(); console.error(`Save URLs failed (${resp.status}): ${err}`); }
        } catch (error) { console.error('Error saving URLs:', error); }
    }

    /** Load saved URLs from server and display domains */
    async function loadSavedUrls() {
        const urlList = document.getElementById('custom-url-list'); if (!urlList) return;
        try {
            const resp = await fetch(`${SERVER_BASE_URL}/api/config/urls`);
            // Clear loading message only if present and fetch call started
             if (urlList.firstChild?.textContent?.includes('Loading')) { urlList.innerHTML = ''; }

            if (!resp.ok) { const err = await resp.text(); throw new Error(`Load URLs failed ${resp.status}: ${err}`); }
            const data = await resp.json();

            // Ensure previous error messages are cleared if load succeeds now
            urlList.querySelectorAll('div[style*="color:red"]')?.forEach(el => el.remove());

            if (!data.urls?.length) { urlList.innerHTML = '<div style="font-size:11px; color:#888; text-align:center; padding: 5px 0;"><i>No custom sources saved.</i></div>'; return; }

            const uniqueDomains = new Set();
            data.urls.forEach(url => { if (!url) return; try { const domain = extractDomain(url); if (domain && !uniqueDomains.has(domain)) { uniqueDomains.add(domain); urlList.appendChild(createUrlListItem(domain, url)); } } catch(e){ console.warn("Err process saved URL:", url, e); } });
            // Show message if all saved URLs were invalid
            if (urlList.children.length === 0 && data.urls.length > 0) { urlList.innerHTML = '<div style="font-size:11px; color:#888; text-align:center; padding: 5px 0;"><i>No valid sources loaded.</i></div>'; }
            updateAllSourceButtons(); // Update any existing result buttons
        } catch (error) {
            console.error('Error loading URLs:', error);
             if (urlList.firstChild?.textContent?.includes('Loading')) { urlList.innerHTML = ''; } // Clear loading on error too
             // Display error without removing existing valid items if any
             const errorDiv = document.createElement('div'); errorDiv.style.cssText = `font-size:11px; color:red; text-align:center; padding: 5px 0;`; errorDiv.textContent = `Error loading sources: ${error.message}`; urlList.appendChild(errorDiv);
        }
    }

// Debounce function
function debounce(func, wait) { let timeout; return function(...args) { const later = () => { clearTimeout(timeout); func.apply(this, args); }; clearTimeout(timeout); timeout = setTimeout(later, wait); }; };

// Debounced resize listener
const debouncedAdjustStyles = debounce(() => { if (isSidebarVisible && document.getElementById('content-analysis-sidebar')) { storeOriginalStyles(); adjustPageForSidebar(); } }, 250);

// Start the bookmarklet
init();

})();