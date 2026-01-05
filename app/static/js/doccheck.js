document.addEventListener("DOMContentLoaded", () => {
    let currentIdx = 0;
    let totalRecords = 0;

    // Referencias a elementos
    const btnUpload = document.getElementById("btn-upload");
    const fileInput = document.getElementById("file-upload");
    const btnSave = document.getElementById("btn-save");
    const btnPrev = document.getElementById("btn-prev");
    const btnNext = document.getElementById("btn-next");
    const btnExpExcel = document.getElementById("btn-export-excel");
    const btnExpTxt = document.getElementById("btn-export-txt");
    const btnConsultar = document.querySelector(".btn-consultar");

    // ===== CARGAR ARCHIVO EXCEL =====
    if (btnUpload && fileInput) {
        btnUpload.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", async () => {
            if (!fileInput.files.length) return;
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            try {
                const resp = await fetch("/doccheck/upload", { method: "POST", body: formData });
                const data = await resp.json();
                if (data.status === "success") {
                    totalRecords = data.count;
                    showModal("success", `¡Archivo cargado!\nTotal registros: ${data.count}`);
                    currentIdx = 0;
                    loadRecord(currentIdx);
                    updateNavButtons();
                } else {
                    showModal("error", "Error: " + data.error);
                }
            } catch (e) {
                showModal("error", "Error de red al cargar archivo");
            }
        });
    }

    // ===== NAVEGACIÓN =====
    if (btnPrev) {
        btnPrev.addEventListener("click", () => {
            if (currentIdx > 0) {
                currentIdx--;
                loadRecord(currentIdx);
                updateNavButtons();
            }
        });
    }

    if (btnNext) {
        btnNext.addEventListener("click", () => {
            if (currentIdx < totalRecords - 1) {
                currentIdx++;
                loadRecord(currentIdx);
                updateNavButtons();
            }
        });
    }

    function updateNavButtons() {
        if (btnPrev) {
            btnPrev.disabled = currentIdx <= 0;
            btnPrev.style.opacity = currentIdx <= 0 ? "0.5" : "1";
        }
        if (btnNext) {
            btnNext.disabled = currentIdx >= totalRecords - 1;
            btnNext.style.opacity = currentIdx >= totalRecords - 1 ? "0.5" : "1";
        }
    }

    // ===== IR A REGISTRO ESPECÍFICO =====
    const recordIdxInput = document.getElementById("record-idx");
    if (recordIdxInput) {
        recordIdxInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                const searchValue = recordIdxInput.value.trim();

                if (!searchValue) {
                    showModal("info", "Ingresa un número de registro");
                    return;
                }

                if (totalRecords === 0) {
                    showModal("info", "Primero carga un archivo Excel");
                    return;
                }

                // Usar el número como posición (1-based → convertir a 0-based)
                const idx = parseInt(searchValue) - 1;

                if (!isNaN(idx) && idx >= 0 && idx < totalRecords) {
                    currentIdx = idx;
                    loadRecord(currentIdx);
                    updateNavButtons();
                    console.log(`Navegando a registro ${idx + 1} de ${totalRecords}`);
                } else {
                    showModal("error", `Registro ${searchValue} no existe.\nRango válido: 1 - ${totalRecords}`);
                }
            }
        });
    }

    // ===== GUARDAR REGISTRO =====
    if (btnSave) {
        btnSave.addEventListener("click", async () => {
            const formData = new FormData();
            const fieldMap = {
                "field-folios": "Folios",
                "field-tipo-doc": "Tipo Doc",
                "field-num-doc": "N° Documento",
                "field-razon": "Razón Social",
                "field-ruc": "RUC",
                "field-fecha": "Fecha Extrema",
                "field-obs": "Observaciones",
                "field-x1": "X1",
                "field-x2": "X2",
                "field-x3": "X3",
            };
            for (const [id, key] of Object.entries(fieldMap)) {
                const el = document.getElementById(id);
                if (el) formData.append(key, el.value);
            }
            try {
                const resp = await fetch(`/doccheck/save/${currentIdx}`, { method: "POST", body: formData });
                const res = await resp.json();
                if (res.status === "success") {
                    showModal("success", "Datos guardados correctamente");
                } else {
                    showModal("error", "Error: " + res.error);
                }
            } catch (e) {
                showModal("error", "Error de red al guardar");
            }
        });
    }

    // ===== CONSULTAR RUC =====
    if (btnConsultar) {
        btnConsultar.addEventListener("click", () => {
            const rucField = document.getElementById("field-ruc");
            const ruc = rucField ? rucField.value.trim() : "";

            const URL_CONSULTA = "http://intranet/cl-ti-iaconsruc/jcrS01Alias";

            if (!ruc) {
                showModal("info", "Validar número RUC\n\nNo hay RUC ingresado.");
                // Abrir la URL de consulta
                window.open(URL_CONSULTA, "_blank");
            } else {
                // Copiar RUC al portapapeles
                navigator.clipboard.writeText(ruc).then(() => {
                    showModal("success", `RUC copiado: ${ruc}\n\nSe abrirá la página de consulta.`);
                    window.open(URL_CONSULTA, "_blank");
                }).catch(() => {
                    // Fallback si no hay clipboard API
                    showModal("info", `RUC: ${ruc}\n\nCopia manualmente y consulta.`);
                    window.open(URL_CONSULTA, "_blank");
                });
            }
        });
    }

    // ===== EXPORTAR =====
    if (btnExpExcel) {
        btnExpExcel.addEventListener("click", () => {
            if (totalRecords === 0) {
                showModal("info", "Primero carga un archivo Excel");
                return;
            }
            showExportModal("excel");
        });
    }

    if (btnExpTxt) {
        btnExpTxt.addEventListener("click", () => {
            if (totalRecords === 0) {
                showModal("info", "Primero carga un archivo Excel");
                return;
            }
            showExportModal("txt");
        });
    }

    // ===== MODAL DE EXPORTACIÓN =====
    function showExportModal(formato) {
        // Crear modal de exportación
        const overlay = document.createElement("div");
        overlay.className = "export-overlay";
        overlay.innerHTML = `
            <div class="export-modal">
                <h3>Exportar a ${formato.toUpperCase()}</h3>
                <div class="export-options">
                    <label class="export-option">
                        <input type="radio" name="export-type" value="todo" checked>
                        <span>Exportar TODO</span>
                    </label>
                    <label class="export-option">
                        <input type="radio" name="export-type" value="caja">
                        <span>Por N° de Caja:</span>
                        <input type="text" id="export-caja-input" placeholder="N° Caja" disabled>
                    </label>
                </div>
                <div class="export-actions">
                    <button class="btn-export-cancel">Cancelar</button>
                    <button class="btn-export-confirm">Exportar</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Event listeners
        const radios = overlay.querySelectorAll('input[name="export-type"]');
        const cajaInput = overlay.querySelector("#export-caja-input");

        radios.forEach(radio => {
            radio.addEventListener("change", () => {
                cajaInput.disabled = radio.value !== "caja";
                if (radio.value === "caja") cajaInput.focus();
            });
        });

        overlay.querySelector(".btn-export-cancel").addEventListener("click", () => {
            overlay.remove();
        });

        overlay.querySelector(".btn-export-confirm").addEventListener("click", () => {
            const selected = overlay.querySelector('input[name="export-type"]:checked').value;
            let url = `/doccheck/export/${formato}`;

            if (selected === "caja") {
                const cajaVal = cajaInput.value.trim();
                if (!cajaVal) {
                    showModal("info", "Ingresa el N° de Caja");
                    return;
                }
                url += `?caja=${encodeURIComponent(cajaVal)}`;
            }

            window.location.href = url;
            overlay.remove();
        });

        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) overlay.remove();
        });
    }

    // ===== CARGAR REGISTRO =====
    async function loadRecord(idx) {
        try {
            const resp = await fetch(`/doccheck/record/${idx}`);
            const res = await resp.json();
            if (res.status === "success") {
                const d = res.data;
                const setVal = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) el.value = val || "";
                };
                setVal("record-idx", d["N° Registro"]);
                setVal("field-paquete", d["Paquete"]);
                setVal("field-caja", d["Caja"]);
                setVal("field-folios", d["Folios"]);
                setVal("field-tipo-doc", d["Tipo Doc"]);
                setVal("field-num-doc", d["N° Documento"]);
                setVal("field-razon", d["Razón Social"]);
                setVal("field-ruc", d["RUC"]);
                setVal("field-fecha", d["Fecha Extrema"]);
                setVal("field-obs", d["Observaciones"]);
                setVal("field-x1", d["X1"]);
                setVal("field-x2", d["X2"]);
                setVal("field-x3", d["X3"]);
            } else if (res.error === "Index out of range") {
                // No hacer nada, ya estamos en el límite
            }
        } catch (e) {
            console.error("Error cargando registro:", e);
        }
    }

    // ===== MODAL DE MENSAJES (usa uiModal global si existe) =====
    function showModal(type, message) {
        const modal = document.getElementById("uiModal");
        const icon = document.getElementById("uiModalIcon");
        const msg = document.getElementById("uiModalMsg");
        const btn = document.getElementById("uiModalBtn");

        if (modal && icon && msg && btn) {
            // Usar el modal global
            icon.className = "uimodal-icon " + (type === "error" ? "error" : "success");
            icon.innerHTML = type === "error"
                ? '<i class="fa-solid fa-xmark"></i>'
                : '<i class="fa-solid fa-check"></i>';
            msg.textContent = message;
            modal.classList.remove("uimodal-hidden");
        } else {
            // Fallback a alert
            alert(message);
        }
    }

    // ===== ATAJOS DE TECLADO =====
    document.addEventListener("keydown", (e) => {
        // Ctrl + S = Guardar
        if (e.ctrlKey && e.key === "s") {
            e.preventDefault();
            if (btnSave) btnSave.click();
        }
        // Flechas izq/der = Navegación
        if (e.key === "ArrowLeft" && !e.target.matches("input")) {
            if (btnPrev && !btnPrev.disabled) btnPrev.click();
        }
        if (e.key === "ArrowRight" && !e.target.matches("input")) {
            if (btnNext && !btnNext.disabled) btnNext.click();
        }
    });

    // Inicializar
    loadRecord(0);
    updateNavButtons();
});
