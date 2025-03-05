const containers = JSON.parse(container_data);

function createContainerCard(container) {
    return `
        <div class="col-12">
            <div class="card container-card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h5 class="card-title text-break">${container.container_name}</h5>
                            <div class="text-muted small mb-2">
                                <i class="fa-solid fa-server"></i>
                                ${container.resource}
                            </div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <div class="text-muted small mb-2">
                            <i class="fa-solid fa-cube"></i>
                            Installed Software
                        </div>
                        <div class="d-flex flex-wrap gap-2">
                            ${container.software.map(sw => `
                                <span class="badge software-badge rounded-pill">${sw}</span>
                            `).join('')}
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-top">
                        <button class="btn btn-link btn-sm p-0 text-decoration-none view-details" data-container-name="${container.container_name}" data-resource-name="${container.resource}">
                            View Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function addSearchTerm(term) {
    if (term && !activeSearchTerms.has(term)) {
        activeSearchTerms.add(term);
        tagContainer.appendChild(createTag(term));
        searchInput.value = '';
        filterContainers();
    }
}

function removeSearchTerm(term) {
    activeSearchTerms.delete(term);
    renderTags();
    filterContainers();
}

function createTag(term) {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.innerHTML = `
        ${term}
        <span class="tag-close">
            <svg viewBox="0 0 24 24" width="12" height="12">
                <path stroke="currentColor" stroke-width="2" d="M18 6L6 18M6 6l12 12"/>
            </svg>
        </span>
    `;
    // Add event listener to the close button
    const closeButton = tag.querySelector('.tag-close');
    closeButton.addEventListener('click', () => removeSearchTerm(term));
    return tag;
}

function renderTags() {
    tagContainer.innerHTML = '';
    activeSearchTerms.forEach(term => {
        tagContainer.appendChild(createTag(term));
    });
}

function filterContainers() {
    const searchTerms = activeSearchTerms.size > 0 
        ? Array.from(activeSearchTerms)
        : searchInput.value.toLowerCase().split(' ').filter(term => term);

    const selectedResource = resourceSelect.value;
    const filtered = containers.filter(container => {
        const matchesSearch = searchTerms.every(term =>
            container.container_name.toLowerCase().includes(term) ||
            container.software.some(sw => sw.toString().toLowerCase().includes(term))
        );
        const matchesResource = selectedResource === 'all' || container.resource === selectedResource;
        return matchesSearch && matchesResource;
    });

    containerGrid.innerHTML = filtered.map(createContainerCard).join('');
}

const searchInput = document.getElementById('searchInput');
const tagContainer = document.getElementById('tagContainer');
const resourceSelect = document.getElementById('resourceSelect');
const containerGrid = document.getElementById('containerGrid');
// const viewDetails = document.getElementsByClassName('')
const activeSearchTerms = new Set();

searchInput.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && searchInput.value.trim()) {
        e.preventDefault();
        addSearchTerm(searchInput.value.trim().toLowerCase());
    } else if (e.key === 'Backspace' && !searchInput.value && activeSearchTerms.size > 0) {
        const lastTerm = Array.from(activeSearchTerms).pop();
        removeSearchTerm(lastTerm);
    }
});

searchInput.addEventListener('input', filterContainers);
resourceSelect.addEventListener('change', filterContainers);

// Get the modal element
const modalElement = document.getElementById('containerDetailsModal');
let containerDetailsModal;

// Initialize the modal only after document is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    containerDetailsModal = new bootstrap.Modal(modalElement);
});

// Setup event listner for view details button
document.addEventListener('click', async(e) => {
    if (e.target.matches('.view-details')){
        const containerName = e.target.dataset.containerName;
        const resourceName = e.target.dataset.resourceName;
        $.ajax({
            url: "/container_details",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                containerName: containerName,
                resourceName: resourceName
            }),
            success: function(response){
                // Update modal content
                document.getElementById('modalContainerName').textContent = response.container_name;
                document.getElementById('modalResource').textContent = response.resource;
                document.getElementById('modalDefinitionFile').textContent = response.definition_file;

                // Update software list - reusing the same badge style from container cards
                const softwareList = document.getElementById('modalSoftwareList');
                softwareList.innerHTML = response.software
                    .map(sw => `<span class="badge software-badge rounded-pill">${sw}</span>`)
                    .join('');

                // Optional fields - Definition File
                const defFileElement = document.getElementById('modalDefinitionFile');
                if (response.definition_file) {
                    defFileElement.textContent = response.definition_file;
                    defFileElement.classList.remove('text-muted');
                } else {
                    defFileElement.innerHTML = '<span class="text-muted">No definition file available</span>';
                }

                // Optional fields - Container File
                const containerFileElement = document.getElementById('modalContainerFile');
                if (response.container_file) {
                    containerFileElement.textContent = response.container_file;
                    containerFileElement.classList.remove('text-muted');
                } else {
                    containerFileElement.innerHTML = '<span class="text-muted">No container file available</span>';
                }

                // Update notes
                const notesElement = document.getElementById('modalContainerNotes');
                notesElement.textContent = response.container_notes || 'No notes available';

                // Show the modal
                containerDetailsModal.show()
            },
            error: function(xhr, status, error){
                console.error("Error: ", error)
            }
        })
    }
})

// Initial render
filterContainers();