import { staticTable } from "../table.js";

/*//////////////////////////////////////////////////////
Event Listener for Software 'Example Use' Modal  //
*/////////////////////////////////////////////////////    
export function onExampleUseClick(element){
    element.stopPropagation()
    let rowData = staticTable.row(element.target.closest('tr')).data();
    var softwareName = rowData[0];
    var encodedSoftwareName = encodeURIComponent(softwareName);
    $.ajax({
        url: "/example_use/"+encodedSoftwareName,
        type:"GET",
        success: function(response){

            var useHtml = response.use
            $("#useCase-modal-title").text('Use Case for ' + softwareName)
            $('#useCaseBody').html(useHtml);
            $('#useCase-modal').modal('show');
        },
        error: function(xhr, status, error){
            console.error("Error fetching example use: ", error);
    }})
}