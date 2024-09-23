import { converter } from "./exampleUseModal.js";
import { makeLinkClickable } from "../table.js";


/*////////////////////////////////////////////////////////////////
    Function for URL identification for quick access to modals //
*///////////////////////////////////////////////////////////////
export function getURLParameter(name) {
    return decodeURIComponent((new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)').exec(location.search) || [,""])[1].replace(/\+/g, '%20')) || null;
}

/*///////////////////////////////////////////////
    Event Listener for Software Details Modal //
*//////////////////////////////////////////////
export function showModalForSoftware(softwareName, staticTable) {
    // Find the row that matches the software name
    staticTable.rows().every(function() {
        var row = this.data();
        if (row[0] === softwareName) { // Assuming the software name is in the first column
            // Trigger the modal logic
            var encodedSoftwareName = encodeURIComponent(softwareName);
            $.ajax({
                url: "/example_use/" + encodedSoftwareName,
                type: "GET",
                success: function(response) {
                    var useHtml = converter.makeHtml(response.use);
                    $("#modalExampleTitle").text('Example Use for ' + softwareName);
                    $('#modalExampleUse').html(useHtml);
                    document.querySelectorAll('#modalExampleUse pre Code').forEach((block) => {
                        hljs.highlightElement(block);
                    });

                    // Populate the softwareDetails modal
                    $('#softwareDetails-modal-title').html("Software Details: " + row[0]);
                    $('#softwareDetailsName').text(row[0]);
                    $('#softwareDetailsRPs').text(row[1]);
                    $('#softwareDetailsType').html(row[6]);
                    $('#softwareDetailsClass').html(row[15]);
                    $('#softwareDetailsField').html(row[11]);
                    $('#softwareDetailsArea').html(row[7]);
                    $('#softwareDetailsDiscipline').html(row[8]);
                    $('#softwareDetailsDescription').html(makeLinkClickable(row[2]));
                    $('#softwareDetailsWebpage').html(makeLinkClickable(row[10]));
                    $('#softwareDetailsDocumentation').html(makeLinkClickable(row[5]));
                    $('#softwareDetailsExamples').html(makeLinkClickable(row[12]));
                    $('#softwareDetailsRPDocs').html(makeLinkClickable(row[13]));
                    $('#softwareDetailsVersions').html(row[14]);
                    $('#softwareDetailsCoreFeat').html(row[4]);
                    $('#softwareDetailsTags').text(row[9]);
                    $('#softwareDetailsAIDesc').text(row[3]);

                    // Show modal
                    $('#softwareDetails-modal').modal('show');
                },
                error: function(xhr, status, error) {
                    console.error("Error fetching example use: ", error);
                }
            });
        }
    });
}