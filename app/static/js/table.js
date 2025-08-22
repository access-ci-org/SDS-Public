import { setupFunctions, updateNavAndHeader } from "./navbarFooter.js";
import { showModalForSoftware, getURLParameter } from "./modals/softwareDetailsModal.js";

export var staticTable
export var column_names = JSON.parse(col_names) // defined in software_search.html

// Add Navbar, Header, and Footers settings
setupFunctions.universalMenus(document.getElementById("universal-menus"));
setupFunctions.header(document.getElementById("header"));
setupFunctions.siteMenus(document.getElementById("site-menus"));
setupFunctions.footerMenus(document.getElementById("footer-menus"));
setupFunctions.footer(document.getElementById("footer"));

// Update Navbar, Header, and Footer
updateNavAndHeader();

// Build columns array first, before initializing DataTable
function buildColumns() {
    var cols = [];
    var headerCells = $('#softwareTable thead th');

    // Create a reverse mapping from display names to internal keys
    const reverseColumnMap = {};
    Object.entries(column_names).forEach(([key, value]) => {
        reverseColumnMap[value] = key;
    });

    headerCells.each(function(index) {
        const displayName = $(this).text().trim();
        const internalKey = reverseColumnMap[displayName];
        var column = {
            data: internalKey,
        };
        // Helper function to safely split comma-separated values
        function safeSplit(data, separator) {
            if (!data || data === null || data === undefined || data === 'N/A') {
                return [];
            }
            return String(data)
                .split(separator)
                .map(item => item.trim())
                .filter(item => item && item !== '' && item !== 'N/A');
        }

        // Special handling for column 3 (index 3) with comma-separated values
        if (internalKey === 'ai_general_tags') {
            column.render = {
                _: function(data, type, row){
                    return data || '';
                },
                sp: function(data, type, row) {
                    return safeSplit(data, ', ');
                }
            };
            column.searchPanes = {
                orthogonal: 'sp'
            };
        } else if (internalKey === 'ai_research_discipline') {
            column.render = {
                _: function(data, type, row){
                    return data || '';
                },
                sp: function(data, type, row) {
                    return safeSplit(data, ', ');
                }
            };
            column.searchPanes = {
                orthogonal: 'sp'
            };
            column.visible = false;
        } else if (internalKey === 'ai_software_type') {
            column.visible = false;
        }
        if (internalKey === 'rp_name') {
            column.render = {
                _: function(data, type, row){
                    return data || '';
                },
                sp: function(data, type, row) {
                    return safeSplit(data, '<br>');
                }
            };
            column.searchPanes = {
                orthogonal: 'sp'
            };
            column.width = "150px";
        }

        if (internalKey === "software_name") {
            column.render = function(data, type, row) {
                if (type === 'display') {
                    return `<span class="table-software">` + (data || '') + '</span>';
                }
                return data || '';
            };
        } else if (internalKey === 'more_info') {
            column.render = function(data, type, row) {
                if (type === 'display') {
                    return '<button class="primary-button" type="button">DETAILS</button>';
                }
                return data || '';
            };
        } else if (internalKey === 'container'){
            column.render = function(data, type, row){
                if (type === 'display' && data && data !== 'N/A') {
                    return "<a class='viewContainer' href='#' onClick='return false;'> view containers</a>";
                }
                return data || '';
            };
        }
        $(this).text(displayName.replace("AI", ""))
        cols.push(column);
    });
    return cols;
}

// Get the columns array
var columns = buildColumns();

// Find which column indices have searchPanes enabled and valid data
var searchPaneColumns = [];
columns.forEach(function(col, index) {
    if (col.searchPanes && col.data) {
        // Only include columns that have searchPanes config and a valid data property
        searchPaneColumns.push(index);
    }
});

// If no searchPanes columns found, disable searchPanes entirely
var searchPanesConfig = false;
if (searchPaneColumns.length > 0) {
    searchPanesConfig = {
        columns: searchPaneColumns,
        layout: 'columns-3',
        threshold: 1.0,
        dtOpts: {
            select: { style: 'multi'},
            order: [[ 1, "desc" ]]
        }
    };
}

