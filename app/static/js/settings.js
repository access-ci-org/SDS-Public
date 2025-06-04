import { showAlert } from "./alerts.js"

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