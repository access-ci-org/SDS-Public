import { escapeHtml } from "../utils.js";
import { showAlert } from "../alerts.js";

export function createContainerDetailsTemplate(containerData, includeTitle = false) {
    const {
        container_name,
        resource,
        resource_name,
        definition_file,
        container_file,
        software,
        notes,
        command,
        container_notes
    } = containerData;

    // Use either 'resource' or 'resource_name' depending on data structure
    const resourceDisplay = resource || resource_name || 'N/A';
    const commandDisplay = command || '';
    const notesDisplay = notes || container_notes || '';
    const softwareArray = Array.isArray(software) ? software : [];
    const defFile = definition_file || '';
    const contFile = container_file || '';

    return `
        ${includeTitle ? `
        <div class="mb-3">
            <h5 class="card-title text-break">
                <i class="bi bi-boxes me-2"></i>
                ${escapeHtml(container_name || 'Unnamed Container')}
            </h5>
        </div>
        ` : ''}

        <!-- Resource Info -->
        <div class="mb-4">
            <div class="text-muted small mb-2">
                <i class="bi bi-hdd-stack-fill"></i>
                Resource
            </div>
            <div>${escapeHtml(resourceDisplay)}</div>
        </div>


        ${defFile.length > 0 ?`
            <!-- Definition File -->
            <div class="mb-4">
                <div class="text-muted small mb-2">
                    <i class="bi bi-file-earmark-code-fill"></i>
                    Definition File
                </div>
                <div class="font-monospace p-2 bg-light rounded">
                    ${defFile.startsWith("https://") || defFile.startsWith('http://') ?
                        `<a href="${escapeHtml(defFile)}" target="_blank">${escapeHtml(defFile)}</a>` :
                        escapeHtml(defFile) || '<span class="text-muted">No definition file available</span>'
                    }
                </div>
            </div>
        `: ''}

        ${contFile.length > 0 ?`
            <!-- Container File -->
            <div class="mb-4">
                <div class="text-muted small mb-2">
                    <i class="bi bi-file-earmark-binary-fill"></i>
                    Container File
                </div>
                <div class="font-monospace p-2 bg-light rounded">
                    ${contFile.startsWith("https://") || contFile.startsWith('http://') ?
                        `<a href="${escapeHtml(contFile)}" target="_blank">${escapeHtml(contFile)}</a>` :
                        escapeHtml(contFile) || '<span class="text-muted">No definition file available</span>'
                    }
                </div>
            </div>
        `: ''}

        ${commandDisplay.length > 0 ?`
            <!-- Command -->
            <div class="mb-4">
                <div class="text-muted small mb-2">
                    <i class="bi bi-code-square"></i>
                    Command
                </div>
                <div class="font-monospace p-2 bg-light rounded">
                    ${escapeHtml(commandDisplay).replace(",", "<br>") || '<span class="text-muted">No container file available</span>'}
                </div>
            </div>
        `: ''}

        ${softwareArray.length > 0 ? `
        <!-- Software Section -->
        <div class="mb-4">
            <div class="text-muted small mb-2">
                <i class="bi bi-grid-fill"></i>
                Installed Software
            </div>
            <div class="d-flex flex-wrap gap-2">
                ${softwareArray.map(sw => `
                    <span class="badge software-badge rounded-pill">${escapeHtml(sw)}</span>
                `).join('')}
            </div>
        </div>
        ` : ''}

        ${notesDisplay.length > 0 ? `
            <!-- Notes Section -->
            <div class="mt-3 pt-3 border-top">
                <div class="text-muted small mb-2">
                    <i class="bi bi-pencil-square"></i>
                    Notes
                </div>
                <div class="small p-2 bg-light rounded" style="max-height: 150px; overflow-y: auto; white-space: pre-line;">
                    ${escapeHtml(notesDisplay) || '<span class="text-muted fst-italic">No notes available</span>'}
                </div>
            </div>
        `: ''}
    `;
}

function setupToggleAccordion() {
    const toggleBtn = document.getElementById('toggleAccordions');
    let isExpanded = true; // Start with true since accordions begin expanded

    // Remove existing event listeners to prevent duplicates
    const newToggleBtn = toggleBtn.cloneNode(true);
    toggleBtn.parentNode.replaceChild(newToggleBtn, toggleBtn);

    newToggleBtn.addEventListener('click', function() {
        isExpanded = !isExpanded;
        newToggleBtn.textContent = isExpanded ? 'Hide All' : 'Show All';

        // Get all accordion elements within the container modal
        const accordionButtons = document.querySelectorAll('#container-accordion .accordion-button');
        const accordionCollapses = document.querySelectorAll('#container-accordion .accordion-collapse');

        // Toggle all accordion items
        accordionButtons.forEach(button => {
            if (isExpanded) {
                button.classList.remove('collapsed');
                button.setAttribute('aria-expanded', 'true');
            } else {
                button.classList.add('collapsed');
                button.setAttribute('aria-expanded', 'false');
            }
        });

        accordionCollapses.forEach(collapse => {
            if (isExpanded) {
                collapse.classList.add('show');
            } else {
                collapse.classList.remove('show');
            }
        });
    });
}

// Updated multi-container modal function
export function onViewContainerClick(e, table) {
    let row = table.row(e.target.closest('tr')).data();
    let softwareName = row['software_name'];

    $.ajax({
        url: "/container/" + encodeURIComponent(softwareName),
        type: "GET",
        dataType: "json",
        success: function(response) {
            // Clear previous content
            $("#container-accordion").empty();
            $("#container-modal-title").text(softwareName);

            response.forEach((containerData, index) => {
                $("#container-accordion").append(`
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="heading-${index}">
                            <button class="accordion-button" type="button" data-bs-toggle="collapse"
                                data-bs-target="#container-${index}" aria-expanded="true"
                                aria-controls="container-${index}">
                                <i class="bi bi-boxes me-2"></i>
                                <div class="flex-grow-1">
                                    ${escapeHtml(containerData['container_name'] || 'Unnamed')}
                                </div>
                                <div class="px-5">
                                    v: ${escapeHtml(containerData['software_versions'] || '')}
                                </div>
                            </button>
                        </h2>
                        <div id="container-${index}" class="accordion-collapse collapse show"
                            aria-labelledby="heading-${index}">
                            <div class="accordion-body">
                                ${createContainerDetailsTemplate(containerData)}
                            </div>
                        </div>
                    </div>
                `);
            });

            setupToggleAccordion();
            $('#container-modal').modal('show');
        },
        error: function(xhr, status, error) {
            console.error("Error: ", error);
            showAlert("Unable to load container details. Please try again.", "danger");
        }
    });
}