$(document).ready(function()
{
    /*/////////////////////////////////////////////////////////////////////////////////////////////////////////
        STATIC TABLE                                                                                        //
        Enabled: Buttons (Column Visibility), FixedColumn, FixedHeader, SearchPanes, Select //
    *///////////////////////////////////////////////////////////////////////////////////////////////////////

    var staticTable = $('#softwareTable').DataTable({
        ordering: false,    // Disables sorting
        // fixedColumns: true, // Makes first column 'fixed' to the left side of the table when scrolling
        fixedHeader: true,  // Makes column headers 'fixed' to the top of the table when scrolling
        // autowidth: false,
        // scrollCollapse: true,
        pageLength: 25,     // Rows displayed per page
        pagingType: 'full_numbers',     // 'First', 'Previous', 'Next', 'Last', with page numbers
        lengthMenu: [                   // User-selectable menu for pageLength
            [10, 25, 50, 250, 500, -1],
            [10, 25, 50, 250, 500, 'All']
        ],
        // DOM: various layout and formatting options.
        // For example: 'p' affects the paging style at the bottom of the table.
        dom: 'P<"#table-filters.d-flex flex-column flex-md-row justify-content-between"\
                    f\
                >\
                rt\
                <"#table_footer_menu.d-flex justify-content-between "lip>',
        language: {
            paginate: { // Change Arrows (< and >) into Word Equivalents
                previous: "Prev",
                next: "Next",
                first: "First",
                last: "Last"
            },
        },
        stateSave: false,   // Toggle for saving table options between page reloads
        stateDuration:-1,   // How long to save
        searchPanes:{
            columns:[1,3,4,5],
            layout: 'columns-2',
            threshold: 1.0,
            dtOpts: {
                select: { style: 'multi'},
                order: [[ 1, "desc" ]]
            }
        },
        columns: columns,
        initComplete: function() {
            const api = this.api();
            api.searchPanes.rebuildPane();
            // Target the fixed header cells inside the dt-scroll-headInner container.
            // These are the header cells that DataTables displays for scrolling/fixed columns.
            $('#softwareTableDiv table thead tr th').each(function(i) {
                // Get the original header text from the span with class "dt-column-title"
                let originalText = $(this).find('.dt-column-title').text().trim();
                if (!(originalText === 'Documentation, Uses, and more')) {
                    let new_header;
                    if (originalText.includes("Tags") || originalText.includes("Description")) {
                        originalText = originalText.replace("AI ", "")
                        new_header = `
                            <span style="display:block; font-weight:bold;">${originalText}
                            <img src="static/ACCESS-ai.svg" clas="ai-icon" style="max-width:20px; margin-bottom:5px;">
                            </span>
                        `
                    } else {
                        new_header = `
                            <span style="display:block; font-weight:bold;">${originalText}</span>
                        `
                    }
                    // Clear the header cell and add new header for the title
                    $(this).empty().append(new_header);

                    // Create an input field with a placeholder and append it to the header cell
                    let $input = $('<input type="text" class="col-search" style="width: 100%;" placeholder="Search ">');
                    $(this).append($input);
                    // Attach event listener to perform column search
                    $input.on('keyup change', function(e) {
                        self = this;
                        const columnIndex = api.column(this.closest('th')).index();
                        if (api.column(columnIndex).search() !== this.value) {
                            api.column(columnIndex).search(this.value).draw().one('draw', function(){
                                // minor timeout to ensure DOM updates
                                setTimeout(function(){
                                    self.focus();
                                },0)
                            })
                        }
                    });
                }
            });

            $('#softwareTable').show();
            api.columns.adjust(); // adjust columns if needed

        }

    });


    // Hide SearchPanes (filters) by default
    $(".dtsp-panesContainer").hide();
    // Add filter button to the table
    $("#table-filters").append(`
        <div id="toggle-filters" class="filter-button">
            <span id="filter-text">Show Filters</span>
            <i class="bi bi-filter"></i>
        </div>
    `);
    $("#toggle-filters").click(() => {
        $(".dtsp-panesContainer").toggle("fast", function() {
            const isVisible = $(".dtsp-panesContainer").is(":visible");
            const buttonText = isVisible ? "Hide Filters" : "Show Filters";
            if (!(isVisible)){
                const table = $("#softwareTable").DataTable();
                table.searchPanes.clearSelections();
            }
            $("#filter-text").html(buttonText);
        });
    })

/*///////////////////////////////////////////////////////////////
    Return softwareDetails modal to default state when closed //
*//////////////////////////////////////////////////////////////
    $('#softwareDetails-modal').on('hidden.bs.modal', function() {
        $("#software-data").html('')
        history.pushState(null, '', '/');
    });


/*//////////////////////////////////////////////
    Disable Searching Through Hidden Columns //
*/////////////////////////////////////////////
    $.fn.dataTable.ext.search.push(
        function(settings, data, dataIndex) {
            var api = new $.fn.dataTable.Api(settings);
            var visibleColumns = api.columns(':visible').indexes().toArray();

            // Check if all visible columns for the row are empty
            var allEmpty = true;
            for (var i = 0; i < visibleColumns.length; i++) {
                var columnIndex = visibleColumns[i];
                if (data[columnIndex].trim() !== '') {
                    allEmpty = false;
                    break;
                }
            }

            return !allEmpty; // Show row if not all visible columns are empty
        }
    );

    // Check initial URL for parameter
    var initialSoftwareName = getURLParameter('software');
    if (initialSoftwareName) {
        showModalForSoftware(initialSoftwareName);
    }

    // main search table input
    $(".dt-search input").attr('placeholder', 'Search Table')
    // datatables search panes buttons
    $(".dtsp-titleRow button").addClass('tag')
    // enable collapse all button on individual pane expand
    $(".dtsp-searchPane, .dtsp-collapseButton").on('click', function(e){
        if ($(".dtsp-collapseAll").hasClass("dtsp-disabledButton")) {
            $(".dtsp-collapseAll").removeClass("dtsp-disabledButton");
            $(".dtsp-collapseAll").removeAttr("disabled");
        }
    })
});

