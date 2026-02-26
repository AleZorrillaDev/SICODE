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

    const progressContainer = document.getElementById('progressContainer');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const progressFill = document.getElementById('progressFill');
    const progressFiles = document.getElementById('progress-files');
    const progressTime = document.getElementById('progress-time');

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

    // ===== TOAST NOTIFICATIONS (Copied from DocCheck) =====
    function showToast(type, message) {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;

        const icons = {
            success: '<i class="fa-solid fa-check-circle"></i>',
            error: '<i class="fa-solid fa-times-circle"></i>',
            info: '<i class="fa-solid fa-info-circle"></i>',
            warning: '<i class="fa-solid fa-exclamation-triangle"></i>'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close"><i class="fa-solid fa-times"></i></button>
        `;

        container.appendChild(toast);

        // Auto cerrar después de 4 segundos
        const autoClose = setTimeout(() => {
            toast.classList.add("toast-exit");
            setTimeout(() => toast.remove(), 300);
        }, 4000);

        // Cerrar manualmente
        toast.querySelector(".toast-close").addEventListener("click", () => {
            clearTimeout(autoClose);
            toast.classList.add("toast-exit");
            setTimeout(() => toast.remove(), 300);
        });
    }

    // --- Folder Selection Logic (Web Explorer) ---
    const folderBreadcrumbs = document.getElementById('folder-breadcrumbs');

    function openFolderModal() {
        folderModal.style.display = 'flex';
        selectedModalPath = currentFolder || "";
        folderPathInput.value = selectedModalPath;
        loadFolders(selectedModalPath);
    }

    function closeFolderModal() {
        folderModal.style.display = 'none';
        folderList.innerHTML = '';
        folderBreadcrumbs.innerHTML = '';
    }

    function renderBreadcrumbs(path) {
        folderBreadcrumbs.innerHTML = '';
        
        // Root / Units
        const rootItem = document.createElement('div');
        rootItem.className = 'breadcrumb-item';
        rootItem.innerHTML = '<i class="fa-solid fa-hard-drive"></i> Sistema';
        rootItem.onclick = () => {
            selectedModalPath = "";
            folderPathInput.value = "";
            loadFolders("");
        };
        folderBreadcrumbs.appendChild(rootItem);

        if (!path) {
            rootItem.classList.add('active');
            return;
        }

        // Add separator
        const sep = document.createElement('span');
        sep.className = 'breadcrumb-separator';
        sep.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
        folderBreadcrumbs.appendChild(sep);

        // Split path
        const parts = path.split(/[\\/]/).filter(p => p !== "");
        let accumulatedPath = "";
        
        // Handle Windows Drive
        if (path.includes(':')) {
            accumulatedPath = path.substring(0, path.indexOf(':') + 1) + "\\";
        }

        parts.forEach((part, index) => {
            if (index === 0 && part.includes(':')) return; // handled by drive start logic if needed, but let's be more robust

            const item = document.createElement('div');
            item.className = 'breadcrumb-item';
            item.textContent = part;
            
            // Build path for this piece
            let piecePath = "";
            if (path.includes(':')) {
                // Windows
                const drive = path.substring(0, path.indexOf(':') + 1);
                const subParts = parts.slice(0, index + 1);
                // Si la primera parte es la unidad, ya está
                piecePath = drive + "\\" + parts.slice(1, index + 1).join("\\");
            } else {
                // Linux / Posix
                piecePath = "/" + parts.slice(0, index + 1).join("/");
            }

            item.onclick = () => {
                selectedModalPath = piecePath;
                folderPathInput.value = selectedModalPath;
                loadFolders(piecePath);
            };

            folderBreadcrumbs.appendChild(item);

            if (index < parts.length - 1) {
                const s = document.createElement('span');
                s.className = 'breadcrumb-separator';
                s.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
                folderBreadcrumbs.appendChild(s);
            } else {
                item.classList.add('active');
            }
        });
    }

    async function loadFolders(path) {
        renderBreadcrumbs(path);
        folderList.innerHTML = '<div style="padding: 40px; text-align: center; color: #64748b;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><br><span style="margin-top:10px; display:inline-block; font-size: 16px;">Buscando carpetas...</span></div>';
        
        try {
            const res = await fetch(`/bpsearch/list-folders?path=${encodeURIComponent(path)}`);
            const data = await res.json();
            
            if (data.error) {
                showToast('error', data.error);
                folderList.innerHTML = `<div style="color: #ef4444; padding: 20px; text-align:center; background: #fef2f2; border-radius: 8px;"><i class="fa-solid fa-circle-exclamation fa-2x"></i><br>Error: ${data.error}</div>`;
                return;
            }

            folderList.innerHTML = '';
            
            // Si hay un error de unidades vacías
            if (data.folders.length === 0 && (!path || path === "")) {
                folderList.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b; font-size: 16px;">No se encontraron discos en tu equipo.</div>';
                return;
            }

            data.folders.forEach(folder => {
                const div = document.createElement('div');
                div.className = 'folder-item';
                
                let icon = '<i class="fa-solid fa-folder"></i>';
                let displayName = folder.name;

                // Usar nombre de disco real provisto por el servidor
                if (!path || path === "") {
                    icon = '<i class="fa-solid fa-hdd"></i>';
                    div.style.borderLeft = '4px solid #64748b';
                } else {
                    div.style.borderLeft = '4px solid #0066b3';
                }

                div.innerHTML = `
                    <div style="font-size: 20px; margin-right: 12px; color: ${(!path || path === "") ? '#64748b' : '#0066b3'};">${icon}</div>
                    <div style="display: flex; flex-direction: column;">
                        <span style="font-weight: 600; font-size: 15px;">${displayName}</span>
                    </div>
                `;
                
                div.onclick = () => {
                    selectedModalPath = folder.path;
                    folderPathInput.value = selectedModalPath;
                    loadFolders(folder.path);
                };
                folderList.appendChild(div);
            });

            if (data.folders.length === 0) {
                folderList.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8; font-size: 16px;"><i class="fa-solid fa-folder-open fa-2x"></i><br><br>Esta carpeta está vacía</div>';
            }

        } catch (e) {
            folderList.innerHTML = '<div style="color: #ef4444; padding: 20px; text-align:center; font-size: 16px;">Error de conexión con el servidor</div>';
        }
    }

    btnSelectFolder.addEventListener('click', openFolderModal);
    modalClose.addEventListener('click', closeFolderModal);
    btnCancelFolder.addEventListener('click', closeFolderModal);

    btnGoPath.addEventListener('click', () => {
        const path = folderPathInput.value.trim();
        selectedModalPath = path;
        loadFolders(path);
    });

    folderPathInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const path = folderPathInput.value.trim();
            selectedModalPath = path;
            loadFolders(path);
        }
    });

    btnConfirmFolder.addEventListener('click', async () => {
        const path = folderPathInput.value.trim();
        if (!path) {
            showToast('warning', 'Selecciona o escribe una ruta');
            return;
        }

        const btnOriginalText = btnConfirmFolder.innerHTML;
        btnConfirmFolder.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validando...';
        btnConfirmFolder.disabled = true;

        try {
            const res = await fetch('/bpsearch/set-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ carpeta: path })
            });
            const data = await res.json();

            if (data.status === 'success') {
                currentFolder = data.carpeta;
                folderPathSpan.textContent = currentFolder;
                
                // Actualizar contadores si existen en el HTML
                const pdfTotalSpan = document.getElementById('pdfs-total');
                if (pdfTotalSpan) pdfTotalSpan.textContent = data.pdfs_total;
                if (pdfCountSpan) pdfCountSpan.textContent = `${data.pdfs_carpeta} PDFs`;

                btnSelectFolder.style.display = 'none';
                folderDisplay.style.display = 'block';
                
                closeFolderModal();
                showToast('success', 'Carpeta seleccionada correctamente');
            } else {
                showToast('error', data.message || 'La carpeta no es válida');
            }
        } catch (e) {
            showToast('error', 'Error al validar la carpeta');
        } finally {
            btnConfirmFolder.innerHTML = btnOriginalText;
            btnConfirmFolder.disabled = false;
        }
    });

    // --- Search Logic ---
    btnSearch.addEventListener('click', startSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startSearch();
    });

    async function startSearch() {
        if (isSearching) return;

        const palabra = searchInput.value.trim();
        if (!palabra) {
            showToast('warning', 'Ingresa una palabra para buscar');
            return;
        }

        if (!currentFolder) {
            showToast('warning', 'Selecciona una carpeta primero');
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
        progressText.textContent = 'Buscando con cuidado...';
        progressPercent.textContent = '0%';
        progressFiles.textContent = '0/0 archivos';
        progressTime.textContent = '0s transcurridos';
        
        // Enable controls instead of showing
        btnPause.disabled = false;
        btnCancel.disabled = false;
        btnPause.innerHTML = '<i class="fa-solid fa-pause"></i> Pausar';

        isSearching = true;
        isPaused = false;

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
                showToast('error', data.message || 'Error iniciando búsqueda');
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
            showToast('error', 'Error iniciando búsqueda: ' + e.message);
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
        progressFiles.textContent = `${data.current}/${data.total} archivos`;
        progressTime.textContent = `${data.tiempo_transcurrido}s transcurridos`;
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
        showToast('success', `Búsqueda completada. ${data.encontrados} encontrados.`);

        if (data.encontrados > 0) {
            exportSection.style.display = 'block';
        }
    }

    function cancelSearchUI() {
        stopSearchUI(false);
        progressText.textContent = "Cancelado por el usuario";
        progressContainer.classList.add('error');
        showToast('info', 'Búsqueda cancelada');
    }

    function stopSearchUI(completed) {
        isSearching = false;
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        
        // Disable controls instead of hiding
        btnPause.disabled = true;
        btnCancel.disabled = true;
        
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
            btnPause.innerHTML = '<i class="fa-solid fa-play"></i> Reanudar';
            progressText.textContent = "Búsqueda pausada";
            progressContainer.classList.remove('processing');
        } else {
            btnPause.innerHTML = '<i class="fa-solid fa-pause"></i> Pausar';
            progressText.textContent = "Continuando búsqueda...";
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
    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', async (e) => {
            e.preventDefault();
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
    }
});
