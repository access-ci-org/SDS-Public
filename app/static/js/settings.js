import { showAlert } from "./alerts.js"

// ── Column / download settings ────────────────────────────────────────────────

$(".form-check-input").change(function(){

    let column = $(this).attr('id');
    $.ajax({
        url:"/update_col_visibility/"+column,
        type: 'POST',
        success: function(response){
            showAlert(response.success, 'success');
        },
        error: function(xhr, status, error){
            console.error("Error updating column")
            showAlert("Error updating column", 'danger')
        }
    })
})

$("#download-software-csv").click(function (){
    showAlert("Preparing download...", 'info')
    window.location = "/download_software_csv"
})

$("#download-software-json").click(function () {
    showAlert("Preparing download...", 'info')
    window.location = "/download_software_json"
})

$("#download-analytics-json").click(function () {
    showAlert("Preparing download...", 'info')
    window.location = "/download_analytics_json"
})
