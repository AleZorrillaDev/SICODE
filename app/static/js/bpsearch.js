// BPSearch - Logic

document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const btnSelectFolder = document.getElementById('btn-select-folder');
    // We toggle display of this container
    const folderDisplay = document.getElementById('folder-display');
    const folderPathSpan = document.getElementById('folder-path');

    // progress details hidden by default but updated
    const pdfCountSpan = document.getElementById('pdf-count') || { textContent: '' }; // Fallback mainly

    const searchInput = document.getElementById('search-input');
    const btnSearch = document.getElementById('btn-search');

    // Pills logic replaced chkSubcarpetas
    const pillActual = document.getElementById('pill-actual');
    const pillSubcarpetas = document.getElementById('pill-subcarpetas');

    const chkIgnorarHistorial = document.getElementById('chk-ignorar-historial');
    const btnClearHistory = document.getElementById('btn-clear-history');

    const progressContainer = document.getElementById('progressContainer');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const progressFill = document.getElementById('progressFill');
    const progressFiles = document.getElementById('progress-files');
    const progressTime = document.getElementById('progress-time');

    const searchControls = document.getElementById('search-controls');
    const btnPause = document.getElementById('btn-pause');
    const btnCancel = document.getElementById('btn-cancel');

    // Results logic (List Container)
    const resultsCount = document.getElementById('results-count');
    const resultsList = document.getElementById('results-list');

    const exportSection = document.getElementById('export-section');
    const btnExportPdf = document.getElementById('btn-export-pdf');
    const btnExportExcel = document.getElementById('btn-export-excel');
    const btnExportTxt = document.getElementById('btn-export-txt');

    // Modal
    const folderModal = document.getElementById('folder-modal');
    const modalClose = document.getElementById('modal-close');
    const btnCancelFolder = document.getElementById('btn-cancel-folder');
    const btnConfirmFolder = document.getElementById('btn-confirm-folder');
    const folderPathInput = document.getElementById('folder-path-input');
    const btnGoPath = document.getElementById('btn-go-path');
    const folderList = document.getElementById('folder-list');

    // --- State ---
    let currentFolder = "";
    let isSearching = false;
    let isPaused = false;
    let eventSource = null;
    let selectedModalPath = "";

    // --- Toast Notification ---
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Trigger reflow
        toast.offsetHeight;

        // Show
        setTimeout(() => toast.classList.add('show'), 10);

        // Hide after 3s
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- Folder Selection Logic (Native) ---
    btnSelectFolder.addEventListener('click', async () => {
        const originalText = btnSelectFolder.innerHTML;
        // Visual feedback
        btnSelectFolder.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Abriendo...';
        btnSelectFolder.disabled = true;

        try {
            const res = await fetch('/bpsearch/select-folder-dialog');
            const data = await res.json();

            if (data.status === 'success') {
                currentFolder = data.carpeta;
                folderPathSpan.textContent = currentFolder;
                pdfCountSpan.textContent = `${data.pdfs_carpeta} PDFs`;

                // Show info
                btnSelectFolder.style.display = 'none';
                folderDisplay.style.display = 'block';

                showToast('Carpeta seleccionada correctamente', 'success');
            } else if (data.status === 'cancelled') {
                showToast('Selección cancelada', 'info');
            } else {
                showToast(data.message || 'Error seleccionando carpeta', 'error');
            }
        } catch (e) {
            showToast('Error de comunicación con el servidor', 'error');
        } finally {
            btnSelectFolder.innerHTML = originalText;
            btnSelectFolder.disabled = false;
        }
    });

    // Modal logic removed as per user request
    /* 
    modalClose.addEventListener('click', closeFolderModal);
    btnCancelFolder.addEventListener('click', closeFolderModal); 
    ... (rest of modal logic commented out if needed later, or deleted)
    */

    // --- Search Logic ---
    btnSearch.addEventListener('click', startSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startSearch();
    });

    async function startSearch() {
        if (isSearching) return;

        const palabra = searchInput.value.trim();
        if (!palabra) {
            showToast('Ingresa una palabra para buscar', 'warning');
            return;
        }

        if (!currentFolder) {
            showToast('Selecciona una carpeta primero', 'warning');
            return;
        }

        // Determine mode from pills
        const incluirSubcarpetas = pillSubcarpetas.classList.contains('active');

        // Reset UI
        resultsList.innerHTML = '';
        resultsCount.textContent = '0';
        progressContainer.classList.remove('completed', 'error');
        progressContainer.classList.add('processing');
        progressFill.style.width = '0%';
        progressText.textContent = 'Iniciando...';
        progressPercent.textContent = '0%';
        searchControls.style.display = 'flex';
        exportSection.style.display = 'none';

        isSearching = true;
        isPaused = false;
        btnPause.innerHTML = 'Pausar';

        try {
            // Trigger search start
            const res = await fetch('/bpsearch/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carpeta: currentFolder,
                    palabra: palabra,
                    incluir_subcarpetas: incluirSubcarpetas,
                    ignorar_historial: chkIgnorarHistorial.checked
                })
            });

            const data = await res.json();
            if (data.status !== 'started') {
                showToast(data.message || 'Error iniciando búsqueda', 'error');
                isSearching = false;
                return;
            }

            // Connect to SSE
            if (eventSource) eventSource.close();
            eventSource = new EventSource('/bpsearch/search-stream');

            eventSource.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                handleSearchEvent(msg);
            };

            eventSource.onerror = () => {
                if (isSearching) {
                    // Don't toast on clean close, but here likely error
                    // showToast('Conexión perdida con el servidor', 'error');
                    // stopSearchUI(false);
                }
                eventSource.close();
            };

        } catch (e) {
            showToast('Error iniciando búsqueda: ' + e.message, 'error');
            isSearching = false;
        }
    }

    function handleSearchEvent(msg) {
        if (msg.type === 'progress') {
            updateProgress(msg);
        } else if (msg.type === 'found') {
            addResult(msg);
        } else if (msg.type === 'complete') {
            finishSearch(msg);
        } else if (msg.type === 'cancelled') {
            cancelSearchUI();
        } else if (msg.type === 'error') {
            console.error(msg.error);
        }
    }

    function updateProgress(data) {
        const pct = data.percent;
        progressFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
        progressText.textContent = `Procesando: ${data.archivo}`;
        progressFiles.textContent = `${data.current}/${data.total}`;
        progressTime.textContent = `${data.tiempo_transcurrido}s`;
    }

    function addResult(data) {
        const div = document.createElement('div');
        div.className = 'result-item'; // CSS handles this

        div.innerHTML = `
            <div class="result-item-title">${data.archivo}</div>
            <div class="result-item-details">
                <span class="result-highlight">${data.veces} coincidencias</span> 
                | Pág: ${data.paginas.join(', ')}
            </div>
        `;
        resultsList.appendChild(div);

        // Update count
        const currentCount = parseInt(resultsCount.textContent) || 0;
        resultsCount.textContent = `${currentCount + 1}`;
    }

    function finishSearch(data) {
        stopSearchUI(true);
        progressText.textContent = data.message;
        progressPercent.textContent = "100%";
        progressFill.style.width = "100%";
        showToast(`Búsqueda completada. ${data.encontrados} encontrados.`, 'success');

        if (data.encontrados > 0) {
            exportSection.style.display = 'block';
        }
    }

    function cancelSearchUI() {
        stopSearchUI(false);
        progressText.textContent = "Cancelado por el usuario";
        progressContainer.classList.add('error');
        showToast('Búsqueda cancelada', 'info');
    }

    function stopSearchUI(completed) {
        isSearching = false;
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        searchControls.style.display = 'none';
        progressContainer.classList.remove('processing');
        if (completed) progressContainer.classList.add('completed');
    }

    // --- Controls ---
    btnPause.addEventListener('click', async () => {
        if (!isSearching) return;

        const url = isPaused ? '/bpsearch/resume' : '/bpsearch/pause';
        await fetch(url, { method: 'POST' });

        isPaused = !isPaused;
        if (isPaused) {
            btnPause.textContent = 'Reanudar';
            progressText.textContent = "Pausado...";
            progressContainer.classList.remove('processing');
        } else {
            btnPause.textContent = 'Pausar';
            progressContainer.classList.add('processing');
        }
    });

    btnCancel.addEventListener('click', async () => {
        if (!isSearching) return;
        await fetch('/bpsearch/cancel', { method: 'POST' });
    });

    // --- Exports ---
    const getSearchWord = () => searchInput.value.trim() || "busqueda";

    btnExportPdf.addEventListener('click', () => {
        window.location.href = `/bpsearch/export/pdf?palabra=${encodeURIComponent(getSearchWord())}`;
    });

    btnExportExcel.addEventListener('click', () => {
        window.location.href = `/bpsearch/export/excel?palabra=${encodeURIComponent(getSearchWord())}`;
    });

    btnExportTxt.addEventListener('click', () => {
        window.location.href = `/bpsearch/export/txt?palabra=${encodeURIComponent(getSearchWord())}`;
    });

    // --- Clear History ---
    btnClearHistory.addEventListener('click', async () => {
        const palabra = searchInput.value.trim();
        if (!palabra) {
            showToast('Ingresa una palabra para borrar su historial', 'warning');
            return;
        }

        if (!currentFolder) {
            showToast('Selecciona una carpeta primero', 'warning');
            return;
        }

        if (confirm(`¿Seguro que deseas borrar el historial de búsqueda para "${palabra}"?`)) {
            try {
                const res = await fetch('/bpsearch/clear-history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ palabra: palabra })
                });
                const data = await res.json();
                showToast(data.message, data.status === 'success' ? 'success' : 'info');
            } catch (e) {
                showToast('Error al borrar historial', 'error');
            }
        }
    });
});
