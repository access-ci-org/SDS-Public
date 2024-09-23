import { staticTable } from "../table.js";
export var converter

/*/////////////////////////////////////////////////////////////////////
    Initialize a Showdown converter with the Highlight.js extension //
*////////////////////////////////////////////////////////////////////
var converter = new showdown.Converter({
    extensions: [highlightExtension]
});

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

            var useHtml = converter.makeHtml(response.use)
            $("#useCase-modal-title").text('Use Case for ' + softwareName)
            $('#useCaseBody').html(useHtml);

            document.querySelectorAll('#useCaseBody pre Code').forEach((block)=>{
                hljs.highlightElement(block)
            })

            $('#useCase-modal').modal('show');
        },
        error: function(xhr, status, error){
            console.error("Error fetching example use: ", error);
    }})
}

/*//////////////////////////////////////////
    Highlight.js for 'Example Use' modal //
*/////////////////////////////////////////
// Define the Highlight.js extension for Showdown
function highlightExtension() {
    return [{
        type: 'output',
        filter: function (text, converter, options) {
            var left = '<pre><code\\b[^>]*>',
                right = '</code></pre>',
                flags = 'g',
                replacement = function (wholeMatch, match, left, right) {
                    match = match.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
                    return left + hljs.highlightAuto(match).value + right;
                };
            return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
        }
    }];
}