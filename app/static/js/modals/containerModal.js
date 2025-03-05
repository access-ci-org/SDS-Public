export function onViewContainerClick(e, table){
    let row = table.row(e.target.closest('tr')).data();
    let softwareName = row['software_name'];
    $.ajax({
        url: "/container/"+softwareName,
        type:"GET",
        dataType: "json",
        success: function(response){
            $("#conatiner-modal").modal('show');
            $("#container-modal-title").html(`Containers for: ${softwareName}`)
            response.forEach((value, index) => {
                $("#container-accordion").append(`
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading-${index}">
                <button class="accordion-button" type="button" data-bs-toggle="collapse"
                    data-bs-target="#container-${index}" aria-expanded="true" 
                    aria-controls="container-${index}">
                    <div class="d-flex align-items-center">
                        <i class="fa-solid fa-cube me-2"></i>
                        ${value['container_name'] || 'Unnamed'}
                    </div>
                </button>
                </h2>
                <div id="container-${index}" class="accordion-collapse collapse show"
                aria-labelledby="heading-${index}">
                <div class="accordion-body">
                <!-- Container Info -->
                <div class="mb-4">
                    <div class="text-muted small mb-2">
                        <i class="fa-solid fa-server"></i>
                        Resource
                    </div>
                    <div>${value['resource_name'] || 'N/A'}</div>
                </div>

                <!-- Definition File -->
                <div class="mb-4">
                    <div class="text-muted small mb-2">
                        <i class="fa-solid fa-file-code"></i>
                        Definition File
                    </div>
                    <div class="font-monospace p-2 bg-light rounded">
                        ${value['definition_file'] || '<span class="text-muted">No definition file available</span>'}
                    </div>
                </div>

                <!-- Container File -->
                <div class="mb-4">
                    <div class="text-muted small mb-2">
                        <i class="fa-solid fa-box"></i>
                        Container File
                    </div>
                    <div class="font-monospace p-2 bg-light rounded">
                        ${value['container_file'] || '<span class="text-muted">No container file available</span>'}
                    </div>
                </div>
                <!-- Notes -->
                <div class="mt-3 pt-3 border-top">
                    <div class="text-muted small mb-2">
                        <i class="fa-solid fa-note-sticky"></i>
                        Notes
                    </div>
                    <div class="small">
                        ${value['notes'] || '<span class="text-muted fst-italic">No notes available</span>'}
                    </div>
                </div>
            </div>
        </div>
    </div>
              `);
          });

        const toggleBtn = document.getElementById('toggleAccordions');
        let isExpanded = true; // Start with true since your accordions begin with "show" class

        toggleBtn.addEventListener('click', function() {
            isExpanded = !isExpanded;

            // Update button text
            toggleBtn.textContent = isExpanded ? 'Hide All' : 'Show All';

            // Get all accordion elements
            const accordionButtons = document.querySelectorAll('.accordion-button');
            const accordionCollapses = document.querySelectorAll('.accordion-collapse');

            // Toggle accordion items
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
          $('#container-modal').modal('show');
        }
    })
}