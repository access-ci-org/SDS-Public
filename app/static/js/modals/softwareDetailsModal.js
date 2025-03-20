import {makeLinkClickable } from "../table.js";

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
        if (row['software_name'] === softwareName) { // Assuming the software name is in the first column

            if (use_ai_info.toLowerCase() === 'true') {
                // Trigger the modal logic
                var encodedSoftwareName = encodeURIComponent(softwareName);
                $.ajax({
                    url: "/example_use/" + encodedSoftwareName,
                    type: "GET",
                    success: function(response) {
                        var useHtml = response.use;
                        $('#modalExampleUse').html(useHtml);
                    },
                    error: function(xhr, status, error) {
                        console.error("Error fetching example use: ", error);
                    }
                });
            }

            // Populate the softwareDetails modal
            $('#softwareDetails-modal-title').html("Software Details: " + row['software_name']);
            $('#softwareDetailsName').text(row['software_name']);
            $('#softwareDetailsRPs').text(row['resource_name']);
            $('#softwareDetailsDescription').html(makeLinkClickable(row['software_description']));
            $('#softwareDetailsVersions').html(row['software_version']);
            if (use_curated_info === "True") {
                $('#softwareDetailsDocumentation').html(makeLinkClickable(row['software_documentation']));
                $('#softwareDetailsExamples').html(makeLinkClickable(row['software_use_link']));
                $('#softwareDetailsWebpage').html(makeLinkClickable(row["software_web_page"]));
            }

            if (use_ai_info === "True") {
                $('#softwareDetailsType').html(row['ai_software_type']);
                $('#softwareDetailsClass').html(row['ai_software_class']);
                $('#softwareDetailsField').html(row['ai_research_field']);
                $('#softwareDetailsArea').html(row['ai_research_area']);
                $('#softwareDetailsDiscipline').html(row['ai_research_discipline']);
                $('#softwareDetailsCoreFeat').html(row['ai_core_features']);
                $('#softwareDetailsTags').text(row['ai_general_tags']);
                $('#softwareDetailsAIDesc').text(row['ai_description']);
            }

            // Get the modal element
            const modalElement = document.getElementById('softwareDetails-modal');
            // if there's an existing instance of the modal
            let modal = bootstrap.Modal.getInstance(modalElement);
            if (!modal) {
                // Only create new instance if one doesn't exist
                modal = new bootstrap.Modal(modalElement);
            }
            modal.show();
        }
    });
}