/*//////////////////////////////
    Clickable Links In Table //
*/////////////////////////////
export function makeLinkClickable(data) {
    var urlRegex = /(https?:\/\/[^\s<>]+)/g;  // Matches URLs starting with http/https and not containing whitespace or angle brackets
    if (data !== undefined) {
        return data.replace(urlRegex, function(url) {
            // Insert zero-width space after slashes or dots
            var spacedUrl = url.replace(/(\/|\.)+/g, '$&\u200B');
            return '<a href="' + url + '" target="_blank">' + spacedUrl + '</a>';
        });
    }
}

$('#softwareTable').on('click', '.primary-button', function(e) {
    const row = $(this).closest("tr");
    const softwareEntry = row.children()[0]
    const softwareNameHTML = softwareEntry.children[0]
    const softwareName = softwareNameHTML.firstChild.data
    history.pushState(null, '', '?software=' + encodeURIComponent(softwareName));
    showModalForSoftware(softwareName);
})

// Handels click on the "similar software" section on the software details modal
function handleSimilarSoftwareSelection(selector, tableId, needsDecoding = false) {
    $("#softwareDetails-modal").on('click', selector, function(e) {
        const text = this.innerText.trim();
        const currentSelections = $('div.dtsp-searchPane table').DataTable().rows({selected: true}).data().toArray();
        const newSelections = [...currentSelections, text];
        const searchPaneTable = $(`.dtsp-searchPanes table#${tableId}`).DataTable();

        searchPaneTable.rows(function(idx, data, node) {
            const displayValue = needsDecoding ? $('<div>').html(data.display).text() : data.display;
            return newSelections.includes(displayValue);
        }).select();

        // show the search panes and change text to hide
        $(".dtsp-panesContainer").show();
        $("#filter-text").html("Hide Filter");
        $("#softwareDetails-modal").modal('hide');
    });
}

// Set up all three search handlers
handleSimilarSoftwareSelection('.tag', 'DataTables_Table_1');
handleSimilarSoftwareSelection('.research-discipline', 'DataTables_Table_2', true); // needs decoding
handleSimilarSoftwareSelection('.software-type', 'DataTables_Table_3');