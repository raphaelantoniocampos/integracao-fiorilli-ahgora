/**
 * UI and Logic for the Configuration page
 */

function showTab(tabId, btn) {
    // Toggle tabs visibility
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    const targetTab = document.getElementById('tab-' + tabId);
    if (targetTab) {
        targetTab.classList.add('active');
    }

    // Toggle active button style
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    if (btn) {
        btn.classList.add('active');
    }

    // Update URL hash without scroll
    history.replaceState(null, null, ' ' + window.location.pathname + '#' + tabId);
}

/**
 * Initializes the configuration page state
 * @param {Object} options - State options from the server
 */
async function initConfig(options = {}) {
    const hash = window.location.hash.substring(1);

    // Auto-select tab based on hash or errors
    if (options.hasPasswordError || options.hasPasswordSuccess || window.location.pathname === '/change-password') {
        const btn = document.querySelector('a[href="#password"]');
        if (btn) showTab('password', btn);
    } else if (options.hasCreateUserError || options.hasCreateUserSuccess || window.location.pathname === '/create-user') {
        const btn = document.querySelector('a[href="#create-user"]');
        if (btn) showTab('create-user', btn);
    } else if (hash) {
        const btn = document.querySelector(`a[href="#${hash}"]`);
        if (btn) showTab(hash, btn);
    }
}
