import { makeLinkClickable } from "../table.js";
import { COLUMN_MAP } from "../table.js";

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
                    var useHtml = response.use;
                    $("#modalExampleTitle").text('Example Use for ' + softwareName);
                    $('#modalExampleUse').html(useHtml);

                    // Populate the softwareDetails modal
                    $('#softwareDetails-modal-title').html("Software Details: " + row[0]);
                    $('#softwareDetailsName').text(row[COLUMN_MAP['Software']]);
                    $('#softwareDetailsRPs').text(row[COLUMN_MAP["RPName"]]);
                    $('#softwareDetailsType').html(row[COLUMN_MAP["SoftwareType"]]);
                    $('#softwareDetailsClass').html(row[COLUMN_MAP["SoftwareClass"]]);
                    $('#softwareDetailsField').html(row[COLUMN_MAP["ResearchField"]]);
                    $('#softwareDetailsArea').html(row[COLUMN_MAP["ResearchArea"]]);
                    $('#softwareDetailsDiscipline').html(row[COLUMN_MAP["ResearchDiscipline"]]);
                    $('#softwareDetailsDescription').html(makeLinkClickable(row[COLUMN_MAP["SoftwareDescription"]]));
                    $('#softwareDetailsWebpage').html(makeLinkClickable(row[COLUMN_MAP["SoftwaresWebPage"]]));
                    $('#softwareDetailsDocumentation').html(makeLinkClickable(row[COLUMN_MAP["SoftwareDocumentation"]]));
                    $('#softwareDetailsExamples').html(makeLinkClickable(row[COLUMN_MAP["ExampleSoftwareUse"]]));
                    $('#softwareDetailsRPDocs').html(makeLinkClickable(row[COLUMN_MAP["RPSoftwareDocumentation"]]));
                    $('#softwareDetailsVersions').html(row[COLUMN_MAP["VersionInfo"]]);
                    $('#softwareDetailsCoreFeat').html(row[COLUMN_MAP["CoreFeatures"]]);
                    $('#softwareDetailsTags').text(row[COLUMN_MAP["GeneralTags"]]);
                    $('#softwareDetailsAIDesc').text(row[COLUMN_MAP["AIDescription"]]);

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