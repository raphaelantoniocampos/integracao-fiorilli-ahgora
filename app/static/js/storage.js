const EXPIRATION_TIME_DAYS = 5
const EXPIRATION_TIME_MS = EXPIRATION_TIME_DAYS * 24 * 60 * 60 * 1000;

// Helper functions for encryption
function str2ab(str) {
    const buf = new ArrayBuffer(str.length);
    const bufView = new Uint8Array(buf);
    for (let i = 0, strLen = str.length; i < strLen; i++) {
        bufView[i] = str.charCodeAt(i);
    }
    return buf;
}

function checkAndHandleExpiration() {
    const lastSaved = localStorage.getItem('credentials_timestamp');

    if (lastSaved) {
        const now = new Date().getTime();
        const timePassed = now - parseInt(lastSaved);

        if (timePassed > EXPIRATION_TIME_MS) {
            console.log("Credentials expired. Cleaning up...");

            const keysToClear = [
                'fiorilli_password', 'ahgora_password', 'fiorilli_user',
                'ahgora_user', 'ahgora_company', 'credentials_timestamp',
                'fiorilli_url', 'ahgora_url'
            ];

            keysToClear.forEach(key => localStorage.removeItem(key));
            return true;
        }
    }

    localStorage.setItem('credentials_timestamp', new Date().getTime().toString());
    return false;
}

async function importPublicKey(pemString) {
    const pemHeader = "-----BEGIN PUBLIC KEY-----";
    const pemFooter = "-----END PUBLIC KEY-----";
    let pemContent = pemString.substring(pemString.indexOf(pemHeader) + pemHeader.length, pemString.indexOf(pemFooter));
    pemContent = pemContent.replace(/\s/g, '');

    const binaryDerString = window.atob(pemContent);
    const binaryDer = str2ab(binaryDerString);

    try {
        return await window.crypto.subtle.importKey(
            "spki",
            binaryDer,
            {
                name: "RSA-OAEP",
                hash: "SHA-256"
            },
            true,
            ["encrypt"]
        );
    }
    catch (TypeError) {
        return false;
    }
}

async function encryptString(text, publicKey) {
    const enc = new TextEncoder();
    const encoded = enc.encode(text);
    const encrypted = await window.crypto.subtle.encrypt(
        {
            name: "RSA-OAEP"
        },
        publicKey,
        encoded
    );

    let binary = '';
    const bytes = new Uint8Array(encrypted);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

// Credential retrieval and encryption logic
async function getEncryptedCredentials() {

    const isExpired = checkAndHandleExpiration();

    const fiorilliPwd = localStorage.getItem('fiorilli_password');
    const ahgoraPwd = localStorage.getItem('ahgora_password');
    const fiorilliUser = localStorage.getItem('fiorilli_user');
    const ahgoraUser = localStorage.getItem('ahgora_user');
    const ahgoraCompany = localStorage.getItem('ahgora_company');
    const fiorilliUrl = localStorage.getItem('fiorilli_url') || '';
    const ahgoraUrl = localStorage.getItem('ahgora_url') || '';

    if (isExpired || !fiorilliPwd || !ahgoraPwd || !fiorilliUser || !ahgoraUser || !ahgoraCompany) {
        alert(isExpired ? 'Sua sessão expirou. Por favor, configure novamente.' : 'Configure suas credenciais.');
        window.location.href = '/config';
        return null;
    }

    const keysResponse = await fetch('/api/sync/public-key');
    if (!keysResponse.ok) {
        throw new Error("Falha ao obter chave pública");
    }
    const pkData = await keysResponse.json();

    const publicKey = await importPublicKey(pkData.public_key);
    if (!publicKey) {
        const currentUrl = window.location.origin;
        alert(`O seu navegador está bloqueando as APIs de criptografia porque esta conexão não é segura (HTTP).\n\nPara resolver em rede local:\n1. Acesse chrome://flags/#unsafely-treat-insecure-origin-as-secure\n2. Ative a opção e adicione: ${currentUrl}\n3. Reinicie o navegador.`);
        return null;
    }

    const encryptedFiorilli = await encryptString(fiorilliPwd, publicKey);
    const encryptedAhgora = await encryptString(ahgoraPwd, publicKey);

    return {
        fiorilli_user: fiorilliUser,
        ahgora_user: ahgoraUser,
        ahgora_company: ahgoraCompany,
        fiorilli_password: encryptedFiorilli,
        ahgora_password: encryptedAhgora,
        fiorilli_url: fiorilliUrl || null,
        ahgora_url: ahgoraUrl || null
    };
}

// Action functions
async function startSync(event) {
    const btn = event.currentTarget;
    const btnText = document.getElementById("syncBtnText");

    btn.disabled = true;
    if (btnText) btnText.innerText = "Iniciando...";

    try {
        const credentials = await getEncryptedCredentials();
        if (!credentials) return;

        const response = await fetch('/api/sync/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Falha ao iniciar sincronização");
        }

        setTimeout(() => typeof htmx !== 'undefined' && htmx.trigger('#jobs-list', 'refresh'), 500);
    } catch (error) {
        alert(error.message || "Ocorreu um erro ao iniciar a sincronização.");
        console.error(error);
    } finally {
        btn.disabled = false;
        if (btnText) btnText.innerText = "Iniciar Sincronização";
    }
}

async function executeBatch(jobId, taskType, btn) {
    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    try {
        const credentials = await getEncryptedCredentials();
        if (!credentials) {
            console.warn("No credentials found");
            // alert("DEBUG: No credentials found");
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            return;
        }

        const url = `/api/sync/tasks/batch/execute?job_id=${jobId}&task_type=${encodeURIComponent(taskType)}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Falha ao executar lote");
        }

        if (typeof htmx !== 'undefined') {
            htmx.trigger(document.body, 'refresh');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        } else {
            window.location.reload();
        }
    } catch (error) {
        alert(error.message || "Erro ao executar lote.");
        console.error(error);
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

async function executeTask(taskId, btn) {
    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    try {
        const credentials = await getEncryptedCredentials();
        if (!credentials) {
            console.warn("No credentials found");
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            return;
        }

        const response = await fetch(`/api/sync/tasks/${taskId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Falha ao executar tarefa");
        }

        if (typeof htmx !== 'undefined') {
            htmx.trigger(document.body, 'refresh');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        } else {
            window.location.reload();
        }
    } catch (error) {
        alert(error.message || "Erro ao executar tarefa.");
        console.error(error);
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

async function cancelBatch(jobId, taskType, btn) {
    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    try {
        const response = await fetch(`/api/sync/tasks/batch/cancel?job_id=${jobId}&task_type=${encodeURIComponent(taskType)}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Falha ao cancelar lote");
        }

        if (typeof htmx !== 'undefined') {
            htmx.trigger(document.body, 'refresh');
            if (btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        } else {
            window.location.reload();
        }
    } catch (error) {
        alert(error.message || "Erro ao cancelar lote.");
        console.error(error);
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

// Global exposure
window.startSync = startSync;
window.executeBatch = executeBatch;
window.executeTask = executeTask;
window.cancelBatch = cancelBatch;
