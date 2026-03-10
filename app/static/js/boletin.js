// Boletin - Calendar, Search and PDF Logic

document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let currentDate = new Date();
    let selectedDates = new Set(); 
    let selectionStart = null; 
    let selectionEnd = null;
    let hoverDate = null; // For previewing range
    let dataCache = {}; 
    let currentSearchTerm = "";

    // --- DOM Elements ---
    const calendarGrid = document.getElementById('calendar-grid');
    const monthDisplay = document.getElementById('current-month');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const resultsList = document.getElementById('results-list');
    const resultsCount = document.getElementById('results-count');
    const pdfViewport = document.getElementById('pdf-viewport');
    const viewControls = document.getElementById('view-controls');
    const docTitle = document.getElementById('current-document-title');
    const viewportLoader = document.getElementById('viewport-loader');
    const emptyViewer = document.getElementById('empty-viewer');
    const btnDownloadMain = document.getElementById('btn-download-main');
    const btnOpenExternal = document.getElementById('btn-open-external');
    const btnClearSelection = document.getElementById('btn-clear-selection');
    
    // Search elements
    const searchWordInput = document.getElementById('search-word');
    const btnStartSearch = document.getElementById('btn-start-search');
    const progressContainerBar = document.getElementById('search-progress-container');
    const progressBar = document.getElementById('search-progress-bar');
    const progressStatusText = document.getElementById('search-status-text');
    const progressStatusPercent = document.getElementById('search-status-percent');

    const months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

    renderCalendar();

    prevMonthBtn.onclick = () => { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(); };
    nextMonthBtn.onclick = () => { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(); };
    
    btnClearSelection.onclick = () => {
        selectedDates.clear();
        selectionStart = null;
        selectionEnd = null;
        hoverDate = null;
        resultsList.innerHTML = '<div style="text-align: center; padding: 40px 0; color: #94a3b8;"><i class="fa-solid fa-calendar-day" style="font-size: 24px; margin-bottom: 10px;"></i><p>Selecciona una fecha</p></div>';
        resultsCount.textContent = "0";
        renderCalendar();
    };

    // --- Booking.com Style Range Selection ---
    
    function initClickEvents(div, dateStr) {
        div.onclick = () => {
            if (!selectionStart || (selectionStart && selectionEnd)) {
                // Iniciar nueva selección o resetear si ya había un rango completo
                selectionStart = dateStr;
                selectionEnd = null;
                selectedDates.clear();
                selectedDates.add(dateStr);
            } else if (selectionStart && !selectionEnd) {
                // Completar el rango
                let d1 = new Date(selectionStart + "T00:00:00");
                let d2 = new Date(dateStr + "T00:00:00");
                
                if (d2 < d1) {
                    // Si seleccionó una fecha anterior, resetear inicio
                    selectionStart = dateStr;
                    selectedDates.clear();
                    selectedDates.add(dateStr);
                } else {
                    selectionEnd = dateStr;
                    selectRange(selectionStart, selectionEnd);
                    updateCumulativeResults();
                }
            }
            hoverDate = null;
            renderCalendar();
        };

        div.onmouseenter = () => {
            if (selectionStart && !selectionEnd) {
                // Mostrar preview mientras decide el final del rango
                let targetDate = new Date(dateStr + "T00:00:00");
                let startDate = new Date(selectionStart + "T00:00:00");
                
                if (targetDate >= startDate) {
                    hoverDate = dateStr;
                    updateDayHighlights();
                }
            }
        };
    }

    function selectRange(start, end) {
        selectedDates.clear();
        let d1 = new Date(start + "T00:00:00");
        let d2 = new Date(end + "T00:00:00");

        let current = new Date(d1);
        while (current <= d2) {
            const y = current.getFullYear();
            const m = String(current.getMonth() + 1).padStart(2, '0');
            const d = String(current.getDate()).padStart(2, '0');
            selectedDates.add(`${y}-${m}-${d}`);
            current.setDate(current.getDate() + 1);
        }
    }

    function updateDayHighlights() {
        const allDays = document.querySelectorAll('.calendar-day[data-date]');
        allDays.forEach(div => {
            const dateStr = div.dataset.date;
            div.classList.remove('active', 'in-range', 'range-start', 'range-end');
            
            // Lógica cuando el rango ya está cerrado
            if (selectionStart && selectionEnd) {
                if (selectedDates.has(dateStr)) {
                    div.classList.add('active');
                    if (dateStr === selectionStart) div.classList.add('range-start');
                    if (dateStr === selectionEnd) div.classList.add('range-end');
                    if (dateStr !== selectionStart && dateStr !== selectionEnd) div.classList.add('in-range');
                }
            } 
            // Lógica de Previsualización (Hover)
            else if (selectionStart && !selectionEnd) {
                if (dateStr === selectionStart) {
                    div.classList.add('active', 'range-start', 'range-end'); // Inicialmente parece un círculo solo
                }
                
                if (hoverDate) {
                    let d = new Date(dateStr + "T00:00:00");
                    let s = new Date(selectionStart + "T00:00:00");
                    let h = new Date(hoverDate + "T00:00:00");
                    
                    if (d >= s && d <= h) {
                        div.classList.add('active');
                        if (dateStr === selectionStart) {
                            div.classList.remove('range-end'); // Rompe el lado derecho
                        } else if (dateStr === hoverDate) {
                            div.classList.add('range-end');
                        } else {
                            div.classList.add('in-range');
                        }
                    }
                }
            }
        });
    }

    // --- Search Logic ---
    btnStartSearch.onclick = async () => {
        const palabra = searchWordInput.value.trim();
        if (!palabra) { showToast('warning', 'Ingresa una palabra para buscar'); return; }
        if (selectedDates.size === 0) { showToast('warning', 'Selecciona al menos un día en el calendario'); return; }

        currentSearchTerm = palabra;
        let targetPdfs = getAllSelectedPdfs();
        if (targetPdfs.length === 0) { showToast('info', 'No hay boletines disponibles en los días seleccionados'); return; }

        progressContainerBar.style.display = 'block';
        resultsList.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Buscando coincidencias...</div>';
        resultsCount.textContent = "0";

        try {
            const res = await fetch('/boletin/api/search-bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ palabra, pdfs: targetPdfs })
            });
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            resultsList.innerHTML = '';
            let foundCount = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');
                lines.forEach(line => {
                    if (!line.startsWith('data: ')) return;
                    try {
                        const event = JSON.parse(line.substring(6));
                        if (event.type === 'progress') {
                            progressBar.style.width = `${event.percent}%`;
                            progressStatusPercent.textContent = `${event.percent}%`;
                            progressStatusText.textContent = `Analizando: ${event.archivo}`;
                        } else if (event.type === 'found') {
                            foundCount++;
                            resultsCount.textContent = foundCount;
                            addSearchResult(event);
                        } else if (event.type === 'complete') {
                            progressStatusText.textContent = "Búsqueda finalizada";
                            const msg = foundCount > 0
                                ? `${foundCount} coincidencia${foundCount > 1 ? 's' : ''} encontrada${foundCount > 1 ? 's' : ''}`
                                : 'Sin coincidencias en los días seleccionados';
                            showToast(foundCount > 0 ? 'success' : 'info', msg);
                            if (foundCount === 0) resultsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #94a3b8;">No se encontraron coincidencias</div>';
                        }
                    } catch(e) {}
                });
            }
        } catch (e) {
            console.error(e);
            showToast('error', 'Error durante la búsqueda');
        }
    };

    function getAllSelectedPdfs() {
        let all = [];
        const sorted = Array.from(selectedDates).sort();
        sorted.forEach(dateKey => {
            const [y, m, d] = dateKey.split('-');
            const monthKey = `${y}-${m}`;
            const pdfs = dataCache[monthKey] || [];
            all = all.concat(pdfs.filter(p => p.dia === parseInt(d)));
        });
        return all;
    }

    function addSearchResult(event) {
        const pdfWithPages = { ...event.pdf, paginas: event.paginas };
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-info">
                <div class="result-title">${event.pdf.titulo}</div>
                <div class="result-meta"><span style="color: #ca8a04; font-weight:700;">${event.veces} coincidencias</span> | Págs: ${event.paginas.join(', ')}</div>
            </div>`;
        div.onclick = () => {
            document.querySelectorAll('.result-item').forEach(r => r.classList.remove('selected'));
            div.classList.add('selected');
            viewPdf(pdfWithPages, currentSearchTerm);
        };
        resultsList.appendChild(div);
    }

    async function renderCalendar() {
        calendarGrid.innerHTML = '';
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        monthDisplay.textContent = `${months[month]} ${year}`;

        ['D', 'L', 'M', 'M', 'J', 'V', 'S'].forEach(d => {
            const div = document.createElement('div'); div.className = 'calendar-day-head'; div.textContent = d;
            calendarGrid.appendChild(div);
        });

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        for (let i = 0; i < firstDay; i++) {
            const div = document.createElement('div'); div.className = 'calendar-day empty';
            calendarGrid.appendChild(div);
        }

        const monthKey = `${year}-${String(month + 1).padStart(2, '0')}`;
        // No bloqueamos el renderizado esperando datos, los cargamos asíncronamente
        fetchMonthData(year, month + 1).then(() => {
             // Si el mes que terminó de cargar es el actual, refrescar indicadores de datos
             if (currentDate.getFullYear() === year && currentDate.getMonth() === month) {
                 const mData = dataCache[monthKey] || [];
                 document.querySelectorAll('.calendar-day[data-date]').forEach(d => {
                     const day = parseInt(d.textContent);
                     if (mData.some(p => p.dia === day)) d.classList.add('has-data');
                 });
             }
        });

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const div = document.createElement('div');
            div.className = 'calendar-day';
            div.textContent = day;
            div.dataset.date = dateStr;
            
            initClickEvents(div, dateStr);
            
            const today = new Date();
            if (today.getFullYear() === year && today.getMonth() === month && today.getDate() === day) div.classList.add('today');

            calendarGrid.appendChild(div);
        }
        
        // Aplicar estado visual inicial al renderizar el mes
        updateDayHighlights();
    }

    function updateCumulativeResults() {
        if (selectedDates.size === 0) {
            resultsList.innerHTML = '<div style="text-align: center; padding: 40px 0; color: #94a3b8;"><i class="fa-solid fa-calendar-day" style="font-size: 24px; margin-bottom: 10px;"></i><p>Selecciona una fecha</p></div>';
            resultsCount.textContent = "0";
            return;
        }
        let allPdfs = getAllSelectedPdfs();
        resultsList.innerHTML = '';
        resultsCount.textContent = allPdfs.length;
        if (allPdfs.length === 0) {
            resultsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #94a3b8;">No hay boletines en estos días</div>';
            return;
        }
        allPdfs.forEach(pdf => {
            const div = document.createElement('div');
            div.className = 'result-item';
            div.innerHTML = `<div class="result-info"><div class="result-title">${pdf.titulo}</div><div class="result-meta">Boletín Oficial | ${pdf.fecha}</div></div>`;
            div.onclick = () => {
                document.querySelectorAll('.result-item').forEach(r => r.classList.remove('selected'));
                div.classList.add('selected');
                viewPdf(pdf);
            };
            resultsList.appendChild(div);
        });
    }

    async function fetchMonthData(year, month) {
        const monthStr = String(month).padStart(2, '0');
        const mk = `${year}-${monthStr}`;
        if (dataCache[mk]) return;
        try {
            const res = await fetch(`/boletin/api/calendar?anio=${year}&mes=${monthStr}`);
            const data = await res.json();
            if (data.status === 'success') dataCache[mk] = data.data;
        } catch (e) {}
    }

    function viewPdf(pdf, term = "") {
        emptyViewer.style.display = 'none';
        viewportLoader.style.display = 'flex';
        viewControls.style.display = 'none';
        docTitle.textContent = pdf.titulo;
        const existing = pdfViewport.querySelector('iframe');
        if (existing) existing.remove();
        const iframe = document.createElement('iframe');
        let viewerUrl = `/boletin/api/view?url=${encodeURIComponent(pdf.url_online)}&fecha=${pdf.fecha}&titulo=${encodeURIComponent(pdf.titulo)}`;
        if (term) viewerUrl += `&highlight=${encodeURIComponent(term)}`;
        let fragment = "";
        if (pdf.paginas && pdf.paginas.length > 0) fragment = `#page=${pdf.paginas[0]}`;
        else if (term) fragment = `#search="${encodeURIComponent(term)}"`;
        iframe.src = viewerUrl + fragment;
        iframe.onload = () => { viewportLoader.style.display = 'none'; viewControls.style.display = 'flex'; };
        btnDownloadMain.onclick = () => {
            window.location.href = `/boletin/api/download?url=${encodeURIComponent(pdf.url_online)}&fecha=${pdf.fecha}&titulo=${encodeURIComponent(pdf.titulo)}`;
            showToast('info', 'Descargando boletín...');
        };
        btnOpenExternal.onclick = () => {
            window.open(pdf.url_online, '_blank');
            showToast('info', 'Abriendo en nueva pestaña...');
        };
        pdfViewport.appendChild(iframe);
    }

    function showToast(type, message) {
        if (window.showToast) {
            window.showToast(message, type);
        }
    }

});
