import { showAlert } from "./alerts.js"

$(".form-check-input").change(function(){

    let column = $(this).attr('id');
    $.ajax({
        url:"/update_col_visibility/"+column,
        type: 'POST',
        success: function(response){
            showAlert('Column successfully updated', 'success');
        },
        error: function(xhr, status, error){
            console.error("Error updating column")
            showAlert("Error updating column", 'danger')
        }
    })
})
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('draggable-container');
    const draggableRows = document.querySelectorAll('.draggable-row');
    let draggingElement = null;

    // Create and insert points between rows
    function createInsertionPoints() {
        const rows = container.querySelectorAll('.draggable-row');
        container.querySelectorAll('.insertion-point').forEach(point => point.remove());

        rows.forEach((row, index) => {
            // Skip if this is the software row
            if (row.querySelector('.form-check-input').id === 'software_name') {
                // Add insertion point after software row only
                const point = document.createElement('div');
                point.className = 'insertion-point';
                point.dataset.position = '1';
                row.parentNode.insertBefore(point, row.nextSibling);
                return;
            }

            // For all other rows, add insertion point after
            if (index > 0) {
                const point = document.createElement('div');
                point.className = 'insertion-point';
                point.dataset.position = (index + 1).toString();
                row.parentNode.insertBefore(point, row.nextSibling);
            }
        });
    }

    // Clear all active insertion points
    function clearInsertionPoints() {
        document.querySelectorAll('.insertion-point').forEach(point => {
            point.classList.remove('active');
        });
    }

    function handleDragStart(e) {
        // Prevent dragging of Software column
        if (this.querySelector('.form-check-input').id === 'software_name') {
            e.preventDefault();
            return false;
        }
        draggingElement = this;
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        createInsertionPoints();
    }

    function handleDragEnd(e) {
        if (draggingElement) {
            draggingElement.classList.remove('dragging');
        }
        draggingElement = null;
        // Remove all insertion points
        document.querySelectorAll('.insertion-point').forEach(point => point.remove());
    }

    function handleDragOver(e) {
        e.preventDefault();
        const insertionPoint = getClosestInsertionPoint(e.clientY);
        if (insertionPoint) {
            clearInsertionPoints();
            insertionPoint.classList.add('active');
        }
    }

    function getClosestInsertionPoint(y) {
        const insertionPoints = [...document.querySelectorAll('.insertion-point')];
        let closest = null;
        let closestDistance = Infinity;

        insertionPoints.forEach(point => {
            const rect = point.getBoundingClientRect();
            const distance = Math.abs(y - (rect.top + rect.height / 2));
            if (distance < closestDistance) {
                closestDistance = distance;
                closest = point;
            }
        });

        return closest;
    }

    function handleDrop(e) {
        e.preventDefault();
        const insertionPoint = document.querySelector('.insertion-point.active');

        if (draggingElement && insertionPoint) {
            const position = parseInt(insertionPoint.dataset.position);
            const rows = [...container.querySelectorAll('.draggable-row')];

            // Get the index of the Software column
            const softwareIndex = rows.findIndex(row =>
                row.querySelector('.form-check-input').id === 'software_name'
            );
            // If trying to drop before Software, adjust position
            if (position <= softwareIndex) {
                return false;
            }

            const targetRow = rows[position] || null;

            if (targetRow) {
                container.insertBefore(draggingElement, targetRow);
            } else {
                container.appendChild(draggingElement);
            }
            updateColumnOrder();
        }

        // Cleanup
        clearInsertionPoints();
        document.querySelectorAll('.insertion-point').forEach(point => point.remove());
        return false;
    }

    // Add event listeners to all draggable rows
    draggableRows.forEach(row => {
        row.addEventListener('dragstart', handleDragStart, false);
        row.addEventListener('dragend', handleDragEnd, false);
    });

    // Add container listeners for drag over and drop
    container.addEventListener('dragover', handleDragOver, false);
    container.addEventListener('drop', handleDrop, false);

    // Handle cases where drag operation is canceled
    document.addEventListener('dragleave', function(e) {
        if (!e.relatedTarget) {
            clearInsertionPoints();
        }
    });

});

// Function to get teh current column order
function getColumnOrder(){
    const columns = [];
    const softwareColumn = 'software_name';
    // Add software_name first if it exists
    document.querySelectorAll('.draggable-row').forEach(row => {
        const formSwitch = row.querySelector('.form-check-input');
        if (formSwitch && formSwitch.id === softwareColumn) {
            columns.push(formSwitch.id.trim());
        }
    });

    // Add all other columns
    document.querySelectorAll('.draggable-row').forEach(row => {
        const formSwitch = row.querySelector('.form-check-input');
        if (formSwitch && formSwitch.id !== softwareColumn) {
            columns.push(formSwitch.id.trim());
        }
    });
    return columns;
}

// Function to send teh new column order to teh backend
function updateColumnOrder() {
    const columns = getColumnOrder();
    $.ajax({
        url:"/update_col_order",
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            col_order: columns
        }),
        success: function(response){
            console.log('Column order successfully updated', response)
            showAlert('Column order successfully updated', 'success');
        },
        error: function(xhr, status, error){
            console.error("Error updating column order", error)
            showAlert("Error updating column order", 'danger')
        }
    })
}

document.querySelectorAll('.column-input').forEach(input => {
    const originalName = input.getAttribute('placeholder');
    let previousValue = input.value || originalName;

    // Handle Enter key
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur();
        }
    });

    // Handle blur (clicking away)
    input.addEventListener('blur', function() {
        if (this.value.trim() !== previousValue) {
            handleColumnRename(this, originalName, this.value.trim());
            previousValue = this.value.trim();
        }
    });

});

// Function to handle column rename
function handleColumnRename(input, originalName, newName){
    if (newName === '' || newName === originalName) return;

    $.ajax({
        url: '/update_col_name',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            original_key: input.dataset.originalKey,
            new_name: newName
        }),
        success: function(response){
            console.log('Column name successfully updated', response)
            showAlert('Column name successfully updated', 'success');

            const label = input.closest('.draggable-row').querySelector('.column-name');
            if (label) {
                label.textContent = newName;
            }
        },
        error: function(xhr, status, error) {
            console.error("Error renaming column:", error);
            showAlert("Error renaming column", 'danger');
            // Reset input to original value on error
            input.value = originalName;
        }
    })
}