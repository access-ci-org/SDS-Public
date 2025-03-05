import { showAlert } from './alerts.js'
$(document).ready(function(){
    // Add a custom sorting plugin for checkboxes
    $.fn.dataTable.ext.order['dom-checkbox'] = function (settings, col) {
        return this.api().column(col, {order:'index'}).nodes().map(function (td, i) {
        return $('input', td).prop('checked') ? '1' : '0';
        });
    };

    var table = $("#report-table").DataTable({
        "aaSorting":[],
        columnDefs: [
            {
            targets: 0,
            orderable: true,
            orderDataType: 'dom-checkbox'
            }
        ]
    });

    // Handle checkbox changes
    $('#report-table').on('change', '.resolve-checkbox', function() {
        var reportId = $(this).data('report-id');
        var isResolved = $(this).prop('checked');
        $.ajax({
            url:"/chage_issue_status",
            type: 'POST',
            data: JSON.stringify({reportId:reportId, isResolved:isResolved}),
            contentType: 'application/json',
            success: function(response){
                response=JSON.parse(response)
                if (response['success'] === true){
                    // Update the row appearance based on resolved status
                    $(this).closest('tr').toggleClass('resolved-row', isResolved);
                } else {
                    console.error("Unable to update report satus")
                    showAlert('Error while trying to resolve report. Please try again', 'danger')
                }
            },
            error: function(xhr, status, error){
                console.error("Error:", error)
            }
        })
        // Trigger a re-sort of the table
        table.order([0, 'asc']).draw();
    });
    table.order([0, 'asc']).draw();
});